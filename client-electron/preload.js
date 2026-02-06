const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("whisprly", {
  // Config & server
  getConfig: () => ipcRenderer.invoke("get-config"),
  getTones: () => ipcRenderer.invoke("get-tones"),
  checkHealth: () => ipcRenderer.invoke("check-health"),

  // Audio processing (done in renderer via fetch to server)
  getServerUrl: async () => {
    const config = await ipcRenderer.invoke("get-config");
    return config.server?.url || "http://localhost:8899";
  },

  // Actions
  autoPaste: (text) => ipcRenderer.invoke("auto-paste", text),
  notify: (title, body) => ipcRenderer.invoke("notify", title, body),
  quit: () => ipcRenderer.invoke("quit-app"),

  // Context menu
  showContextMenu: (tones, currentTone) =>
    ipcRenderer.send("show-context-menu", tones, currentTone),

  // Settings
  openSettings: () => ipcRenderer.invoke("open-settings"),
  closeSettings: () => ipcRenderer.invoke("close-settings"),
  getCurrentHotkey: () => ipcRenderer.invoke("get-current-hotkey"),
  saveHotkey: (accelerator) => ipcRenderer.invoke("save-hotkey", accelerator),

  // Events from main process
  onToggleRecording: (callback) =>
    ipcRenderer.on("toggle-recording", () => callback()),

  onToneChanged: (callback) =>
    ipcRenderer.on("tone-changed", (_, tone) => callback(tone)),
});
