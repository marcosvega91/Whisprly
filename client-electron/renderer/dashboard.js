// ─── Tab Navigation ─────────────────────────────────────────────

const navItems = document.querySelectorAll(".nav-item");
const tabs = document.querySelectorAll(".tab");

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    const tabId = item.dataset.tab;
    navItems.forEach((n) => n.classList.remove("active"));
    item.classList.add("active");
    tabs.forEach((t) => {
      t.classList.toggle("hidden", t.id !== `tab-${tabId}`);
    });
  });
});

// ─── Utilities ──────────────────────────────────────────────────

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(isoStr) {
  const d = new Date(isoStr + "Z");
  const now = new Date();
  const diff = now - d;

  if (diff < 60000) return "Just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── History ────────────────────────────────────────────────────

const historyList = document.getElementById("history-list");
const historyEmpty = document.getElementById("history-empty");
const btnClearHistory = document.getElementById("btn-clear-history");

async function loadHistory() {
  const entries = await whisprly.getHistory();

  historyList.innerHTML = "";

  if (entries.length === 0) {
    historyEmpty.classList.remove("hidden");
    historyList.classList.add("hidden");
    btnClearHistory.style.display = "none";
    return;
  }

  historyEmpty.classList.add("hidden");
  historyList.classList.remove("hidden");
  btnClearHistory.style.display = "block";

  entries.forEach((entry) => {
    const el = document.createElement("div");
    el.className = "history-entry";
    el.innerHTML = `
      <div class="text">${escapeHtml(entry.clean_text)}</div>
      <div class="meta">
        <span class="meta-left">
          <span class="tone-badge">${escapeHtml(entry.tone)}</span>
          <span>${formatDate(entry.created_at)}</span>
        </span>
        <span class="actions">
          <button class="btn-copy">Copy</button>
          <button class="btn-delete">Delete</button>
        </span>
      </div>
    `;

    el.querySelector(".btn-copy").addEventListener("click", async (e) => {
      await whisprly.copyToClipboard(entry.clean_text);
      e.target.textContent = "Copied!";
      setTimeout(() => (e.target.textContent = "Copy"), 1200);
    });

    el.querySelector(".btn-delete").addEventListener("click", async () => {
      await whisprly.deleteHistoryEntry(entry.id);
      loadHistory();
    });

    historyList.appendChild(el);
  });
}

btnClearHistory.addEventListener("click", async () => {
  if (btnClearHistory.dataset.confirm === "true") {
    await whisprly.clearHistory();
    loadHistory();
    btnClearHistory.dataset.confirm = "";
    btnClearHistory.textContent = "Clear All";
  } else {
    btnClearHistory.dataset.confirm = "true";
    btnClearHistory.textContent = "Are you sure?";
    setTimeout(() => {
      btnClearHistory.dataset.confirm = "";
      btnClearHistory.textContent = "Clear All";
    }, 3000);
  }
});

whisprly.onHistoryUpdated(() => loadHistory());

// ─── Tone Selector ──────────────────────────────────────────────

const toneGrid = document.getElementById("tone-grid");

async function loadTones() {
  const tonesData = await whisprly.getTones();
  const activeTone = await whisprly.getCurrentTone();
  const config = await whisprly.getConfig();
  const presets = config.tone?.presets || {};

  toneGrid.innerHTML = "";

  tonesData.tones.forEach((tone) => {
    const card = document.createElement("div");
    card.className = `tone-card${tone === activeTone ? " selected" : ""}`;

    const preview = presets[tone]
      ? presets[tone].substring(0, 80) + "..."
      : "";

    card.innerHTML = `
      <div class="tone-name">${escapeHtml(tone)}</div>
      <div class="tone-preview">${escapeHtml(preview)}</div>
    `;

    card.addEventListener("click", async () => {
      await whisprly.setTone(tone);
      toneGrid.querySelectorAll(".tone-card").forEach((c) =>
        c.classList.remove("selected")
      );
      card.classList.add("selected");
    });

    toneGrid.appendChild(card);
  });
}

// ─── Hotkey Capture (ported from settings.js) ───────────────────

let originalHotkey = "";
let capturedAccelerator = "";
let isListening = false;

const hotkeyField = document.getElementById("hotkey-field");
const hotkeyDisplay = document.getElementById("hotkey-display");
const hotkeyStatus = document.getElementById("hotkey-status");
const btnSaveHotkey = document.getElementById("btn-save-hotkey");

const KEY_DISPLAY = {
  Meta: "\u2318",
  Control: "\u2303",
  Alt: "\u2325",
  Shift: "\u21E7",
};

const KEY_TO_ELECTRON = {
  Meta: "Command",
  Control: "Ctrl",
  Alt: "Alt",
  Shift: "Shift",
};

function keyToDisplay(key) {
  if (KEY_DISPLAY[key]) return KEY_DISPLAY[key];
  if (key === " ") return "Space";
  if (key.length === 1) return key.toUpperCase();
  return key;
}

function keyToElectron(key) {
  if (KEY_TO_ELECTRON[key]) return KEY_TO_ELECTRON[key];
  if (key === " ") return "Space";
  if (key.length === 1) return key.toUpperCase();
  const specials = {
    ArrowUp: "Up",
    ArrowDown: "Down",
    ArrowLeft: "Left",
    ArrowRight: "Right",
    Backspace: "Backspace",
    Delete: "Delete",
    Enter: "Return",
    Escape: "Escape",
    Tab: "Tab",
  };
  return specials[key] || key;
}

function renderKeys(accelerator) {
  if (!accelerator) {
    hotkeyDisplay.textContent = "Not set";
    return;
  }
  const parts = accelerator.split("+");
  hotkeyDisplay.innerHTML = parts
    .map((p) => {
      const symbols = { Command: "\u2318", Ctrl: "\u2303", Alt: "\u2325", Shift: "\u21E7" };
      const label = symbols[p] || p;
      return `<span class="key">${label}</span>`;
    })
    .join("");
}

const pressedKeys = new Set();

function startListening() {
  isListening = true;
  pressedKeys.clear();
  hotkeyField.classList.add("listening");
  hotkeyStatus.textContent = "Press keys...";
  hotkeyStatus.className = "listening";
  hotkeyDisplay.innerHTML = '<span style="color: #6366f1">Waiting for input...</span>';
}

function stopListening() {
  isListening = false;
  hotkeyField.classList.remove("listening");
}

hotkeyField.addEventListener("click", () => {
  if (!isListening) startListening();
});

hotkeyField.addEventListener("focus", () => {
  if (!isListening) startListening();
});

hotkeyField.addEventListener("blur", () => {
  if (isListening && pressedKeys.size === 0) {
    stopListening();
    renderKeys(capturedAccelerator || originalHotkey);
    hotkeyStatus.textContent = "";
    hotkeyStatus.className = "";
  }
});

document.addEventListener("keydown", (e) => {
  if (!isListening) return;
  e.preventDefault();
  e.stopPropagation();

  pressedKeys.add(e.key);

  const modifiers = [];
  const regular = [];
  for (const k of pressedKeys) {
    if (["Meta", "Control", "Alt", "Shift"].includes(k)) {
      modifiers.push(k);
    } else {
      regular.push(k);
    }
  }

  const modOrder = ["Control", "Alt", "Shift", "Meta"];
  modifiers.sort((a, b) => modOrder.indexOf(a) - modOrder.indexOf(b));

  const allKeys = [...modifiers, ...regular];
  hotkeyDisplay.innerHTML = allKeys
    .map((k) => `<span class="key">${keyToDisplay(k)}</span>`)
    .join("");
});

document.addEventListener("keyup", (e) => {
  if (!isListening) return;
  e.preventDefault();

  const modifiers = [];
  const regular = [];
  for (const k of pressedKeys) {
    if (["Meta", "Control", "Alt", "Shift"].includes(k)) {
      modifiers.push(k);
    } else {
      regular.push(k);
    }
  }

  if (modifiers.length === 0 || regular.length === 0) {
    pressedKeys.delete(e.key);
    if (pressedKeys.size === 0) {
      hotkeyStatus.textContent = "Need modifier + key (e.g. \u2318+Shift+Space)";
      hotkeyStatus.className = "error";
      renderKeys(capturedAccelerator || originalHotkey);
      stopListening();
    }
    return;
  }

  const modOrder = ["Control", "Alt", "Shift", "Meta"];
  modifiers.sort((a, b) => modOrder.indexOf(a) - modOrder.indexOf(b));

  const electronParts = [
    ...modifiers.map((k) => KEY_TO_ELECTRON[k]),
    ...regular.map((k) => keyToElectron(k)),
  ];
  capturedAccelerator = electronParts.join("+");

  pressedKeys.clear();
  stopListening();

  renderKeys(capturedAccelerator);

  const changed = capturedAccelerator !== originalHotkey;
  btnSaveHotkey.disabled = !changed;
  hotkeyStatus.textContent = changed ? "Modified" : "";
  hotkeyStatus.className = changed ? "changed" : "";
});

btnSaveHotkey.addEventListener("click", async () => {
  if (!capturedAccelerator || capturedAccelerator === originalHotkey) return;

  btnSaveHotkey.disabled = true;
  btnSaveHotkey.textContent = "Saving...";

  const result = await whisprly.saveHotkey(capturedAccelerator);

  if (result.success) {
    originalHotkey = capturedAccelerator;
    hotkeyStatus.textContent = "Saved!";
    hotkeyStatus.className = "changed";
    btnSaveHotkey.textContent = "Save Hotkey";
  } else {
    hotkeyStatus.textContent = result.error || "Failed to register hotkey";
    hotkeyStatus.className = "error";
    btnSaveHotkey.textContent = "Save Hotkey";
    btnSaveHotkey.disabled = false;
  }
});

// ─── Init ───────────────────────────────────────────────────────

async function init() {
  const [hotkey] = await Promise.all([
    whisprly.getCurrentHotkey(),
    loadHistory(),
    loadTones(),
  ]);

  originalHotkey = hotkey;
  capturedAccelerator = hotkey;
  renderKeys(hotkey);
  hotkeyStatus.textContent = "";
}

init();
