const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => ipcRenderer.invoke('app:version'),
  getPlatform: () => ipcRenderer.invoke('app:platform'),
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),

  onBackendStatus: (callback) => {
    const handler = (_, status) => callback(status);
    ipcRenderer.on('backend:status', handler);
    return () => ipcRenderer.removeListener('backend:status', handler);
  },
});
