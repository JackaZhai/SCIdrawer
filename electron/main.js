const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let pyProc = null;
let mainWindow = null;
const APP_ICON = path.join(__dirname, '..', 'static', 'app-icon.ico');

if (process.platform === 'win32') {
  app.setAppUserModelId('com.scidrawer.desktop');
}

function waitForServer(url, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
      });
      req.on('error', retry);

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

function startPythonServer(port) {
  const projectRoot = path.resolve(__dirname, '..');
  const pythonExe = process.env.SCIDRAWER_PYTHON || process.env.NANO_BANANA_PYTHON || 'python';

  pyProc = spawn(pythonExe, ['app.py'], {
    cwd: projectRoot,
    env: { ...process.env, PORT: String(port) },
    stdio: 'pipe',
    windowsHide: true
  });

  pyProc.stdout.on('data', (d) => process.stdout.write(String(d)));
  pyProc.stderr.on('data', (d) => process.stderr.write(String(d)));

  pyProc.on('exit', (code) => {
    if (code !== 0) {
      console.error(`Python exited with code ${code}`);
    }
  });
}

function registerWindowIpc() {
  ipcMain.on('window:minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('window:toggle-maximize', () => {
    if (!mainWindow) return;
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });

  ipcMain.on('window:close', () => {
    if (mainWindow) mainWindow.close();
  });
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 980,
    minHeight: 640,
    frame: false,
    backgroundColor: '#0b0f14',
    icon: APP_ICON,
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (process.platform === 'win32') {
    mainWindow.setIcon(APP_ICON);
  }

  mainWindow.loadURL(`http://127.0.0.1:${port}/`);
}

app.whenReady().then(async () => {
  const port = Number(process.env.PORT || 1200);

  try {
    registerWindowIpc();
    startPythonServer(port);
    await waitForServer(`http://127.0.0.1:${port}/`);
    createWindow(port);
  } catch (err) {
    dialog.showErrorBox('启动失败', `无法启动本地服务：${err.message}`);
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(port);
    }
  });
});

app.on('window-all-closed', () => {
  if (pyProc) {
    try { pyProc.kill(); } catch {}
    pyProc = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
