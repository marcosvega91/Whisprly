from unittest.mock import patch, MagicMock

from core.cleaner import TextCleaner


class TestSystemPrompt:
    def test_is_italian(self):
        assert "italiano" in TextCleaner.SYSTEM_PROMPT
        assert "punteggiatura" in TextCleaner.SYSTEM_PROMPT

    def test_contains_key_rules(self):
        assert "PRESERVA" in TextCleaner.SYSTEM_PROMPT
        assert "sinonimi" in TextCleaner.SYSTEM_PROMPT


class TestCleanerInit:
    @patch("core.cleaner.anthropic.Anthropic")
    def test_defaults(self, mock_cls):
        tc = TextCleaner(api_key="test-key")
        assert tc.model == "claude-sonnet-4-20250514"
        assert tc.max_tokens == 4096
        mock_cls.assert_called_once_with(api_key="test-key")

    @patch("core.cleaner.anthropic.Anthropic")
    def test_custom_params(self, mock_cls):
        tc = TextCleaner(api_key="k", model="haiku", max_tokens=1024)
        assert tc.model == "haiku"
        assert tc.max_tokens == 1024


class TestClean:
    @patch("core.cleaner.anthropic.Anthropic")
    def test_empty_text_returns_empty(self, mock_cls):
        tc = TextCleaner(api_key="test-key")
        assert tc.clean("") == ""
        assert tc.clean("   ") == ""
        mock_cls.return_value.messages.create.assert_not_called()

    @patch("core.cleaner.anthropic.Anthropic")
    def test_clean_calls_api(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        result = tc.clean("testo grezzo", tone_instruction="professionale")

        assert result == "Testo pulito e corretto."
        mock_cls.return_value.messages.create.assert_called_once()

    @patch("core.cleaner.anthropic.Anthropic")
    def test_includes_system_prompt(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        tc.clean("testo")

        call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        assert call_kwargs["system"] == TextCleaner.SYSTEM_PROMPT

    @patch("core.cleaner.anthropic.Anthropic")
    def test_includes_tone_in_message(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        tc.clean("testo", tone_instruction="my tone")

        call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "<tono>" in user_msg
        assert "my tone" in user_msg

    @patch("core.cleaner.anthropic.Anthropic")
    def test_includes_extra_instructions(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        tc.clean("testo", extra_instructions="extra info")

        call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "<istruzioni_extra>" in user_msg
        assert "extra info" in user_msg

    @patch("core.cleaner.anthropic.Anthropic")
    def test_includes_raw_text_in_message(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        tc.clean("il mio testo grezzo")

        call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "<trascrizione_grezza>" in user_msg
        assert "il mio testo grezzo" in user_msg

    @patch("core.cleaner.anthropic.Anthropic")
    def test_omits_optional_tags_when_empty(self, mock_cls, mock_anthropic_response):
        mock_cls.return_value.messages.create.return_value = mock_anthropic_response

        tc = TextCleaner(api_key="test-key")
        tc.clean("testo")

        call_kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        user_msg = call_kwargs["messages"][0]["content"]
        assert "<tono>" not in user_msg
        assert "<istruzioni_extra>" not in user_msg
        assert "<trascrizione_grezza>" in user_msg
