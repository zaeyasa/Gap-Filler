/**
 * Gap Filler Desktop - Preload Script
 * Secure bridge between renderer and main process
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected APIs to renderer
contextBridge.exposeInMainWorld('gapFiller', {
    // Dependency checks
    checkOllama: () => ipcRenderer.invoke('check-ollama'),
    checkModel: (modelName) => ipcRenderer.invoke('check-model', modelName),
    getDefaultModel: () => ipcRenderer.invoke('get-default-model'),

    // Ollama installation
    downloadOllama: () => ipcRenderer.invoke('download-ollama'),
    installOllama: (path) => ipcRenderer.invoke('install-ollama', path),
    startOllama: () => ipcRenderer.invoke('start-ollama'),

    // Model management
    pullModel: (modelName) => ipcRenderer.invoke('pull-model', modelName),
    onModelPullProgress: (callback) => {
        ipcRenderer.on('model-pull-progress', (event, data) => callback(data));
    },

    // Backend management
    startBackend: () => ipcRenderer.invoke('start-backend'),

    // Setup flow
    finishSetup: () => ipcRenderer.invoke('finish-setup'),

    // Utilities
    openExternal: (url) => ipcRenderer.invoke('open-external', url)
});

// Version info
contextBridge.exposeInMainWorld('appInfo', {
    version: '1.0.0',
    name: 'Gap Filler',
    description: 'Plant Genomics Literature Gap Finder'
});
