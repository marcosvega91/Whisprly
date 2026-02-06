"""
Whisprly - Modulo Registrazione Audio
Gestisce la cattura audio dal microfono usando sounddevice.
"""

import io
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    """Registra audio dal microfono e lo esporta come buffer WAV."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, dtype: str = "int16"):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Avvia la registrazione audio."""
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
                blocksize=1024,
            )
            self._stream.start()

    def stop(self) -> bytes:
        """
        Ferma la registrazione e restituisce l'audio come bytes WAV.
        
        Returns:
            bytes: Audio in formato WAV pronto per Whisper API
        """
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

        if not self._frames:
            return b""

        # Combina tutti i frame audio
        audio_data = np.concatenate(self._frames, axis=0)

        # Converti in WAV in memoria
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, self.sample_rate, format="WAV", subtype="PCM_16")
        buffer.seek(0)
        return buffer.read()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Callback chiamato da sounddevice per ogni blocco audio."""
        if status:
            print(f"[AudioRecorder] Warning: {status}")
        if self._recording:
            self._frames.append(indata.copy())

    def get_duration(self) -> float:
        """Restituisce la durata corrente della registrazione in secondi."""
        if not self._frames:
            return 0.0
        total_samples = sum(f.shape[0] for f in self._frames)
        return total_samples / self.sample_rate
