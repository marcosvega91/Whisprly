"""
Whisprly - Desktop Notification Module
Native macOS notifications via osascript (no external dependencies).
"""

import subprocess
import threading


def notify(title: str, message: str, timeout: int = 5) -> None:
    """Display a macOS desktop notification via osascript."""
    def _send():
        try:
            # Escape quotes for AppleScript
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
            print(f"[Notification] [{title}] {message}")

    threading.Thread(target=_send, daemon=True).start()
