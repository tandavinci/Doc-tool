/**
 * Electron Main Process
 *
 * - Creates BrowserWindow loading frontend/index.html
 * - Spawns persistent Python backend (backend/protocol.py)
 * - Maintains request/response mapping via request IDs
 * - Forwards IPC requests from renderer to Python stdin
 * - Forwards Python stdout responses back to renderer
 * - Terminates Python cleanly on app close
 * - Prevents orphan processes
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const readline = require('readline');

let mainWindow = null;
let pythonProcess = null;
let requestId = 0;
let pendingRequests = new Map(); // id -> { resolve, reject }
let backendReady = false;

// =============================================================================
// PYTHON BACKEND MANAGEMENT
// =============================================================================

function spawnBackend() {
  const backendPath = path.join(__dirname, '..', 'backend', 'protocol.py');

  pythonProcess = spawn('python', [backendPath], {
    cwd: path.join(__dirname, '..', 'backend'),
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  });

  // Read stdout line by line (newline-delimited JSON)
  const rl = readline.createInterface({ input: pythonProcess.stdout });

  rl.on('line', (line) => {
    if (!line.trim()) return;
    try {
      const response = JSON.parse(line);

      // Handle ready signal
      if (response.status === 'ready') {
        backendReady = true;
        console.log('[main] Backend ready');
        return;
      }

      // Route response to pending request
      const id = response.id;
      if (id && pendingRequests.has(id)) {
        const { resolve } = pendingRequests.get(id);
        pendingRequests.delete(id);
        resolve(response);
      }
    } catch (e) {
      console.error('[main] Failed to parse backend response:', e.message);
    }
  });

  // Log backend stderr
  pythonProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim();
    if (msg) console.log('[backend]', msg);
  });

  // Detect backend crash
  pythonProcess.on('exit', (code, signal) => {
    console.log(`[main] Backend exited: code=${code}, signal=${signal}`);
    pythonProcess = null;
    backendReady = false;

    // Reject all pending requests
    for (const [id, { reject }] of pendingRequests) {
      reject(new Error('Backend process crashed'));
    }
    pendingRequests.clear();

    // Notify renderer if window exists
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend-error', {
        message: 'Backend process crashed. Please restart the application.',
      });
    }
  });

  pythonProcess.on('error', (err) => {
    console.error('[main] Failed to start backend:', err.message);
    backendReady = false;
  });
}

function sendToBackend(action, payload) {
  return new Promise((resolve, reject) => {
    if (!pythonProcess || !backendReady) {
      reject(new Error('Backend not available'));
      return;
    }

    requestId++;
    const id = `req-${String(requestId).padStart(4, '0')}`;
    const request = { id, action, payload };

    pendingRequests.set(id, { resolve, reject });

    // Write JSON + newline to stdin
    const line = JSON.stringify(request) + '\n';
    pythonProcess.stdin.write(line, 'utf-8');
  });
}

function shutdownBackend() {
  if (!pythonProcess) return Promise.resolve();

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      // Force kill after 3 seconds
      if (pythonProcess) {
        console.log('[main] Force killing backend');
        pythonProcess.kill('SIGKILL');
      }
      resolve();
    }, 3000);

    pythonProcess.once('exit', () => {
      clearTimeout(timeout);
      resolve();
    });

    // Send shutdown command
    try {
      const shutdownReq = JSON.stringify({ id: 'shutdown', action: 'shutdown' }) + '\n';
      pythonProcess.stdin.write(shutdownReq, 'utf-8');
    } catch (e) {
      // stdin may already be closed
      if (pythonProcess) {
        pythonProcess.kill('SIGTERM');
      }
    }
  });
}

// =============================================================================
// IPC HANDLERS
// =============================================================================

ipcMain.handle('analyze', async (event, text) => {
  return sendToBackend('analyze', { text });
});

ipcMain.handle('rewrite', async (event, text) => {
  return sendToBackend('rewrite', { text });
});

ipcMain.handle('convert-dita', async (event, text, format) => {
  return sendToBackend('convert_dita', { text, format });
});

ipcMain.handle('impact-analyze', async (event, jiraItems, ditaTopics, threshold) => {
  return sendToBackend('impact_analyze', { jiraItems, ditaTopics, threshold });
});

// =============================================================================
// WINDOW CREATION
// =============================================================================

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// =============================================================================
// APP LIFECYCLE
// =============================================================================

app.whenReady().then(() => {
  spawnBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('before-quit', async (event) => {
  if (pythonProcess) {
    event.preventDefault();
    await shutdownBackend();
    app.quit();
  }
});

// Ensure cleanup on all exit paths
process.on('exit', () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGKILL');
  }
});

process.on('SIGTERM', () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGKILL');
  }
  process.exit(0);
});
