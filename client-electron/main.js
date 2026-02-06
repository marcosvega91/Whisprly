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
let settingsWindow = null;
let currentToggleAccelerator = null;

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

// ─── Settings Window ────────────────────────────────────────────

function openSettings() {
  if (settingsWindow) {
    settingsWindow.focus();
    return;
  }

  // Show dock so the settings window behaves like a normal app
  if (process.platform === "darwin") app.dock.show();

  settingsWindow = new BrowserWindow({
    width: 420,
    height: 320,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    titleBarStyle: "hiddenInset",
    vibrancy: "under-window",
    backgroundColor: "#1a1a2e",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  settingsWindow.loadFile(
    path.join(__dirname, "renderer", "settings.html")
  );

  settingsWindow.on("closed", () => {
    settingsWindow = null;
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

  ipcMain.on("show-context-menu", (event, tones, currentTone) => {
    const toneItems = tones.map((tone) => ({
      label: tone.charAt(0).toUpperCase() + tone.slice(1),
      type: "radio",
      checked: tone === currentTone,
      click: () => {
        event.sender.send("tone-changed", tone);
      },
    }));

    const menu = Menu.buildFromTemplate([
      { label: "Whisprly", enabled: false },
      { type: "separator" },
      { label: "Voice Tone", submenu: toneItems },
      { type: "separator" },
      {
        label: "Settings...",
        click: () => openSettings(),
      },
      {
        label: "Quit",
        click: () => app.quit(),
      },
    ]);

    menu.popup({ window: BrowserWindow.fromWebContents(event.sender) });
  });

  ipcMain.handle("quit-app", () => app.quit());

  // ─── Settings IPC ──────────────────────────────────────────────

  ipcMain.handle("open-settings", () => openSettings());

  ipcMain.handle("close-settings", () => {
    if (settingsWindow) settingsWindow.close();
  });

  ipcMain.handle("get-current-hotkey", () => {
    return currentToggleAccelerator || "Command+Shift+Space";
  });

  ipcMain.handle("save-hotkey", (_, accelerator) => {
    // 1. Try registering the new shortcut
    try {
      // Unregister old toggle shortcut
      if (currentToggleAccelerator) {
        globalShortcut.unregister(currentToggleAccelerator);
      }

      const ok = globalShortcut.register(accelerator, () => {
        if (mainWindow) mainWindow.webContents.send("toggle-recording");
      });

      if (!ok) {
        // Re-register old one
        if (currentToggleAccelerator) {
          globalShortcut.register(currentToggleAccelerator, () => {
            if (mainWindow) mainWindow.webContents.send("toggle-recording");
          });
        }
        return { success: false, error: "Shortcut already in use by another app" };
      }

      // 2. Save to config.yaml (preserve formatting, only replace the hotkey line)
      const raw = fs.readFileSync(CONFIG_PATH, "utf8");
      const updated = raw.replace(
        /^(\s*toggle_recording:\s*).+$/m,
        `$1${accelerator}`
      );
      fs.writeFileSync(CONFIG_PATH, updated, "utf8");

      // 3. Update state
      currentToggleAccelerator = accelerator;
      config.hotkeys = cfg.hotkeys;

      console.log(`Hotkey updated: ${accelerator}`);
      return { success: true };
    } catch (e) {
      console.error("Failed to save hotkey:", e);
      return { success: false, error: e.message };
    }
  });
}

// ─── Hotkeys ────────────────────────────────────────────────────

function registerHotkeys() {
  const hotkeyCfg = config.hotkeys || {};

  const toggleKey = mapHotkeyToElectron(
    hotkeyCfg.toggle_recording || "<ctrl>+<shift>+space"
  );
  const quitKey = mapHotkeyToElectron(
    hotkeyCfg.quit || "<ctrl>+<shift>+q"
  );

  if (toggleKey) {
    const ok = globalShortcut.register(toggleKey, () => {
      if (mainWindow) mainWindow.webContents.send("toggle-recording");
    });
    if (ok) currentToggleAccelerator = toggleKey;
    console.log(
      ok
        ? `Hotkey registered: ${toggleKey}`
        : `Failed to register hotkey: ${toggleKey}`
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
});

app.on("window-all-closed", (e) => {
  // Don't quit — the floating widget may have been hidden, not closed
  // App quits via context menu "Quit" or quit hotkey
});
