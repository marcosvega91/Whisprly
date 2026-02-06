"""
Whisprly - Modulo Notifiche Desktop
Notifiche macOS native via osascript (nessuna dipendenza esterna).
"""

import subprocess
import threading


def notify(title: str, message: str, timeout: int = 5) -> None:
    """
    Mostra una notifica desktop macOS via osascript.
    """
    def _send():
        try:
            # Escape delle virgolette per AppleScript
            safe_title = title.replace('"', '\\"')
            safe_message = message.replace('"', '\\"')
            subprocess.run(
                [
                    "osascript", "-e",
                    f'display notification "{safe_message}" with title "{safe_title}"',
                ],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            print(f"🔔 [{title}] {message}")

    threading.Thread(target=_send, daemon=True).start()
