import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from core.recorder import AudioRecorder


class TestAudioRecorderInit:
    def test_defaults(self):
        rec = AudioRecorder()
        assert rec.sample_rate == 16000
        assert rec.channels == 1
        assert rec.dtype == "int16"
        assert not rec.is_recording

    def test_custom_params(self):
        rec = AudioRecorder(sample_rate=44100, channels=2, dtype="float32")
        assert rec.sample_rate == 44100
        assert rec.channels == 2
        assert rec.dtype == "float32"


class TestAudioRecorderRecording:
    @patch("core.recorder.sd.InputStream")
    def test_start_begins_recording(self, mock_stream_cls):
        rec = AudioRecorder()
        rec.start()
        assert rec.is_recording
        mock_stream_cls.assert_called_once()
        mock_stream_cls.return_value.start.assert_called_once()

    @patch("core.recorder.sd.InputStream")
    def test_start_idempotent(self, mock_stream_cls):
        rec = AudioRecorder()
        rec.start()
        rec.start()  # second call should be a no-op
        assert mock_stream_cls.call_count == 1

    @patch("core.recorder.sd.InputStream")
    def test_stop_returns_wav_bytes(self, mock_stream_cls):
        rec = AudioRecorder()
        rec.start()
        # Simulate audio callback with fake frames
        rec._frames = [np.zeros((1024,), dtype=np.int16)]
        wav_bytes = rec.stop()
        assert not rec.is_recording
        assert len(wav_bytes) > 44  # WAV header is 44 bytes
        assert wav_bytes[:4] == b"RIFF"

    def test_stop_when_not_recording(self):
        rec = AudioRecorder()
        result = rec.stop()
        assert result == b""

    @patch("core.recorder.sd.InputStream")
    def test_stop_with_no_frames(self, mock_stream_cls):
        rec = AudioRecorder()
        rec.start()
        result = rec.stop()
        assert result == b""


class TestAudioRecorderDuration:
    def test_no_frames(self):
        rec = AudioRecorder()
        assert rec.get_duration() == 0.0

    def test_with_frames(self):
        rec = AudioRecorder(sample_rate=16000)
        rec._frames = [np.zeros((16000,), dtype=np.int16)]
        assert rec.get_duration() == pytest.approx(1.0)

    def test_with_multiple_frames(self):
        rec = AudioRecorder(sample_rate=16000)
        rec._frames = [
            np.zeros((8000,), dtype=np.int16),
            np.zeros((8000,), dtype=np.int16),
        ]
        assert rec.get_duration() == pytest.approx(1.0)


class TestAudioCallback:
    def test_callback_appends_frames_when_recording(self):
        rec = AudioRecorder()
        rec._recording = True
        data = np.ones((1024,), dtype=np.int16)
        rec._audio_callback(data, 1024, None, None)
        assert len(rec._frames) == 1
        np.testing.assert_array_equal(rec._frames[0], data)

    def test_callback_ignores_when_not_recording(self):
        rec = AudioRecorder()
        rec._recording = False
        data = np.ones((1024,), dtype=np.int16)
        rec._audio_callback(data, 1024, None, None)
        assert len(rec._frames) == 0
