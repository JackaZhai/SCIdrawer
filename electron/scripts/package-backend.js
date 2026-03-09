const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function run(command, args, opts = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    shell: false,
    ...opts
  });
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed with code ${result.status}`);
  }
}

function runAllowFail(command, args, opts = {}) {
  return spawnSync(command, args, {
    stdio: 'inherit',
    shell: false,
    ...opts
  });
}

function main() {
  const electronDir = path.resolve(__dirname, '..');
  const projectRoot = path.resolve(electronDir, '..');
  const requirementsFile = path.join(projectRoot, 'requirements.txt');
  const appEntrypoint = path.join(projectRoot, 'app.py');
  const templatesDir = path.join(projectRoot, 'templates');
  const staticDir = path.join(projectRoot, 'static');
  const distDir = path.join(electronDir, 'dist-backend');
  const workDir = path.join(electronDir, 'build-backend');
  const specDir = electronDir;
  const venvDir = path.join(electronDir, '.backend-build-venv');
  const venvPythonExe = path.join(venvDir, 'Scripts', 'python.exe');
  const backendExe = path.join(distDir, 'scidrawer-backend.exe');
  const pythonExe = process.env.SCIDRAWER_PYTHON || process.env.NANO_BANANA_PYTHON || 'python';
  const paperBananaRuntimeDeps = [
    'google-genai',
    'google-auth',
    'openai',
    'anthropic',
    'aiofiles',
    'pillow',
    'numpy',
    'tqdm',
    'json_repair',
    'python-dotenv',
    'pyyaml'
  ];

  if (!fs.existsSync(appEntrypoint)) {
    throw new Error(`app.py not found: ${appEntrypoint}`);
  }
  if (!fs.existsSync(templatesDir) || !fs.existsSync(staticDir)) {
    throw new Error('templates/static directories are required for backend packaging.');
  }
  if (!fs.existsSync(requirementsFile)) {
    throw new Error(`requirements.txt not found: ${requirementsFile}`);
  }

  fs.mkdirSync(distDir, { recursive: true });
  fs.mkdirSync(workDir, { recursive: true });

  if (!fs.existsSync(venvPythonExe)) {
    console.log('[package-backend] Creating isolated build venv...');
    run(pythonExe, ['-m', 'venv', venvDir]);
  }
  console.log('[package-backend] Installing build dependencies in isolated venv...');
  run(venvPythonExe, ['-m', 'pip', 'install', '--upgrade', 'pip']);
  run(venvPythonExe, [
    '-m',
    'pip',
    'install',
    '-r',
    requirementsFile,
    'pyinstaller',
    ...paperBananaRuntimeDeps
  ]);

  const dataSeparator = path.delimiter;
  const pyArgs = [
    '-m',
    'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name',
    'scidrawer-backend',
    '--distpath',
    distDir,
    '--workpath',
    workDir,
    '--specpath',
    specDir,
    '--hidden-import',
    'charset_normalizer',
    '--hidden-import',
    'openai',
    '--hidden-import',
    'anthropic',
    '--hidden-import',
    'google.genai',
    '--hidden-import',
    'google.genai.types',
    '--hidden-import',
    'google.auth',
    '--hidden-import',
    'aiofiles',
    '--hidden-import',
    'yaml',
    '--hidden-import',
    'dotenv',
    '--hidden-import',
    'PIL',
    '--hidden-import',
    'numpy',
    '--hidden-import',
    'tqdm',
    '--hidden-import',
    'json_repair',
    '--collect-all',
    'openai',
    '--collect-all',
    'anthropic',
    '--collect-all',
    'google.genai',
    '--collect-all',
    'google.auth',
    '--collect-all',
    'charset_normalizer',
    '--add-data',
    `${templatesDir}${dataSeparator}templates`,
    '--add-data',
    `${staticDir}${dataSeparator}static`,
    appEntrypoint
  ];

  console.log('[package-backend] Building backend executable...');
  run(venvPythonExe, pyArgs, {
    cwd: projectRoot,
    env: { ...process.env, PYTHONNOUSERSITE: '1' }
  });

  if (!fs.existsSync(backendExe)) {
    throw new Error(`Backend executable not found after build: ${backendExe}`);
  }

  console.log(`[package-backend] Done: ${backendExe}`);
}

try {
  main();
} catch (err) {
  console.error(`[package-backend] ${err.message}`);
  process.exit(1);
}
