"""
Whisprly - Modulo Trascrizione (OpenAI Whisper)
Invia l'audio a Whisper API e restituisce la trascrizione grezza.
"""

import io
from openai import OpenAI


class Transcriber:
    """Trascrittore audio tramite OpenAI Whisper API."""

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        language: str = "it",
        temperature: float = 0.0,
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.language = language
        self.temperature = temperature

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Trascrivi audio bytes in testo usando Whisper.
        
        Args:
            audio_bytes: Audio in formato WAV
            
        Returns:
            str: Testo trascritto grezzo
        """
        if not audio_bytes:
            return ""

        # Whisper API accetta file-like objects
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"

        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=audio_file,
            language=self.language,
            temperature=self.temperature,
            # Prompt opzionale per aiutare Whisper con contesto italiano
            prompt=(
                "Trascrizione di dettatura in italiano. "
                "Il parlante potrebbe usare termini tecnici inglesi "
                "come deploy, commit, sprint, bug, feature, merge."
            ),
        )

        return response.text.strip()
