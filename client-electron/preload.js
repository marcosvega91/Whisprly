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

  // Dashboard
  openDashboard: () => ipcRenderer.invoke("open-dashboard"),
  closeDashboard: () => ipcRenderer.invoke("close-dashboard"),
  getCurrentHotkey: () => ipcRenderer.invoke("get-current-hotkey"),
  saveHotkey: (accelerator) => ipcRenderer.invoke("save-hotkey", accelerator),

  // Tone
  getCurrentTone: () => ipcRenderer.invoke("get-current-tone"),
  setTone: (tone) => ipcRenderer.invoke("set-tone", tone),

  // History
  saveHistoryEntry: (data) => ipcRenderer.invoke("save-history-entry", data),
  getHistory: () => ipcRenderer.invoke("get-history"),
  deleteHistoryEntry: (id) => ipcRenderer.invoke("delete-history-entry", id),
  clearHistory: () => ipcRenderer.invoke("clear-history"),
  copyToClipboard: (text) => ipcRenderer.invoke("copy-to-clipboard", text),

  // Events from main process
  onToggleRecording: (callback) =>
    ipcRenderer.on("toggle-recording", () => callback()),

  onToneChanged: (callback) =>
    ipcRenderer.on("tone-changed", (_, tone) => callback(tone)),

  onHistoryUpdated: (callback) =>
    ipcRenderer.on("history-updated", () => callback()),
});
