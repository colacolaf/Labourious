const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const isDev = process.env.NODE_ENV === 'development';

// ponytail: dev path only — production bundling requires PyInstaller, see Phase 9 notes
let backendProcess = null;

function startBackend() {
  const projectRoot = path.join(__dirname, '../..');
  const pythonPath = isDev
    ? path.join(projectRoot, '.venv/bin/python')
    : path.join(process.resourcesPath, 'backend', 'python');
  const cwd = isDev ? projectRoot : process.resourcesPath;

  backendProcess = spawn(pythonPath, ['-m', 'uvicorn', 'backend.main:app', '--port', '8000', '--host', '127.0.0.1'], {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString().trim()));
  backendProcess.on('exit', (code) => console.log(`[backend] exited with code ${code}`));
}

function waitForBackend(maxWaitMs = 30_000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      const req = http.get('http://127.0.0.1:8000/api/health', (res) => {
        if (res.statusCode === 200) { resolve(); return; }
        retry();
      });
      req.on('error', retry);
      req.setTimeout(500, () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() - start > maxWaitMs) {
        reject(new Error('Backend failed to start within 30s'));
        return;
      }
      setTimeout(check, 500);
    };
    check();
  });
}

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    backgroundColor: '#0a0a0f',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      devTools: isDev,
    },
    show: false,
  });

  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../build/index.html')}`;

  mainWindow.loadURL(startUrl);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (isDev) mainWindow.webContents.openDevTools();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  // Check if backend already up (dev mode guard)
  let backendAlreadyUp = false;
  await new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:8000/api/health', (res) => {
      backendAlreadyUp = res.statusCode === 200;
      resolve();
    });
    req.on('error', resolve);
    req.setTimeout(500, () => { req.destroy(); resolve(); });
  });

  if (!backendAlreadyUp) {
    startBackend();
    try {
      await waitForBackend();
    } catch (e) {
      dialog.showErrorBox('Backend Failed to Start', 'Python backend did not start within 30s. Check logs.');
    }
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }
});

ipcMain.handle('app:version', () => app.getVersion());

ipcMain.handle('app:platform', () => process.platform);

ipcMain.handle('shell:openExternal', (_, url) => {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    shell.openExternal(url);
  }
});
