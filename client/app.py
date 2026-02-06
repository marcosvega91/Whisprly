"""
Whisprly Client — Lightweight macOS client.
Records audio locally, sends to Docker server for transcription and cleanup,
and auto-pastes the result into the focused input field.
"""

import sys
import subprocess
import threading
import time
import yaml
import pyperclip
import requests
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pynput import keyboard
import pystray

from core.recorder import AudioRecorder
from core.notifier import notify


# ─── App State ──────────────────────────────────────────────────

class AppState:
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"

    def __init__(self):
        self.status = self.IDLE
        self.current_tone = "professionale"
        self.available_tones: list[str] = []
        self._lock = threading.Lock()

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status

    def set_tone(self, tone: str) -> None:
        with self._lock:
            self.current_tone = tone


# ─── Configuration ──────────────────────────────────────────────

def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if not config_path.exists():
        print("config.yaml not found!")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─── Tray Icon ──────────────────────────────────────────────────

def create_icon_image(color: str = "#4CAF50") -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    mic_color = "white"
    draw.rounded_rectangle([24, 14, 40, 38], radius=6, fill=mic_color)
    draw.arc([18, 26, 46, 48], start=0, end=180, fill=mic_color, width=3)
    draw.line([32, 48, 32, 54], fill=mic_color, width=3)
    draw.line([24, 54, 40, 54], fill=mic_color, width=3)
    return img


ICON_COLORS = {
    AppState.IDLE: "#4CAF50",
    AppState.RECORDING: "#F44336",
    AppState.PROCESSING: "#FF9800",
}


def update_tray_icon(icon: pystray.Icon | None, state: AppState) -> None:
    if icon is None:
        return
    try:
        color = ICON_COLORS.get(state.status, ICON_COLORS[AppState.IDLE])
        icon.icon = create_icon_image(color)
    except Exception:
        pass


# ─── Auto-Paste ─────────────────────────────────────────────────

def auto_paste(text: str) -> None:
    """Copy text to clipboard and simulate Cmd+V to paste into the focused field."""
    pyperclip.copy(text)
    time.sleep(0.1)  # Small delay to ensure clipboard is ready
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke "v" using command down'],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Auto-paste failed: {e}. Text is still in the clipboard.")


# ─── Pipeline (via Server) ──────────────────────────────────────

def process_audio(
    audio_bytes: bytes,
    server_url: str,
    state: AppState,
    tray_icon: pystray.Icon | None = None,
) -> None:
    """Send audio to the server and paste the result."""
    try:
        state.set_status(AppState.PROCESSING)
        update_tray_icon(tray_icon, state)
        notify("Whisprly", "Processing...")

        # Send to server
        response = requests.post(
            f"{server_url}/process",
            files={"audio": ("recording.wav", audio_bytes, "audio/wav")},
            data={"tone": state.current_tone},
            timeout=60,
        )

        if response.status_code != 200:
            error = response.json().get("detail", "Unknown error")
            notify("Whisprly", f"Server error: {error}")
            return

        result = response.json()
        raw_text = result["raw_text"]
        clean_text = result["clean_text"]

        print(f"\nRaw transcription:\n{raw_text}\n")
        print(f"Cleaned text:\n{clean_text}\n")

        # Auto-paste into the focused field
        auto_paste(clean_text)

        preview = clean_text[:100] + ("..." if len(clean_text) > 100 else "")
        notify("Whisprly", f"Pasted!\n{preview}")

    except requests.ConnectionError:
        notify("Whisprly", "Server unreachable. Is Docker running?")
    except requests.Timeout:
        notify("Whisprly", "Timeout: the server did not respond in time.")
    except Exception as e:
        print(f"Error: {e}")
        notify("Whisprly", f"Error: {str(e)[:100]}")
    finally:
        state.set_status(AppState.IDLE)
        update_tray_icon(tray_icon, state)


# ─── Hotkey ─────────────────────────────────────────────────────

def parse_hotkey(hotkey_str: str) -> set:
    key_map = {
        "<ctrl>": keyboard.Key.ctrl_l,
        "<shift>": keyboard.Key.shift_l,
        "<alt>": keyboard.Key.alt_l,
        "<cmd>": keyboard.Key.cmd,
        "cmd_r": keyboard.Key.cmd_r,
        "space": keyboard.Key.space,
        "<space>": keyboard.Key.space,
    }
    parts = hotkey_str.lower().replace("+", " ").split()
    keys = set()
    for part in parts:
        part = part.strip()
        if part in key_map:
            keys.add(key_map[part])
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            try:
                keys.add(getattr(keyboard.Key, part))
            except AttributeError:
                print(f"Unrecognized key: {part}")
    return keys


class HotkeyManager:
    """Manages global hotkeys. Supports both combos (e.g. ctrl+shift+space)
    and single modifiers as tap-to-toggle (e.g. cmd_r)."""

    def __init__(self):
        self._pressed_keys: set = set()
        self._callbacks: dict[frozenset, callable] = {}
        self._tap_callbacks: dict = {}  # key -> callback for single modifier
        self._listener: keyboard.Listener | None = None
        self._other_key_pressed = False  # True if other keys pressed during modifier

    def register(self, hotkey_str: str, callback: callable) -> None:
        keys = parse_hotkey(hotkey_str)
        if len(keys) == 1:
            # Single key: use tap-to-toggle (activates on release, only if pressed alone)
            key = next(iter(keys))
            self._tap_callbacks[key] = callback
            print(f"Hotkey registered (tap): {hotkey_str}")
        else:
            self._callbacks[frozenset(keys)] = callback
            print(f"Hotkey registered: {hotkey_str}")

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def _on_press(self, key) -> None:
        self._pressed_keys.add(key)

        # For tap-to-toggle: if the modifier is already pressed and another key arrives,
        # it means it's a combo (e.g. Cmd+C), not a single tap
        if key not in self._tap_callbacks:
            self._other_key_pressed = True

        # Check multi-key combos (normalizing _r -> _l)
        normalized = set()
        for k in self._pressed_keys:
            if hasattr(k, 'name') and k.name.endswith('_r'):
                try:
                    normalized.add(getattr(keyboard.Key, k.name.replace('_r', '_l')))
                except AttributeError:
                    normalized.add(k)
            else:
                normalized.add(k)

        frozen = frozenset(normalized)
        for combo, callback in self._callbacks.items():
            if combo.issubset(frozen):
                callback()

    def _on_release(self, key) -> None:
        # Tap-to-toggle: activate only if the modifier was pressed and released alone
        if key in self._tap_callbacks and not self._other_key_pressed:
            self._tap_callbacks[key]()

        self._pressed_keys.discard(key)

        # Reset flag when all keys are released
        if not self._pressed_keys:
            self._other_key_pressed = False


# ─── Tray Menu ──────────────────────────────────────────────────

def create_tray_menu(state: AppState, tones: list[str]) -> pystray.Menu:
    def make_tone_handler(tone_name):
        def handler(icon, item):
            state.set_tone(tone_name)
            notify("Whisprly", f"Tone changed: {tone_name}")
            icon.menu = create_tray_menu(state, tones)
        return handler

    def is_current_tone(tone_name):
        def check(item):
            return state.current_tone == tone_name
        return check

    tone_items = []
    for tone in tones:
        tone_items.append(
            pystray.MenuItem(
                tone.capitalize(),
                make_tone_handler(tone),
                checked=is_current_tone(tone),
                radio=True,
            )
        )

    return pystray.Menu(
        pystray.MenuItem(
            lambda text: f"Status: {state.status.upper()}",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Voice Tone", pystray.Menu(*tone_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )


# ─── Main ───────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Whisprly Client — Voice Dictation")
    print("=" * 50)

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    config = load_config()

    # Server URL
    server_cfg = config.get("server", {})
    server_url = server_cfg.get("url", "http://localhost:8899")

    # Check server connection
    print(f"Connecting to server: {server_url}")
    try:
        r = requests.get(f"{server_url}/health", timeout=5)
        if r.status_code == 200:
            print("Server reachable!")
        else:
            print(f"Server responded with status {r.status_code}")
    except requests.ConnectionError:
        print("Server unreachable. Start Docker with: docker compose up -d")
        print("   The client will continue, but dictation won't work until the server is running.\n")

    # Load tones from server or fallback from config
    tones = []
    default_tone = config.get("tone", {}).get("default", "professionale")
    try:
        r = requests.get(f"{server_url}/tones", timeout=5)
        if r.status_code == 200:
            data = r.json()
            tones = data["tones"]
            default_tone = data["default"]
    except Exception:
        tone_cfg = config.get("tone", {})
        tones = list(tone_cfg.get("presets", {}).keys())
        custom = tone_cfg.get("custom_tones", {}) or {}
        tones.extend(custom.keys())

    # Audio recorder
    audio_cfg = config.get("audio", {})
    recorder = AudioRecorder(
        sample_rate=audio_cfg.get("sample_rate", 16000),
        channels=audio_cfg.get("channels", 1),
        dtype=audio_cfg.get("dtype", "int16"),
    )

    # App state
    state = AppState()
    state.current_tone = default_tone
    state.available_tones = tones

    tray_ref = {"icon": None}
    last_toggle_time = {"t": 0.0}

    def toggle_recording():
        now = time.time()
        if now - last_toggle_time["t"] < 0.5:
            return
        last_toggle_time["t"] = now

        if state.status == AppState.PROCESSING:
            return

        if not recorder.is_recording:
            recorder.start()
            state.set_status(AppState.RECORDING)
            update_tray_icon(tray_ref["icon"], state)
            notify("Whisprly", "Recording started... Press again to stop.")
            print("Recording started...")
        else:
            audio_data = recorder.stop()
            duration = recorder.get_duration()
            print(f"Recording stopped ({duration:.1f}s)")

            if len(audio_data) < 1000:
                notify("Whisprly", "Recording too short, ignored.")
                state.set_status(AppState.IDLE)
                update_tray_icon(tray_ref["icon"], state)
                return

            threading.Thread(
                target=process_audio,
                args=(audio_data, server_url, state, tray_ref["icon"]),
                daemon=True,
            ).start()

    def quit_app():
        print("\nWhisprly closed. See you!")
        if tray_ref["icon"]:
            tray_ref["icon"].stop()

    # Hotkeys
    hotkeys_cfg = config.get("hotkeys", {})
    hotkey_mgr = HotkeyManager()
    hotkey_mgr.register(
        hotkeys_cfg.get("toggle_recording", "<ctrl>+<shift>+space"),
        toggle_recording,
    )
    hotkey_mgr.register(
        hotkeys_cfg.get("quit", "<ctrl>+<shift>+q"),
        quit_app,
    )
    hotkey_mgr.start()

    # Tray icon
    icon = pystray.Icon(
        name="Whisprly",
        icon=create_icon_image(),
        title="Whisprly — Voice Dictation",
        menu=create_tray_menu(state, tones),
    )
    tray_ref["icon"] = icon

    hotkey_toggle = hotkeys_cfg.get("toggle_recording", "Ctrl+Shift+Space")
    print(f"\nReady! Press {hotkey_toggle} to dictate.")
    print(f"Active tone: {state.current_tone}")
    print(f"Server: {server_url}")
    print("Use the tray icon to change tone or quit.\n")

    icon.run()

    # Cleanup
    hotkey_mgr.stop()
    if recorder.is_recording:
        recorder.stop()


if __name__ == "__main__":
    main()
