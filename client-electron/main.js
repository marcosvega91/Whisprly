const {
  app,
  BrowserWindow,
  globalShortcut,
  ipcMain,
  clipboard,
  Notification,
  Menu,
  screen,
} = require("electron");
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");
const yaml = require("js-yaml");
const { systemPreferences } = require("electron");
const historyDb = require("./db");

// ─── Configuration ──────────────────────────────────────────────

const CONFIG_PATH = path.join(__dirname, "..", "config.yaml");

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error("config.yaml not found!");
    process.exit(1);
  }
  return yaml.load(fs.readFileSync(CONFIG_PATH, "utf8"));
}

let config = {};
let mainWindow = null;
let dashboardWindow = null;
let currentToggleAccelerator = null;
let currentContextAccelerator = null;
let currentTone = "professionale";

// ─── Window ─────────────────────────────────────────────────────

function createWindow() {
  const { width: screenW, height: screenH } =
    screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 200,
    height: 200,
    x: screenW - 220,
    y: screenH - 220,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    focusable: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // Allow the window to be clicked through when not interacting
  mainWindow.setIgnoreMouseEvents(false);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ─── Dashboard Window ───────────────────────────────────────────

function openDashboard() {
  if (dashboardWindow) {
    dashboardWindow.focus();
    return;
  }

  if (process.platform === "darwin") app.dock.show();

  dashboardWindow = new BrowserWindow({
    width: 720,
    height: 520,
    minWidth: 600,
    minHeight: 400,
    resizable: true,
    titleBarStyle: "hiddenInset",
    vibrancy: "under-window",
    backgroundColor: "#1a1a2e",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  dashboardWindow.loadFile(
    path.join(__dirname, "renderer", "dashboard.html")
  );

  dashboardWindow.on("closed", () => {
    dashboardWindow = null;
    if (process.platform === "darwin") app.dock.hide();
  });
}

// ─── Hotkey Mapping ─────────────────────────────────────────────

function mapHotkeyToElectron(hotkeyStr) {
  if (!hotkeyStr) return null;

  const mapping = {
    "<ctrl>": "Ctrl",
    "<shift>": "Shift",
    "<alt>": "Alt",
    "<cmd>": "Command",
    cmd_r: "Command+Shift+Space", // Right Cmd not supported; use combo
    space: "Space",
    "<space>": "Space",
  };

  // Single key like 'cmd_r' → use fallback combo
  if (mapping[hotkeyStr]) return mapping[hotkeyStr];

  // Multi-key combo like '<ctrl>+<shift>+space'
  const parts = hotkeyStr.split("+").map((p) => p.trim());
  const mapped = parts.map((p) => {
    if (mapping[p]) return mapping[p];
    if (p.length === 1) return p.toUpperCase();
    // Try title case
    return p.charAt(0).toUpperCase() + p.slice(1);
  });

  return mapped.join("+");
}

// ─── IPC Handlers ───────────────────────────────────────────────

function setupIPC() {
  ipcMain.handle("get-config", () => config);

  ipcMain.handle("get-tones", async () => {
    const serverUrl =
      config.server?.url || "http://localhost:8899";
    try {
      const resp = await fetch(`${serverUrl}/tones`);
      if (resp.ok) return await resp.json();
    } catch (_) {
      // Fallback to config
    }
    const presets = Object.keys(config.tone?.presets || {});
    const custom = Object.keys(config.tone?.custom_tones || {});
    return {
      tones: [...presets, ...custom],
      default: config.tone?.default || "professionale",
    };
  });

  ipcMain.handle("check-health", async () => {
    const serverUrl =
      config.server?.url || "http://localhost:8899";
    try {
      const resp = await fetch(`${serverUrl}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      return resp.ok;
    } catch (_) {
      return false;
    }
  });

  ipcMain.handle("auto-paste", (_, text) => {
    clipboard.writeText(text);
    // Small delay then simulate Cmd+V
    return new Promise((resolve) => {
      setTimeout(() => {
        try {
          execSync(
            'osascript -e \'tell application "System Events" to keystroke "v" using command down\''
          );
          resolve(true);
        } catch (e) {
          console.error("Auto-paste failed:", e.message);
          resolve(false);
        }
      }, 100);
    });
  });

  ipcMain.handle("notify", (_, title, body) => {
    if (Notification.isSupported()) {
      new Notification({ title, body, silent: true }).show();
    }
  });

  ipcMain.on("show-context-menu", (event, tones) => {
    const toneItems = tones.map((tone) => ({
      label: tone.charAt(0).toUpperCase() + tone.slice(1),
      type: "radio",
      checked: tone === currentTone,
      click: () => {
        currentTone = tone;
        event.sender.send("tone-changed", tone);
      },
    }));

    const menu = Menu.buildFromTemplate([
      { label: "Whisprly", enabled: false },
      { type: "separator" },
      { label: "Voice Tone", submenu: toneItems },
      { type: "separator" },
      {
        label: "Dashboard...",
        click: () => openDashboard(),
      },
      {
        label: "Quit",
        click: () => app.quit(),
      },
    ]);

    menu.popup({ window: BrowserWindow.fromWebContents(event.sender) });
  });

  ipcMain.handle("quit-app", () => app.quit());

  // ─── Dashboard IPC ─────────────────────────────────────────────

  ipcMain.handle("open-dashboard", () => openDashboard());

  ipcMain.handle("close-dashboard", () => {
    if (dashboardWindow) dashboardWindow.close();
  });

  ipcMain.handle("get-current-hotkey", () => {
    return currentToggleAccelerator || "Command+Shift+Space";
  });

  ipcMain.handle("get-current-context-hotkey", () => {
    return currentContextAccelerator || "Command+Shift+R";
  });

  ipcMain.handle("save-hotkey", (_, accelerator) => {
    try {
      if (currentToggleAccelerator) {
        globalShortcut.unregister(currentToggleAccelerator);
      }

      const ok = globalShortcut.register(accelerator, () => {
        if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send("toggle-recording");
      });

      if (!ok) {
        if (currentToggleAccelerator) {
          globalShortcut.register(currentToggleAccelerator, () => {
            if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send("toggle-recording");
          });
        }
        return { success: false, error: "Shortcut already in use by another app" };
      }

      const raw = fs.readFileSync(CONFIG_PATH, "utf8");
      const updated = raw.replace(
        /^(\s*toggle_recording:\s*).+$/m,
        `$1${accelerator}`
      );
      fs.writeFileSync(CONFIG_PATH, updated, "utf8");

      currentToggleAccelerator = accelerator;
      console.log(`Hotkey updated: ${accelerator}`);
      return { success: true };
    } catch (e) {
      console.error("Failed to save hotkey:", e);
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle("save-context-hotkey", (_, accelerator) => {
    try {
      if (currentContextAccelerator) {
        globalShortcut.unregister(currentContextAccelerator);
      }

      const ok = globalShortcut.register(accelerator, () => {
        captureContextAndRecord();
      });

      if (!ok) {
        if (currentContextAccelerator) {
          globalShortcut.register(currentContextAccelerator, () => {
            captureContextAndRecord();
          });
        }
        return { success: false, error: "Shortcut already in use by another app" };
      }

      const raw = fs.readFileSync(CONFIG_PATH, "utf8");
      const updated = raw.replace(
        /^(\s*context_recording:\s*).+$/m,
        `$1${accelerator}`
      );
      fs.writeFileSync(CONFIG_PATH, updated, "utf8");

      currentContextAccelerator = accelerator;
      console.log(`Context hotkey updated: ${accelerator}`);
      return { success: true };
    } catch (e) {
      console.error("Failed to save context hotkey:", e);
      return { success: false, error: e.message };
    }
  });

  // ─── Tone IPC ─────────────────────────────────────────────────

  ipcMain.handle("get-current-tone", () => currentTone);

  ipcMain.handle("set-tone", (_, tone) => {
    currentTone = tone;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("tone-changed", tone);
    }
    return { success: true };
  });

  // ─── History IPC ──────────────────────────────────────────────

  ipcMain.handle("save-history-entry", (_, { cleanText, rawText, tone }) => {
    try {
      historyDb.addEntry(cleanText, rawText, tone);
      if (dashboardWindow && !dashboardWindow.isDestroyed()) {
        dashboardWindow.webContents.send("history-updated");
      }
      return { success: true };
    } catch (e) {
      console.error("Failed to save history entry:", e);
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle("get-history", () => {
    try {
      return historyDb.getEntries();
    } catch (e) {
      console.error("Failed to get history:", e);
      return [];
    }
  });

  ipcMain.handle("delete-history-entry", (_, id) => {
    try {
      historyDb.deleteEntry(id);
      return { success: true };
    } catch (e) {
      console.error("Failed to delete history entry:", e);
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle("clear-history", () => {
    try {
      historyDb.clearAll();
      return { success: true };
    } catch (e) {
      console.error("Failed to clear history:", e);
      return { success: false, error: e.message };
    }
  });

  ipcMain.handle("copy-to-clipboard", (_, text) => {
    clipboard.writeText(text);
    return { success: true };
  });
}

// ─── Context Capture ─────────────────────────────────────────────

function captureContextAndRecord() {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  // Copy selected text via Cmd+C
  try {
    execSync(
      'osascript -e \'tell application "System Events" to keystroke "c" using command down\''
    );
  } catch (e) {
    console.error("Failed to copy context:", e.message);
  }

  // Wait for clipboard to populate, then read and send to renderer
  setTimeout(() => {
    const contextText = clipboard.readText() || "";
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("toggle-recording-with-context", contextText);
    }
  }, 150);
}

// ─── Hotkeys ────────────────────────────────────────────────────

function registerHotkeys() {
  const hotkeyCfg = config.hotkeys || {};

  const toggleKey = mapHotkeyToElectron(
    hotkeyCfg.toggle_recording || "<ctrl>+<shift>+space"
  );
  const contextKey = mapHotkeyToElectron(
    hotkeyCfg.context_recording || "<cmd>+<shift>+r"
  );
  const quitKey = mapHotkeyToElectron(
    hotkeyCfg.quit || "<ctrl>+<shift>+q"
  );

  if (toggleKey) {
    const ok = globalShortcut.register(toggleKey, () => {
      if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send("toggle-recording");
    });
    if (ok) currentToggleAccelerator = toggleKey;
    console.log(
      ok
        ? `Hotkey registered: ${toggleKey}`
        : `Failed to register hotkey: ${toggleKey}`
    );
  }

  if (contextKey) {
    const ok = globalShortcut.register(contextKey, () => {
      captureContextAndRecord();
    });
    if (ok) currentContextAccelerator = contextKey;
    console.log(
      ok
        ? `Context hotkey registered: ${contextKey}`
        : `Failed to register context hotkey: ${contextKey}`
    );
  }

  if (quitKey) {
    const ok = globalShortcut.register(quitKey, () => app.quit());
    console.log(
      ok
        ? `Quit hotkey registered: ${quitKey}`
        : `Failed to register quit hotkey: ${quitKey}`
    );
  }
}

// ─── macOS Permissions ──────────────────────────────────────────

async function checkPermissions() {
  if (process.platform !== "darwin") return;

  // 1. Microphone — triggers system prompt if not yet granted
  const micStatus = systemPreferences.getMediaAccessStatus("microphone");
  if (micStatus !== "granted") {
    console.log("Requesting microphone access...");
    const granted = await systemPreferences.askForMediaAccess("microphone");
    if (!granted) {
      console.error(
        "Microphone access denied. Grant it in: System Settings > Privacy & Security > Microphone"
      );
    }
  }

  // 2. Accessibility — needed for auto-paste (osascript keystroke simulation)
  const trusted = systemPreferences.isTrustedAccessibilityClient(true);
  if (!trusted) {
    console.log(
      "Accessibility access needed for auto-paste.\n" +
        "  Grant it in: System Settings > Privacy & Security > Accessibility\n" +
        "  Add the Electron app (or Terminal if running via npm start)."
    );
  }

  // 3. Input Monitoring — globalShortcut may need this on some macOS versions
  //    (Electron usually handles this via Accessibility, but log a hint)
  console.log(
    `Permissions: mic=${micStatus === "granted" ? "OK" : micStatus}, ` +
      `accessibility=${trusted ? "OK" : "DENIED"}`
  );
}

// ─── App Lifecycle ──────────────────────────────────────────────

// Hide dock icon on macOS
if (process.platform === "darwin") {
  app.dock.hide();
}

app.whenReady().then(async () => {
  config = loadConfig();
  currentTone = config.tone?.default || "professionale";

  historyDb.init(app.getPath("userData"));

  // Show dock briefly so permission dialogs can appear
  if (process.platform === "darwin") {
    app.dock.show();
  }

  await checkPermissions();

  // Hide dock again after permissions are handled
  if (process.platform === "darwin") {
    app.dock.hide();
  }

  setupIPC();
  createWindow();
  registerHotkeys();

  console.log("Whisprly Electron client started");
  console.log(`Server: ${config.server?.url || "http://localhost:8899"}`);
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
  historyDb.close();
});

app.on("window-all-closed", (e) => {
  // Don't quit — the floating widget may have been hidden, not closed
  // App quits via context menu "Quit" or quit hotkey
});
