from unittest.mock import patch, MagicMock

from core.transcriber import Transcriber
from core.cleaner import TextCleaner


class TestPipeline:
    @patch("core.transcriber.OpenAI")
    @patch("core.cleaner.anthropic.Anthropic")
    def test_full_pipeline(self, mock_anthropic, mock_openai):
        """Test the complete audio -> text pipeline with mocked APIs."""
        # Setup transcriber mock
        mock_t_response = MagicMock()
        mock_t_response.text = "  testo grezzo dettato  "
        mock_openai.return_value.audio.transcriptions.create.return_value = mock_t_response

        # Setup cleaner mock
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Testo pulito e corretto."
        mock_c_response = MagicMock()
        mock_c_response.content = [mock_block]
        mock_anthropic.return_value.messages.create.return_value = mock_c_response

        # Run pipeline
        transcriber = Transcriber(api_key="test")
        cleaner = TextCleaner(api_key="test")

        raw = transcriber.transcribe(b"fake-audio")
        assert raw == "testo grezzo dettato"

        clean = cleaner.clean(raw, tone_instruction="professionale")
        assert clean == "Testo pulito e corretto."

    @patch("core.transcriber.OpenAI")
    @patch("core.cleaner.anthropic.Anthropic")
    def test_tone_reaches_claude(self, mock_anthropic, mock_openai):
        """Verify tone instruction reaches the Claude API call."""
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "result"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_anthropic.return_value.messages.create.return_value = mock_response

        cleaner = TextCleaner(api_key="test")
        cleaner.clean("text", tone_instruction="Be very formal")

        call_kwargs = mock_anthropic.return_value.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "Be very formal" in user_msg
        assert "<tono>" in user_msg

    @patch("core.transcriber.OpenAI")
    def test_empty_audio_short_circuits(self, mock_openai):
        """Verify empty audio returns empty without API call."""
        transcriber = Transcriber(api_key="test")
        result = transcriber.transcribe(b"")
        assert result == ""
        mock_openai.return_value.audio.transcriptions.create.assert_not_called()

    @patch("core.cleaner.anthropic.Anthropic")
    def test_empty_text_short_circuits(self, mock_anthropic):
        """Verify empty text returns empty without API call."""
        cleaner = TextCleaner(api_key="test")
        result = cleaner.clean("")
        assert result == ""
        mock_anthropic.return_value.messages.create.assert_not_called()
