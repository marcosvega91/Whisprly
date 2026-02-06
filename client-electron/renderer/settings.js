// ─── State ───────────────────────────────────────────────────────

let originalHotkey = "";
let capturedAccelerator = "";
let isListening = false;

const field = document.getElementById("hotkey-field");
const display = document.getElementById("hotkey-display");
const status = document.getElementById("hotkey-status");
const btnSave = document.getElementById("btn-save");
const btnCancel = document.getElementById("btn-cancel");

// ─── Key Mapping ─────────────────────────────────────────────────

const KEY_DISPLAY = {
  Meta: "\u2318",     // ⌘
  Control: "\u2303",  // ⌃
  Alt: "\u2325",      // ⌥
  Shift: "\u21E7",    // ⇧
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
  // Handle special keys
  const specials = {
    ArrowUp: "Up", ArrowDown: "Down", ArrowLeft: "Left", ArrowRight: "Right",
    Backspace: "Backspace", Delete: "Delete", Enter: "Return",
    Escape: "Escape", Tab: "Tab",
  };
  return specials[key] || key;
}

function renderKeys(accelerator) {
  if (!accelerator) {
    display.textContent = "Not set";
    return;
  }
  const parts = accelerator.split("+");
  display.innerHTML = parts
    .map((p) => {
      // Convert Electron accelerator parts to display symbols
      const symbols = { Command: "\u2318", Ctrl: "\u2303", Alt: "\u2325", Shift: "\u21E7" };
      const label = symbols[p] || p;
      return `<span class="key">${label}</span>`;
    })
    .join("");
}

// ─── Hotkey Capture ──────────────────────────────────────────────

const pressedKeys = new Set();

function startListening() {
  isListening = true;
  pressedKeys.clear();
  field.classList.add("listening");
  status.textContent = "Press keys...";
  status.className = "listening";
  display.innerHTML = '<span style="color: #6366f1">Waiting for input...</span>';
}

function stopListening() {
  isListening = false;
  field.classList.remove("listening");
}

field.addEventListener("click", () => {
  if (!isListening) startListening();
});

field.addEventListener("focus", () => {
  if (!isListening) startListening();
});

field.addEventListener("blur", () => {
  if (isListening && pressedKeys.size === 0) {
    stopListening();
    renderKeys(capturedAccelerator || originalHotkey);
    status.textContent = "";
    status.className = "";
  }
});

document.addEventListener("keydown", (e) => {
  if (!isListening) return;
  e.preventDefault();
  e.stopPropagation();

  pressedKeys.add(e.key);

  // Build a display of currently pressed keys
  const modifiers = [];
  const regular = [];
  for (const k of pressedKeys) {
    if (["Meta", "Control", "Alt", "Shift"].includes(k)) {
      modifiers.push(k);
    } else {
      regular.push(k);
    }
  }

  // Sort modifiers in standard order
  const modOrder = ["Control", "Alt", "Shift", "Meta"];
  modifiers.sort((a, b) => modOrder.indexOf(a) - modOrder.indexOf(b));

  const allKeys = [...modifiers, ...regular];
  display.innerHTML = allKeys
    .map((k) => `<span class="key">${keyToDisplay(k)}</span>`)
    .join("");
});

document.addEventListener("keyup", (e) => {
  if (!isListening) return;
  e.preventDefault();

  // Capture on key release — build the final accelerator
  const modifiers = [];
  const regular = [];
  for (const k of pressedKeys) {
    if (["Meta", "Control", "Alt", "Shift"].includes(k)) {
      modifiers.push(k);
    } else {
      regular.push(k);
    }
  }

  // Need at least one modifier + one regular key
  if (modifiers.length === 0 || regular.length === 0) {
    pressedKeys.delete(e.key);
    if (pressedKeys.size === 0) {
      status.textContent = "Need modifier + key (e.g. \u2318+Shift+Space)";
      status.className = "error";
      renderKeys(capturedAccelerator || originalHotkey);
      stopListening();
    }
    return;
  }

  // Build Electron accelerator string
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

  // Enable save if changed
  const changed = capturedAccelerator !== originalHotkey;
  btnSave.disabled = !changed;
  status.textContent = changed ? "Modified" : "";
  status.className = changed ? "changed" : "";
});

// ─── Buttons ─────────────────────────────────────────────────────

btnCancel.addEventListener("click", () => {
  whisprly.closeSettings();
});

btnSave.addEventListener("click", async () => {
  if (!capturedAccelerator || capturedAccelerator === originalHotkey) return;

  btnSave.disabled = true;
  btnSave.textContent = "Saving...";

  const result = await whisprly.saveHotkey(capturedAccelerator);

  if (result.success) {
    originalHotkey = capturedAccelerator;
    status.textContent = "Saved!";
    status.className = "changed";
    btnSave.textContent = "Save";

    // Close after brief delay
    setTimeout(() => whisprly.closeSettings(), 600);
  } else {
    status.textContent = result.error || "Failed to register hotkey";
    status.className = "error";
    btnSave.textContent = "Save";
    btnSave.disabled = false;
  }
});

// ─── Escape to close ─────────────────────────────────────────────

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !isListening) {
    whisprly.closeSettings();
  }
});

// ─── Init ────────────────────────────────────────────────────────

async function init() {
  const hotkey = await whisprly.getCurrentHotkey();
  originalHotkey = hotkey;
  capturedAccelerator = hotkey;
  renderKeys(hotkey);
  status.textContent = "";
}

init();
