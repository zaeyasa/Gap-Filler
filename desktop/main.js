/**
 * Gap Filler Desktop - Main Process
 * Electron main entry point
 */

const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');

// Configuration
const CONFIG = {
    BACKEND_PORT: 5000,
    OLLAMA_URL: 'http://localhost:11434',
    DEFAULT_MODEL: 'deepseek-r1:8b-llama-distill-q4_K_M',
    OLLAMA_INSTALLER_URL: 'https://ollama.com/download/OllamaSetup.exe'
};

// Global references
let mainWindow = null;
let installerWindow = null;
let backendProcess = null;
let isDev = process.argv.includes('--dev');

// Paths
function getResourcePath(relativePath) {
    if (isDev) {
        return path.join(__dirname, '..', relativePath);
    }
    return path.join(process.resourcesPath, relativePath);
}

// ============================================================================
// Window Management
// ============================================================================

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        },
        icon: path.join(__dirname, 'assets', 'icon.png'),
        show: false,
        titleBarStyle: 'default',
        autoHideMenuBar: true
    });

    const frontendPath = getResourcePath('frontend/index.html');
    mainWindow.loadFile(frontendPath);

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
        stopBackend();
    });

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

function createInstallerWindow() {
    installerWindow = new BrowserWindow({
        width: 700,
        height: 550,
        resizable: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        },
        icon: path.join(__dirname, 'assets', 'icon.png'),
        show: false,
        frame: true,
        autoHideMenuBar: true,
        title: 'Gap Filler - Setup Wizard'
    });

    installerWindow.loadFile(path.join(__dirname, 'installer', 'installer.html'));

    installerWindow.once('ready-to-show', () => {
        installerWindow.show();
    });

    installerWindow.on('closed', () => {
        installerWindow = null;
    });
}

// ============================================================================
// Backend Management
// ============================================================================

async function startBackend() {
    return new Promise((resolve, reject) => {
        const backendPath = getResourcePath('backend');
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

        console.log(`Starting backend from: ${backendPath}`);

        backendProcess = spawn(pythonCmd, ['app.py'], {
            cwd: backendPath,
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });

        backendProcess.stdout.on('data', (data) => {
            console.log(`[Backend] ${data}`);
            if (data.toString().includes('Running on')) {
                resolve(true);
            }
        });

        backendProcess.stderr.on('data', (data) => {
            console.error(`[Backend Error] ${data}`);
        });

        backendProcess.on('error', (error) => {
            console.error('Failed to start backend:', error);
            reject(error);
        });

        backendProcess.on('close', (code) => {
            console.log(`Backend exited with code ${code}`);
            backendProcess = null;
        });

        // Timeout fallback
        setTimeout(() => resolve(true), 3000);
    });
}

function stopBackend() {
    if (backendProcess) {
        console.log('Stopping backend...');
        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
        } else {
            backendProcess.kill('SIGTERM');
        }
        backendProcess = null;
    }
}

// ============================================================================
// Dependency Checking
// ============================================================================

async function checkOllama() {
    try {
        const fetch = require('node-fetch');
        const response = await fetch(`${CONFIG.OLLAMA_URL}/api/tags`, { timeout: 5000 });
        if (response.ok) {
            const data = await response.json();
            return {
                installed: true,
                running: true,
                models: data.models || []
            };
        }
    } catch (error) {
        // Check if Ollama is installed but not running
        const ollamaPath = process.platform === 'win32'
            ? path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Ollama', 'ollama.exe')
            : '/usr/local/bin/ollama';

        if (fs.existsSync(ollamaPath)) {
            return { installed: true, running: false, models: [] };
        }
    }
    return { installed: false, running: false, models: [] };
}

async function checkModel(modelName) {
    try {
        const fetch = require('node-fetch');
        const response = await fetch(`${CONFIG.OLLAMA_URL}/api/tags`);
        if (response.ok) {
            const data = await response.json();
            const models = data.models || [];
            return models.some(m => m.name.includes(modelName.split(':')[0]));
        }
    } catch (error) {
        return false;
    }
    return false;
}

async function downloadOllama() {
    return new Promise((resolve, reject) => {
        const https = require('https');
        const tempPath = path.join(app.getPath('temp'), 'OllamaSetup.exe');
        const file = fs.createWriteStream(tempPath);

        https.get(CONFIG.OLLAMA_INSTALLER_URL, (response) => {
            // Handle redirects
            if (response.statusCode === 302 || response.statusCode === 301) {
                https.get(response.headers.location, (res) => {
                    res.pipe(file);
                    file.on('finish', () => {
                        file.close();
                        resolve(tempPath);
                    });
                }).on('error', reject);
            } else {
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    resolve(tempPath);
                });
            }
        }).on('error', reject);
    });
}

async function installOllama(installerPath) {
    return new Promise((resolve, reject) => {
        // Silent install
        exec(`"${installerPath}" /S`, (error) => {
            if (error) {
                reject(error);
            } else {
                resolve(true);
            }
        });
    });
}

async function startOllamaService() {
    return new Promise((resolve) => {
        const ollamaPath = path.join(
            process.env.LOCALAPPDATA || '',
            'Programs', 'Ollama', 'ollama.exe'
        );

        if (fs.existsSync(ollamaPath)) {
            spawn(ollamaPath, ['serve'], { detached: true, stdio: 'ignore' });
            // Wait for Ollama to start
            setTimeout(() => resolve(true), 3000);
        } else {
            resolve(false);
        }
    });
}

async function pullModel(modelName, progressCallback) {
    return new Promise(async (resolve, reject) => {
        const fetch = require('node-fetch');

        try {
            const response = await fetch(`${CONFIG.OLLAMA_URL}/api/pull`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: modelName, stream: true })
            });

            const reader = response.body;
            let buffer = '';

            reader.on('data', (chunk) => {
                buffer += chunk.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const data = JSON.parse(line);
                            if (data.total && data.completed) {
                                const percent = Math.round((data.completed / data.total) * 100);
                                if (progressCallback) progressCallback(percent, data.status);
                            } else if (data.status) {
                                if (progressCallback) progressCallback(null, data.status);
                            }
                        } catch (e) { }
                    }
                }
            });

            reader.on('end', () => {
                resolve(true);
            });

            reader.on('error', reject);
        } catch (error) {
            reject(error);
        }
    });
}

// ============================================================================
// IPC Handlers
// ============================================================================

ipcMain.handle('check-ollama', async () => {
    return await checkOllama();
});

ipcMain.handle('check-model', async (event, modelName) => {
    return await checkModel(modelName || CONFIG.DEFAULT_MODEL);
});

ipcMain.handle('get-default-model', () => {
    return CONFIG.DEFAULT_MODEL;
});

ipcMain.handle('download-ollama', async () => {
    try {
        const installerPath = await downloadOllama();
        return { success: true, path: installerPath };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('install-ollama', async (event, installerPath) => {
    try {
        await installOllama(installerPath);
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('start-ollama', async () => {
    return await startOllamaService();
});

ipcMain.handle('pull-model', async (event, modelName) => {
    try {
        await pullModel(modelName || CONFIG.DEFAULT_MODEL, (percent, status) => {
            if (installerWindow) {
                installerWindow.webContents.send('model-pull-progress', { percent, status });
            }
        });
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('start-backend', async () => {
    try {
        await startBackend();
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
});

ipcMain.handle('finish-setup', async () => {
    if (installerWindow) {
        installerWindow.close();
    }
    createMainWindow();
});

ipcMain.handle('open-external', async (event, url) => {
    shell.openExternal(url);
});

// ============================================================================
// App Lifecycle
// ============================================================================

app.whenReady().then(async () => {
    // Check if setup is needed
    const ollamaStatus = await checkOllama();
    const hasModel = ollamaStatus.running ? await checkModel(CONFIG.DEFAULT_MODEL) : false;

    if (!ollamaStatus.installed || !ollamaStatus.running || !hasModel) {
        // Show installer wizard
        createInstallerWindow();
    } else {
        // Start directly
        await startBackend();
        createMainWindow();
    }
});

app.on('window-all-closed', () => {
    stopBackend();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

app.on('before-quit', () => {
    stopBackend();
});
