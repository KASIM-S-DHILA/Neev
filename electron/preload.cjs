const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("studyLens", {
  storage: {
    request: (payload) => ipcRenderer.invoke("storage:request", payload),
    listSources: (payload) =>
      ipcRenderer.invoke("storage:listSources", payload),
    chooseFiles: (payload) =>
      ipcRenderer.invoke("storage:chooseFiles", payload),
    importFile: (payload) => ipcRenderer.invoke("storage:importFile", payload),
    cancelImport: (payload) =>
      ipcRenderer.invoke("storage:cancelImport", payload),
    download: (payload) => ipcRenderer.invoke("storage:download", payload),
  },
  windowAction: (action) => {
    if (["minimize", "maximize", "close"].includes(action))
      ipcRenderer.send("window:action", action);
  },
  onMaximized: (callback) => {
    const listener = (_event, value) => callback(Boolean(value));
    ipcRenderer.on("window:maximized", listener);
    return () => ipcRenderer.removeListener("window:maximized", listener);
  },
});
