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

/**
 * Determine backend executable path based on environment:
 * - Development: runs Python interpreter with protocol.py
 * - Packaged: runs the PyInstaller-bundled backend.exe from resources
 */
function getBackendConfig() {
  if (app.isPackaged) {
    // In packaged mode, backend exe is in resources/backend/
    const backendExe = path.join(process.resourcesPath, 'backend', 'backend.exe');
    return {
      command: backendExe,
      args: [],
      cwd: path.join(process.resourcesPath, 'backend'),
    };
  } else {
    // Development mode: use Python interpreter
    const backendPath = path.join(__dirname, '..', 'backend', 'protocol.py');
    const pythonCmd = process.platform === 'win32' ? 'py' : 'python';
    return {
      command: pythonCmd,
      args: [backendPath],
      cwd: path.join(__dirname, '..', 'backend'),
    };
  }
}

function spawnBackend() {
  const config = getBackendConfig();

  console.log(`[main] Starting backend: ${config.command} ${config.args.join(' ')}`);
  console.log(`[main] Backend cwd: ${config.cwd}`);

  pythonProcess = spawn(config.command, config.args, {
    cwd: config.cwd,
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
        if (DEBUG) console.log(`[main][DEBUG] ← Received from backend: id=${id}, success=${response.success}`);
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

const REQUEST_TIMEOUT_MS = 30000; // 30 second timeout for backend requests
const MARKITDOWN_TIMEOUT_MS = 120000; // 120 second timeout for file conversions
const DEBUG = process.argv.includes('--dev');

function sendToBackend(action, payload) {
  return new Promise((resolve, reject) => {
    if (!pythonProcess || !backendReady) {
      reject(new Error('Backend not available'));
      return;
    }

    requestId++;
    const id = `req-${String(requestId).padStart(4, '0')}`;
    const request = { id, action, payload };

    // Use longer timeout for markitdown conversions (large file processing)
    const timeoutMs = action === 'markitdown' ? MARKITDOWN_TIMEOUT_MS : REQUEST_TIMEOUT_MS;

    // Timeout protection for stalled requests
    const timer = setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        reject(new Error(`Backend request timed out after ${timeoutMs / 1000}s: ${action} (${id})`));
      }
    }, timeoutMs);

    pendingRequests.set(id, {
      resolve: (response) => { clearTimeout(timer); resolve(response); },
      reject: (err) => { clearTimeout(timer); reject(err); },
    });

    // Write JSON + newline to stdin, handling backpressure for large payloads
    const line = JSON.stringify(request) + '\n';
    if (DEBUG) console.log(`[main][DEBUG] → Sending to backend: id=${id}, action=${action}, size=${line.length}`);
    const ok = pythonProcess.stdin.write(line, 'utf-8');
    if (!ok) {
      // Buffer is full, wait for drain before considering ready for next write
      pythonProcess.stdin.once('drain', () => {
        if (DEBUG) console.log(`[main][DEBUG] stdin drained after large write: id=${id}`);
      });
    }
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
// IPC HANDLERS — wrap errors so renderer always gets a structured response
// =============================================================================

ipcMain.on('set-title', (event, title) => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.setTitle(title);
  }
});

ipcMain.handle('analyze', async (event, text) => {
  try {
    return await sendToBackend('analyze', { text });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('rewrite', async (event, text) => {
  try {
    return await sendToBackend('rewrite', { text });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('convert-dita', async (event, text, format) => {
  try {
    return await sendToBackend('convert_dita', { text, format });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('impact-analyze', async (event, jiraItems, ditaTopics, threshold) => {
  try {
    return await sendToBackend('impact_analyze', { jiraItems, ditaTopics, threshold });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('markitdown-convert', async (event, payload) => {
  try {
    return await sendToBackend('markitdown', payload);
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('quick-review', async (event, text) => {
  try {
    return await sendToBackend('quick_review', { text });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
});

ipcMain.handle('first-draft', async (event, text) => {
  try {
    return await sendToBackend('first_draft', { text });
  } catch (e) {
    return { id: null, success: false, error: { code: 'IPC_ERROR', message: e.message } };
  }
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

  // Open DevTools in development mode
  if (DEBUG) {
    mainWindow.webContents.openDevTools();
  }

  // Intercept close — ask renderer to show confirmation dialog
  let forceClose = false;
  mainWindow.on('close', (e) => {
    if (!forceClose) {
      e.preventDefault();
      mainWindow.webContents.send('confirm-close');
    }
  });

  ipcMain.on('close-confirmed', () => {
    forceClose = true;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close();
    }
  });

  ipcMain.on('close-cancelled', () => {
    // User cancelled — do nothing
  });

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
