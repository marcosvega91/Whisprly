from unittest.mock import patch, MagicMock

from core.transcriber import Transcriber


class TestTranscriberInit:
    @patch("core.transcriber.OpenAI")
    def test_defaults(self, mock_openai_cls):
        t = Transcriber(api_key="test-key")
        assert t.model == "whisper-1"
        assert t.language == "it"
        assert t.temperature == 0.0
        mock_openai_cls.assert_called_once_with(api_key="test-key")

    @patch("core.transcriber.OpenAI")
    def test_custom_params(self, mock_openai_cls):
        t = Transcriber(api_key="k", model="whisper-2", language="en", temperature=0.5)
        assert t.model == "whisper-2"
        assert t.language == "en"
        assert t.temperature == 0.5


class TestTranscribe:
    @patch("core.transcriber.OpenAI")
    def test_empty_audio_returns_empty(self, mock_openai_cls):
        t = Transcriber(api_key="test-key")
        assert t.transcribe(b"") == ""
        mock_openai_cls.return_value.audio.transcriptions.create.assert_not_called()

    @patch("core.transcriber.OpenAI")
    def test_transcribe_calls_api(self, mock_openai_cls, mock_openai_response):
        mock_openai_cls.return_value.audio.transcriptions.create.return_value = mock_openai_response

        t = Transcriber(api_key="test-key")
        result = t.transcribe(b"fake-wav-data")

        assert result == "Ciao mondo"  # stripped
        mock_openai_cls.return_value.audio.transcriptions.create.assert_called_once()

    @patch("core.transcriber.OpenAI")
    def test_transcribe_passes_correct_params(self, mock_openai_cls, mock_openai_response):
        mock_openai_cls.return_value.audio.transcriptions.create.return_value = mock_openai_response

        t = Transcriber(api_key="test-key", model="whisper-1", language="it", temperature=0.0)
        t.transcribe(b"fake-wav-data")

        call_kwargs = mock_openai_cls.return_value.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs["model"] == "whisper-1"
        assert call_kwargs.kwargs["language"] == "it"
        assert call_kwargs.kwargs["temperature"] == 0.0

    @patch("core.transcriber.OpenAI")
    def test_italian_prompt_is_present(self, mock_openai_cls, mock_openai_response):
        mock_openai_cls.return_value.audio.transcriptions.create.return_value = mock_openai_response

        t = Transcriber(api_key="test-key")
        t.transcribe(b"fake-wav-data")

        call_kwargs = mock_openai_cls.return_value.audio.transcriptions.create.call_args
        prompt = call_kwargs.kwargs["prompt"]
        assert "italiano" in prompt
        assert "dettatura" in prompt
