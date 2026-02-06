"""
Whisprly - Modulo Notifiche Desktop
Gestisce le notifiche di sistema cross-platform.
"""

import sys
import threading


def notify(title: str, message: str, timeout: int = 5) -> None:
    """
    Mostra una notifica desktop.
    
    Usa plyer come backend principale, con fallback per sistemi
    dove plyer non funziona.
    """
    def _send():
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Whisprly",
                timeout=timeout,
            )
        except Exception:
            # Fallback: stampa in console
            print(f"🔔 [{title}] {message}")

    # Esegui in thread separato per non bloccare
    threading.Thread(target=_send, daemon=True).start()
