from core.transcriber import Transcriber
from core.cleaner import TextCleaner

# Lazy imports for modules with heavy/platform-specific dependencies
# (numpy, sounddevice, subprocess) — not available in Docker server
def __getattr__(name):
    if name == "AudioRecorder":
        from core.recorder import AudioRecorder
        return AudioRecorder
    if name == "notify":
        from core.notifier import notify
        return notify
    raise AttributeError(f"module 'core' has no attribute {name!r}")

__all__ = ["AudioRecorder", "Transcriber", "TextCleaner", "notify"]
