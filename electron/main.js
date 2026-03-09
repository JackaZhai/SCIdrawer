const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const net = require('net');

let backendProc = null;
let mainWindow = null;
let currentPort = null;
let isQuitting = false;
let backendLogStream = null;
const DEV_APP_ICON = path.join(__dirname, '..', 'static', 'app-icon.ico');
const MAX_BACKEND_LOG_LINES = 200;
const backendLogLines = [];

if (process.platform === 'win32') {
  app.setAppUserModelId('com.scidrawer.desktop');
}

function waitForServer(url, timeoutMs = 120000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
          resolve();
          return;
        }
        retry();
      });
      req.on('error', retry);
      req.setTimeout(3000, retry);

      function retry() {
        req.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error('Server did not start in time'));
          return;
        }
        setTimeout(tick, 500);
      }
    };
    tick();
  });
}

function appendBackendLog(stream, chunk) {
  const text = String(chunk);
  const writer = stream === 'stderr' ? process.stderr : process.stdout;
  writer.write(text);
  if (backendLogStream) {
    backendLogStream.write(`[${new Date().toISOString()}] [${stream}] ${text}`);
  }

  const lines = text.split(/\r?\n/).filter(Boolean);
  for (const line of lines) {
    backendLogLines.push(`[${stream}] ${line}`);
  }

  while (backendLogLines.length > MAX_BACKEND_LOG_LINES) {
    backendLogLines.shift();
  }
}

function backendLogTail(lineCount = 30) {
  return backendLogLines.slice(-lineCount).join('\n');
}

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once('error', () => resolve(false));
    tester.once('listening', () => tester.close(() => resolve(true)));
    tester.listen(port, '127.0.0.1');
  });
}

async function pickPort(startPort, maxAttempts = 20) {
  for (let i = 0; i <= maxAttempts; i += 1) {
    const port = startPort + i;
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port found from ${startPort} to ${startPort + maxAttempts}`);
}

function buildRuntime(port) {
  const projectRoot = path.resolve(__dirname, '..');
  const userDataDir = app.getPath('userData');
  const dataDir = path.join(userDataDir, 'data');
  const dbPath = path.join(dataDir, 'app.db');
  const integrationsRoot = app.isPackaged
    ? path.join(process.resourcesPath, 'integrations')
    : path.join(projectRoot, 'integrations');

  fs.mkdirSync(dataDir, { recursive: true });

  return {
    projectRoot,
    userDataDir,
    env: {
      ...process.env,
      PORT: String(port),
      DATA_DIR: dataDir,
      DB_PATH: dbPath,
      PAPERBANANA_ROOT: path.join(integrationsRoot, 'PaperBanana'),
      EDIT_BANANA_ROOT: path.join(integrationsRoot, 'Edit-Banana')
    }
  };
}

function startBackendServer(port) {
  const runtime = buildRuntime(port);
  const backendLogPath = path.join(runtime.userDataDir, 'backend.log');
  backendLogStream = fs.createWriteStream(backendLogPath, { flags: 'a' });
  backendLogStream.write(
    `\n[${new Date().toISOString()}] Starting backend (packaged=${app.isPackaged}) on port ${port}\n`
  );

  if (app.isPackaged) {
    const backendExe = path.join(process.resourcesPath, 'backend', 'scidrawer-backend.exe');
    if (!fs.existsSync(backendExe)) {
      throw new Error(`Backend executable not found: ${backendExe}`);
    }

    backendProc = spawn(backendExe, [], {
      cwd: runtime.userDataDir,
      env: runtime.env,
      stdio: 'pipe',
      windowsHide: true
    });
  } else {
    const pythonExe = process.env.SCIDRAWER_PYTHON || process.env.NANO_BANANA_PYTHON || 'python';
    backendProc = spawn(pythonExe, ['app.py'], {
      cwd: runtime.projectRoot,
      env: runtime.env,
      stdio: 'pipe',
      windowsHide: true
    });
  }

  backendProc.stdout.on('data', (d) => appendBackendLog('stdout', d));
  backendProc.stderr.on('data', (d) => appendBackendLog('stderr', d));

  backendProc.on('exit', (code, signal) => {
    if (backendLogStream) {
      backendLogStream.write(
        `[${new Date().toISOString()}] Backend exited code=${code ?? 'null'} signal=${signal ?? 'none'}\n`
      );
    }
    if (!isQuitting && code !== 0) {
      console.error(`Backend exited with code=${code ?? 'null'} signal=${signal ?? 'none'}`);
    }
  });

  return new Promise((_, reject) => {
    backendProc.once('exit', (code, signal) => {
      const details = backendLogTail();
      const msg =
        `Backend exited unexpectedly (code=${code ?? 'null'}, signal=${signal ?? 'none'}).` +
        (details ? `\n\nRecent backend logs:\n${details}` : '');
      reject(new Error(msg));
    });
  });
}

function registerWindowIpc() {
  ipcMain.on('window:minimize', () => {
    if (mainWindow) {
      mainWindow.minimize();
    }
  });

  ipcMain.on('window:toggle-maximize', () => {
    if (!mainWindow) {
      return;
    }
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });

  ipcMain.on('window:close', () => {
    if (mainWindow) {
      mainWindow.close();
    }
  });
}

function resolveAppIcon() {
  const packagedIcon = path.join(process.resourcesPath, 'static', 'app-icon.ico');
  const iconPath = app.isPackaged ? packagedIcon : DEV_APP_ICON;
  return fs.existsSync(iconPath) ? iconPath : undefined;
}

function createWindow(port) {
  const iconPath = resolveAppIcon();

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 980,
    minHeight: 640,
    frame: false,
    backgroundColor: '#0b0f14',
    icon: iconPath,
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (process.platform === 'win32' && iconPath) {
    mainWindow.setIcon(iconPath);
  }

  mainWindow.loadURL(`http://127.0.0.1:${port}/`);
}

app.whenReady().then(async () => {
  const preferredPort = Number(process.env.PORT || 1200);
  const startupTimeoutMs = Number(process.env.SCIDRAWER_STARTUP_TIMEOUT_MS || 120000);

  try {
    currentPort = await pickPort(preferredPort);
    registerWindowIpc();

    const backendExit = startBackendServer(currentPort);
    await Promise.race([
      waitForServer(`http://127.0.0.1:${currentPort}/`, startupTimeoutMs),
      backendExit
    ]);

    createWindow(currentPort);
  } catch (err) {
    dialog.showErrorBox(
      'Startup Failed',
      `Unable to start local service.\n\n${err.message || String(err)}`
    );
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0 && currentPort) {
      createWindow(currentPort);
    }
  });
});

app.on('window-all-closed', () => {
  isQuitting = true;
  if (backendProc) {
    try {
      backendProc.kill();
    } catch {}
    backendProc = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
  if (backendLogStream) {
    try {
      backendLogStream.end();
    } catch {}
    backendLogStream = null;
  }
});
