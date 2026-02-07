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

// ─── Hotkey Capture ─────────────────────────────────────────────

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

function renderKeysInto(displayEl, accelerator) {
  if (!accelerator) {
    displayEl.textContent = "Not set";
    return;
  }
  const parts = accelerator.split("+");
  displayEl.innerHTML = parts
    .map((p) => {
      const symbols = { Command: "\u2318", Ctrl: "\u2303", Alt: "\u2325", Shift: "\u21E7" };
      const label = symbols[p] || p;
      return `<span class="key">${label}</span>`;
    })
    .join("");
}

// Shared state for whichever field is currently active
let activeCapture = null;
const pressedKeys = new Set();

function createHotkeyCapture({ fieldEl, displayEl, statusEl, saveBtn, saveFn }) {
  let original = "";
  let captured = "";

  function startListening() {
    // Stop any other active capture
    if (activeCapture && activeCapture !== capture) {
      activeCapture.stop();
    }
    activeCapture = capture;
    pressedKeys.clear();
    fieldEl.classList.add("listening");
    statusEl.textContent = "Press keys...";
    statusEl.className = "listening";
    displayEl.innerHTML = '<span style="color: #6366f1">Waiting for input...</span>';
  }

  function stopListening() {
    if (activeCapture === capture) activeCapture = null;
    fieldEl.classList.remove("listening");
  }

  const capture = {
    stop: () => {
      stopListening();
      renderKeysInto(displayEl, captured || original);
      statusEl.textContent = "";
      statusEl.className = "";
    },
    isActive: () => activeCapture === capture,
    setOriginal: (val) => { original = val; captured = val; },
    render: () => renderKeysInto(displayEl, original),
    handleKeyDown: (e) => {
      pressedKeys.add(e.key);
      const modifiers = [];
      const regular = [];
      for (const k of pressedKeys) {
        if (["Meta", "Control", "Alt", "Shift"].includes(k)) modifiers.push(k);
        else regular.push(k);
      }
      const modOrder = ["Control", "Alt", "Shift", "Meta"];
      modifiers.sort((a, b) => modOrder.indexOf(a) - modOrder.indexOf(b));
      displayEl.innerHTML = [...modifiers, ...regular]
        .map((k) => `<span class="key">${keyToDisplay(k)}</span>`)
        .join("");
    },
    handleKeyUp: (e) => {
      const modifiers = [];
      const regular = [];
      for (const k of pressedKeys) {
        if (["Meta", "Control", "Alt", "Shift"].includes(k)) modifiers.push(k);
        else regular.push(k);
      }
      if (modifiers.length === 0 || regular.length === 0) {
        pressedKeys.delete(e.key);
        if (pressedKeys.size === 0) {
          statusEl.textContent = "Need modifier + key (e.g. \u2318+Shift+Space)";
          statusEl.className = "error";
          renderKeysInto(displayEl, captured || original);
          stopListening();
        }
        return;
      }
      const modOrder = ["Control", "Alt", "Shift", "Meta"];
      modifiers.sort((a, b) => modOrder.indexOf(a) - modOrder.indexOf(b));
      captured = [
        ...modifiers.map((k) => KEY_TO_ELECTRON[k]),
        ...regular.map((k) => keyToElectron(k)),
      ].join("+");
      pressedKeys.clear();
      stopListening();
      renderKeysInto(displayEl, captured);
      const changed = captured !== original;
      saveBtn.disabled = !changed;
      statusEl.textContent = changed ? "Modified" : "";
      statusEl.className = changed ? "changed" : "";
    },
  };

  fieldEl.addEventListener("click", () => { if (!capture.isActive()) startListening(); });
  fieldEl.addEventListener("focus", () => { if (!capture.isActive()) startListening(); });
  fieldEl.addEventListener("blur", () => {
    if (capture.isActive() && pressedKeys.size === 0) capture.stop();
  });

  saveBtn.addEventListener("click", async () => {
    if (!captured || captured === original) return;
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
    const result = await saveFn(captured);
    if (result.success) {
      original = captured;
      statusEl.textContent = "Saved!";
      statusEl.className = "changed";
    } else {
      statusEl.textContent = result.error || "Failed to register hotkey";
      statusEl.className = "error";
      saveBtn.disabled = false;
    }
    saveBtn.textContent = "Save";
  });

  return capture;
}

const recordingCapture = createHotkeyCapture({
  fieldEl: document.getElementById("hotkey-field"),
  displayEl: document.getElementById("hotkey-display"),
  statusEl: document.getElementById("hotkey-status"),
  saveBtn: document.getElementById("btn-save-hotkey"),
  saveFn: (acc) => whisprly.saveHotkey(acc),
});

const contextCapture = createHotkeyCapture({
  fieldEl: document.getElementById("context-hotkey-field"),
  displayEl: document.getElementById("context-hotkey-display"),
  statusEl: document.getElementById("context-hotkey-status"),
  saveBtn: document.getElementById("btn-save-context-hotkey"),
  saveFn: (acc) => whisprly.saveContextHotkey(acc),
});

document.addEventListener("keydown", (e) => {
  if (!activeCapture) return;
  e.preventDefault();
  e.stopPropagation();
  activeCapture.handleKeyDown(e);
});

document.addEventListener("keyup", (e) => {
  if (!activeCapture) return;
  e.preventDefault();
  activeCapture.handleKeyUp(e);
});

// ─── Init ───────────────────────────────────────────────────────

async function init() {
  const [hotkey, contextHotkey] = await Promise.all([
    whisprly.getCurrentHotkey(),
    whisprly.getCurrentContextHotkey(),
    loadHistory(),
    loadTones(),
  ]);

  recordingCapture.setOriginal(hotkey);
  recordingCapture.render();

  contextCapture.setOriginal(contextHotkey);
  contextCapture.render();
}

init();
