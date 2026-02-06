"""
Whisprly — Italian Voice Dictation
Desktop system-wide voice dictation app with AI cleanup.

Usage:
    python client/legacy.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading
import time
import yaml
import pyperclip
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from pynput import keyboard
import pystray

from core.recorder import AudioRecorder
from core.transcriber import Transcriber
from core.cleaner import TextCleaner
from core.notifier import notify


# ─── App State ──────────────────────────────────────────────────

class AppState:
    """Global application state."""
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
    """Load configuration from config.yaml."""
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if not config_path.exists():
        print("config.yaml not found! Copy config.yaml.example and configure it.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_tone_instruction(config: dict, tone_name: str) -> str:
    """Return the instruction for the specified tone."""
    tone_cfg = config.get("tone", {})

    # Search in presets
    presets = tone_cfg.get("presets", {})
    if tone_name in presets:
        return presets[tone_name]

    # Search in custom tones
    custom = tone_cfg.get("custom_tones", {}) or {}
    if tone_name in custom:
        return custom[tone_name]

    # Fallback: use the tone name as instruction
    return f"Riscrivi il testo con un tono {tone_name}."


def get_available_tones(config: dict) -> list[str]:
    """Return the list of all available tones."""
    tone_cfg = config.get("tone", {})
    tones = list(tone_cfg.get("presets", {}).keys())
    custom = tone_cfg.get("custom_tones", {}) or {}
    tones.extend(custom.keys())
    return tones


# ─── Tray Icon ──────────────────────────────────────────────────

ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
_base_icon: Image.Image | None = None


def _load_base_icon() -> Image.Image:
    global _base_icon
    if _base_icon is None:
        _base_icon = Image.open(ICON_PATH).convert("RGBA").resize((64, 64), Image.LANCZOS)
    return _base_icon.copy()


def create_icon_image(color: str = "#4CAF50") -> Image.Image:
    """Create a system tray icon with a status indicator dot."""
    img = _load_base_icon()
    draw = ImageDraw.Draw(img)
    # Status dot (bottom-right corner)
    dot_r = 10
    x, y = img.width - dot_r - 2, img.height - dot_r - 2
    draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                 fill=color, outline="white", width=2)
    return img


ICON_COLORS = {
    AppState.IDLE: "#4CAF50",       # Green
    AppState.RECORDING: "#F44336",   # Red
    AppState.PROCESSING: "#FF9800",  # Orange
}


# ─── Main Pipeline ──────────────────────────────────────────────

def process_audio(
    audio_bytes: bytes,
    transcriber: Transcriber,
    cleaner: TextCleaner,
    config: dict,
    state: AppState,
    tray_icon: pystray.Icon | None = None,
) -> None:
    """
    Full pipeline: audio -> transcription -> cleanup -> clipboard.
    Runs in a separate thread.
    """
    try:
        state.set_status(AppState.PROCESSING)
        update_tray_icon(tray_icon, state)
        notify("Whisprly", "Processing...")

        # Step 1: Transcription with Whisper
        raw_text = transcriber.transcribe(audio_bytes)

        if not raw_text.strip():
            notify("Whisprly", "No text detected in audio.")
            return

        print(f"\nRaw transcription:\n{raw_text}\n")

        # Step 2: Cleanup with Claude
        tone_instruction = get_tone_instruction(config, state.current_tone)
        extra_instructions = config.get("extra_instructions", "")

        clean_text = cleaner.clean(
            raw_text=raw_text,
            tone_instruction=tone_instruction,
            extra_instructions=extra_instructions,
        )

        print(f"Cleaned text:\n{clean_text}\n")

        # Step 3: Copy to clipboard
        pyperclip.copy(clean_text)

        # Show preview in notification (truncated)
        preview = clean_text[:100] + ("..." if len(clean_text) > 100 else "")
        notify("Whisprly", f"Copied to clipboard!\n{preview}")

    except Exception as e:
        print(f"Error during processing: {e}")
        notify("Whisprly", f"Error: {str(e)[:100]}")
    finally:
        state.set_status(AppState.IDLE)
        update_tray_icon(tray_icon, state)


# ─── Tray Icon Management ──────────────────────────────────────

def update_tray_icon(icon: pystray.Icon | None, state: AppState) -> None:
    """Update the icon color based on the current state."""
    if icon is None:
        return
    try:
        color = ICON_COLORS.get(state.status, ICON_COLORS[AppState.IDLE])
        icon.icon = create_icon_image(color)
    except Exception:
        pass


def create_tray_menu(state: AppState, config: dict) -> pystray.Menu:
    """Create the tray icon context menu."""

    def make_tone_handler(tone_name):
        def handler(icon, item):
            state.set_tone(tone_name)
            notify("Whisprly", f"Tone changed: {tone_name}")
            # Update the menu
            icon.menu = create_tray_menu(state, config)
        return handler

    def is_current_tone(tone_name):
        def check(item):
            return state.current_tone == tone_name
        return check

    # Tone submenu
    tone_items = []
    for tone in get_available_tones(config):
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


# ─── Hotkey Listener ────────────────────────────────────────────

def parse_hotkey(hotkey_str: str) -> set:
    """Convert a hotkey string into a set of pynput keys."""
    key_map = {
        "<ctrl>": keyboard.Key.ctrl_l,
        "<shift>": keyboard.Key.shift_l,
        "<alt>": keyboard.Key.alt_l,
        "<cmd>": keyboard.Key.cmd,
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
            # Try as Key enum
            try:
                keys.add(getattr(keyboard.Key, part))
            except AttributeError:
                print(f"Unrecognized key: {part}")
    return keys


class HotkeyManager:
    """Manages global hotkeys."""

    def __init__(self):
        self._pressed_keys: set = set()
        self._callbacks: dict[frozenset, callable] = {}
        self._listener: keyboard.Listener | None = None

    def register(self, hotkey_str: str, callback: callable) -> None:
        """Register a hotkey with its callback."""
        keys = parse_hotkey(hotkey_str)
        self._callbacks[frozenset(keys)] = callback
        print(f"Hotkey registered: {hotkey_str}")

    def start(self) -> None:
        """Start the global keyboard listener."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stop the listener."""
        if self._listener:
            self._listener.stop()

    def _normalize_key(self, key) -> keyboard.Key | keyboard.KeyCode:
        """Normalize keys (e.g. ctrl_r -> ctrl_l)."""
        if hasattr(key, 'name'):
            name = key.name
            if name.endswith('_r'):
                try:
                    return getattr(keyboard.Key, name.replace('_r', '_l'))
                except AttributeError:
                    pass
        return key

    def _on_press(self, key) -> None:
        normalized = self._normalize_key(key)
        self._pressed_keys.add(normalized)

        frozen = frozenset(self._pressed_keys)
        for combo, callback in self._callbacks.items():
            if combo.issubset(frozen):
                callback()

    def _on_release(self, key) -> None:
        normalized = self._normalize_key(key)
        self._pressed_keys.discard(normalized)
        # Discard the original version too
        self._pressed_keys.discard(key)


# ─── Main ───────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Whisprly — Italian Voice Dictation")
    print("=" * 50)

    # Load env and config
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    config = load_config()

    # Verify API keys
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not openai_key or openai_key.startswith("sk-your"):
        print("OPENAI_API_KEY not configured! Edit the .env file")
        sys.exit(1)
    if not anthropic_key or anthropic_key.startswith("sk-ant-your"):
        print("ANTHROPIC_API_KEY not configured! Edit the .env file")
        sys.exit(1)

    # Initialize components
    audio_cfg = config.get("audio", {})
    recorder = AudioRecorder(
        sample_rate=audio_cfg.get("sample_rate", 16000),
        channels=audio_cfg.get("channels", 1),
        dtype=audio_cfg.get("dtype", "int16"),
    )

    whisper_cfg = config.get("whisper", {})
    transcriber = Transcriber(
        api_key=openai_key,
        model=whisper_cfg.get("model", "whisper-1"),
        language=whisper_cfg.get("language", "it"),
        temperature=whisper_cfg.get("temperature", 0.0),
    )

    claude_cfg = config.get("claude", {})
    cleaner = TextCleaner(
        api_key=anthropic_key,
        model=claude_cfg.get("model", "claude-sonnet-4-20250514"),
        max_tokens=claude_cfg.get("max_tokens", 4096),
    )

    # App state
    state = AppState()
    state.current_tone = config.get("tone", {}).get("default", "professionale")
    state.available_tones = get_available_tones(config)

    # Tray icon reference (set after creation)
    tray_ref = {"icon": None}

    # Debounce to prevent double triggers
    last_toggle_time = {"t": 0.0}

    def toggle_recording():
        """Toggle recording on/off."""
        now = time.time()
        if now - last_toggle_time["t"] < 0.5:  # 500ms debounce
            return
        last_toggle_time["t"] = now

        if state.status == AppState.PROCESSING:
            return  # Don't interrupt processing

        if not recorder.is_recording:
            # Start recording
            recorder.start()
            state.set_status(AppState.RECORDING)
            update_tray_icon(tray_ref["icon"], state)
            notify("Whisprly", "Recording started... Press again to stop.")
            print("Recording started...")
        else:
            # Stop recording
            audio_data = recorder.stop()
            duration = recorder.get_duration()
            print(f"Recording stopped ({duration:.1f}s)")

            if len(audio_data) < 1000:  # Too short
                notify("Whisprly", "Recording too short, ignored.")
                state.set_status(AppState.IDLE)
                update_tray_icon(tray_ref["icon"], state)
                return

            # Process in background
            threading.Thread(
                target=process_audio,
                args=(audio_data, transcriber, cleaner, config, state, tray_ref["icon"]),
                daemon=True,
            ).start()

    def quit_app():
        """Quit the application."""
        print("\nWhisprly closed. See you!")
        if tray_ref["icon"]:
            tray_ref["icon"].stop()

    # Configure hotkeys
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

    # Create and start tray icon
    icon = pystray.Icon(
        name="Whisprly",
        icon=create_icon_image(),
        title="Whisprly — Voice Dictation",
        menu=create_tray_menu(state, config),
    )
    tray_ref["icon"] = icon

    hotkey_toggle = hotkeys_cfg.get("toggle_recording", "Ctrl+Shift+Space")
    print(f"\nReady! Press {hotkey_toggle} to dictate.")
    print(f"Active tone: {state.current_tone}")
    print("Use the tray icon to change tone or quit.\n")

    # pystray.run() blocks the main thread (required on macOS)
    icon.run()

    # Cleanup
    hotkey_mgr.stop()
    if recorder.is_recording:
        recorder.stop()


if __name__ == "__main__":
    main()
