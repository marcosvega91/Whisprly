"""
Whisprly - Transcription Module (OpenAI Whisper)
Sends audio to the Whisper API and returns raw transcription.
"""

import io
from openai import OpenAI


class Transcriber:
    """Audio transcriber using the OpenAI Whisper API."""

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
        Transcribe audio bytes to text using Whisper.

        Args:
            audio_bytes: Audio in WAV format

        Returns:
            str: Raw transcribed text
        """
        if not audio_bytes:
            return ""

        # Whisper API accepts file-like objects
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"

        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=audio_file,
            language=self.language,
            temperature=self.temperature,
            # Optional prompt to help Whisper with Italian context
            prompt=(
                "Trascrizione di dettatura in italiano. "
                "Il parlante potrebbe usare termini tecnici inglesi "
                "come deploy, commit, sprint, bug, feature, merge."
            ),
        )

        return response.text.strip()
