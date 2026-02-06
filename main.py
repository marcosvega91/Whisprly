"""
Whisprly — Il tuo Wispr Flow italiano
App desktop system-wide per dettatura vocale con AI cleanup.

Uso:
    python main.py
"""

import os
import sys
import threading
import time
import yaml
import pyperclip
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from pynput import keyboard
import pystray

from recorder import AudioRecorder
from transcriber import Transcriber
from cleaner import TextCleaner
from notifier import notify


# ─── Stato dell'app ───────────────────────────────────────────────

class AppState:
    """Stato globale dell'applicazione."""
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


# ─── Configurazione ──────────────────────────────────────────────

def load_config() -> dict:
    """Carica la configurazione da config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("❌ config.yaml non trovato! Copia config.yaml.example e configuralo.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_tone_instruction(config: dict, tone_name: str) -> str:
    """Restituisce l'istruzione del tono specificato."""
    tone_cfg = config.get("tone", {})
    
    # Cerca nei preset
    presets = tone_cfg.get("presets", {})
    if tone_name in presets:
        return presets[tone_name]
    
    # Cerca nei toni custom
    custom = tone_cfg.get("custom_tones", {}) or {}
    if tone_name in custom:
        return custom[tone_name]
    
    # Fallback: usa il nome del tono come istruzione
    return f"Riscrivi il testo con un tono {tone_name}."


def get_available_tones(config: dict) -> list[str]:
    """Restituisce la lista di tutti i toni disponibili."""
    tone_cfg = config.get("tone", {})
    tones = list(tone_cfg.get("presets", {}).keys())
    custom = tone_cfg.get("custom_tones", {}) or {}
    tones.extend(custom.keys())
    return tones


# ─── Icona Tray ──────────────────────────────────────────────────

def create_icon_image(color: str = "#4CAF50") -> Image.Image:
    """Crea un'icona per la system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Cerchio di sfondo
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    
    # Simbolo microfono stilizzato (rettangolo + base)
    mic_color = "white"
    # Corpo microfono
    draw.rounded_rectangle([24, 14, 40, 38], radius=6, fill=mic_color)
    # Base
    draw.arc([18, 26, 46, 48], start=0, end=180, fill=mic_color, width=3)
    # Stelo
    draw.line([32, 48, 32, 54], fill=mic_color, width=3)
    draw.line([24, 54, 40, 54], fill=mic_color, width=3)
    
    return img


ICON_COLORS = {
    AppState.IDLE: "#4CAF50",       # Verde
    AppState.RECORDING: "#F44336",   # Rosso
    AppState.PROCESSING: "#FF9800",  # Arancione
}


# ─── Pipeline principale ─────────────────────────────────────────

def process_audio(
    audio_bytes: bytes,
    transcriber: Transcriber,
    cleaner: TextCleaner,
    config: dict,
    state: AppState,
    tray_icon: pystray.Icon | None = None,
) -> None:
    """
    Pipeline completa: audio → trascrizione → cleanup → clipboard.
    Eseguita in un thread separato.
    """
    try:
        state.set_status(AppState.PROCESSING)
        update_tray_icon(tray_icon, state)
        notify("Whisprly", "⏳ Elaborazione in corso...")

        # Step 1: Trascrizione con Whisper
        raw_text = transcriber.transcribe(audio_bytes)
        
        if not raw_text.strip():
            notify("Whisprly", "⚠️ Nessun testo rilevato nell'audio.")
            return

        print(f"\n📝 Trascrizione grezza:\n{raw_text}\n")

        # Step 2: Cleanup con Claude
        tone_instruction = get_tone_instruction(config, state.current_tone)
        extra_instructions = config.get("extra_instructions", "")

        clean_text = cleaner.clean(
            raw_text=raw_text,
            tone_instruction=tone_instruction,
            extra_instructions=extra_instructions,
        )

        print(f"✨ Testo pulito:\n{clean_text}\n")

        # Step 3: Copia negli appunti
        pyperclip.copy(clean_text)
        
        # Mostra preview nella notifica (troncata)
        preview = clean_text[:100] + ("..." if len(clean_text) > 100 else "")
        notify("Whisprly ✅", f"Copiato negli appunti!\n{preview}")

    except Exception as e:
        print(f"❌ Errore durante l'elaborazione: {e}")
        notify("Whisprly ❌", f"Errore: {str(e)[:100]}")
    finally:
        state.set_status(AppState.IDLE)
        update_tray_icon(tray_icon, state)


# ─── Gestione Tray Icon ─────────────────────────────────────────

def update_tray_icon(icon: pystray.Icon | None, state: AppState) -> None:
    """Aggiorna il colore dell'icona in base allo stato."""
    if icon is None:
        return
    try:
        color = ICON_COLORS.get(state.status, ICON_COLORS[AppState.IDLE])
        icon.icon = create_icon_image(color)
    except Exception:
        pass


def create_tray_menu(state: AppState, config: dict) -> pystray.Menu:
    """Crea il menu contestuale della tray icon."""
    
    def make_tone_handler(tone_name):
        def handler(icon, item):
            state.set_tone(tone_name)
            notify("Whisprly", f"🎨 Tono cambiato: {tone_name}")
            # Aggiorna il menu
            icon.menu = create_tray_menu(state, config)
        return handler

    def is_current_tone(tone_name):
        def check(item):
            return state.current_tone == tone_name
        return check

    # Sottomenu toni
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
            lambda text: f"Stato: {state.status.upper()}",
            None,
            enabled=False,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🎨 Tono di voce", pystray.Menu(*tone_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Esci", lambda icon, item: icon.stop()),
    )


# ─── Hotkey Listener ─────────────────────────────────────────────

def parse_hotkey(hotkey_str: str) -> set:
    """Converte stringa hotkey in set di tasti per pynput."""
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
            # Prova come Key enum
            try:
                keys.add(getattr(keyboard.Key, part))
            except AttributeError:
                print(f"⚠️ Tasto non riconosciuto: {part}")
    return keys


class HotkeyManager:
    """Gestisce gli hotkey globali."""

    def __init__(self):
        self._pressed_keys: set = set()
        self._callbacks: dict[frozenset, callable] = {}
        self._listener: keyboard.Listener | None = None

    def register(self, hotkey_str: str, callback: callable) -> None:
        """Registra un hotkey con la sua callback."""
        keys = parse_hotkey(hotkey_str)
        self._callbacks[frozenset(keys)] = callback
        print(f"⌨️  Hotkey registrato: {hotkey_str}")

    def start(self) -> None:
        """Avvia il listener globale della tastiera."""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Ferma il listener."""
        if self._listener:
            self._listener.stop()

    def _normalize_key(self, key) -> keyboard.Key | keyboard.KeyCode:
        """Normalizza i tasti (es. ctrl_r → ctrl_l)."""
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
        # Discard anche la versione originale
        self._pressed_keys.discard(key)


# ─── Main ────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("🎤 Whisprly — Il tuo Wispr Flow italiano")
    print("=" * 50)

    # Carica env e config
    load_dotenv(Path(__file__).parent / ".env")
    config = load_config()

    # Verifica API keys
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not openai_key or openai_key.startswith("sk-your"):
        print("❌ OPENAI_API_KEY non configurata! Modifica il file .env")
        sys.exit(1)
    if not anthropic_key or anthropic_key.startswith("sk-ant-your"):
        print("❌ ANTHROPIC_API_KEY non configurata! Modifica il file .env")
        sys.exit(1)

    # Inizializza componenti
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

    # Stato app
    state = AppState()
    state.current_tone = config.get("tone", {}).get("default", "professionale")
    state.available_tones = get_available_tones(config)

    # Variabile per l'icona tray (sarà impostata dopo)
    tray_ref = {"icon": None}

    # Debounce per evitare doppi trigger
    last_toggle_time = {"t": 0.0}

    def toggle_recording():
        """Toggle registrazione on/off."""
        now = time.time()
        if now - last_toggle_time["t"] < 0.5:  # Debounce 500ms
            return
        last_toggle_time["t"] = now

        if state.status == AppState.PROCESSING:
            return  # Non interrompere l'elaborazione

        if not recorder.is_recording:
            # Avvia registrazione
            recorder.start()
            state.set_status(AppState.RECORDING)
            update_tray_icon(tray_ref["icon"], state)
            notify("Whisprly 🔴", "Registrazione avviata... Premi di nuovo per fermare.")
            print("🔴 Registrazione avviata...")
        else:
            # Ferma registrazione
            audio_data = recorder.stop()
            duration = recorder.get_duration()
            print(f"⏹️  Registrazione fermata ({duration:.1f}s)")

            if len(audio_data) < 1000:  # Troppo corto
                notify("Whisprly", "⚠️ Registrazione troppo breve, ignorata.")
                state.set_status(AppState.IDLE)
                update_tray_icon(tray_ref["icon"], state)
                return

            # Processa in background
            threading.Thread(
                target=process_audio,
                args=(audio_data, transcriber, cleaner, config, state, tray_ref["icon"]),
                daemon=True,
            ).start()

    def quit_app():
        """Chiudi l'applicazione."""
        print("\n👋 Whisprly chiuso. A presto!")
        if tray_ref["icon"]:
            tray_ref["icon"].stop()

    # Configura hotkeys
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

    # Crea e avvia tray icon
    icon = pystray.Icon(
        name="Whisprly",
        icon=create_icon_image(),
        title="Whisprly — Dettatura Vocale",
        menu=create_tray_menu(state, config),
    )
    tray_ref["icon"] = icon

    hotkey_toggle = hotkeys_cfg.get("toggle_recording", "Ctrl+Shift+Space")
    print(f"\n✅ Pronto! Premi {hotkey_toggle} per dettare.")
    print(f"🎨 Tono attivo: {state.current_tone}")
    print("💡 Usa l'icona nella tray per cambiare tono o uscire.\n")

    # pystray.run() blocca il thread principale (necessario su macOS)
    icon.run()

    # Cleanup
    hotkey_mgr.stop()
    if recorder.is_recording:
        recorder.stop()


if __name__ == "__main__":
    main()
