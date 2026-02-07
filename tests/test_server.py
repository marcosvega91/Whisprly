import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client(sample_config):
    """Create a TestClient with mocked dependencies."""
    with patch("server.app.load_config", return_value=sample_config), \
         patch("server.app.load_dotenv"), \
         patch.dict("os.environ", {
             "OPENAI_API_KEY": "test-openai-key",
             "ANTHROPIC_API_KEY": "test-anthropic-key",
         }), \
         patch("server.app.Transcriber") as mock_t_cls, \
         patch("server.app.TextCleaner") as mock_c_cls:

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "Testo trascritto"
        mock_t_cls.return_value = mock_transcriber

        mock_cleaner = MagicMock()
        mock_cleaner.clean.return_value = "Testo pulito"
        mock_c_cls.return_value = mock_cleaner

        from server.app import app
        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    def test_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestTonesEndpoint:
    def test_returns_tones(self, client):
        r = client.get("/tones")
        assert r.status_code == 200
        data = r.json()
        assert "tones" in data
        assert "default" in data
        assert "professionale" in data["tones"]
        assert data["default"] == "professionale"


class TestTranscribeEndpoint:
    def test_valid_audio(self, client, sample_audio_bytes):
        r = client.post("/transcribe", files={"audio": ("test.wav", sample_audio_bytes)})
        assert r.status_code == 200
        assert r.json()["raw_text"] == "Testo trascritto"

    def test_too_short_audio(self, client):
        r = client.post("/transcribe", files={"audio": ("test.wav", b"short")})
        assert r.status_code == 400
        assert "Audio too short" in r.json()["detail"]


class TestCleanEndpoint:
    def test_valid_text(self, client):
        r = client.post("/clean", json={"raw_text": "testo da pulire", "tone": "professionale"})
        assert r.status_code == 200
        assert r.json()["clean_text"] == "Testo pulito"

    def test_empty_text(self, client):
        r = client.post("/clean", json={"raw_text": "", "tone": "professionale"})
        assert r.status_code == 400
        assert "Empty text" in r.json()["detail"]

    def test_whitespace_text(self, client):
        r = client.post("/clean", json={"raw_text": "   ", "tone": "professionale"})
        assert r.status_code == 400

    def test_with_context(self, client):
        r = client.post("/clean", json={
            "raw_text": "rispondi che va bene",
            "tone": "professionale",
            "context": "Ci vediamo domani alle 10?",
        })
        assert r.status_code == 200
        assert r.json()["clean_text"] == "Testo pulito"


class TestProcessEndpoint:
    def test_full_pipeline(self, client, sample_audio_bytes):
        r = client.post(
            "/process",
            files={"audio": ("test.wav", sample_audio_bytes)},
            data={"tone": "professionale"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["raw_text"] == "Testo trascritto"
        assert data["clean_text"] == "Testo pulito"

    def test_with_context(self, client, sample_audio_bytes):
        r = client.post(
            "/process",
            files={"audio": ("test.wav", sample_audio_bytes)},
            data={"tone": "professionale", "context": "Some email thread"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["raw_text"] == "Testo trascritto"
        assert data["clean_text"] == "Testo pulito"

    def test_too_short_audio(self, client):
        r = client.post(
            "/process",
            files={"audio": ("test.wav", b"short")},
            data={"tone": "professionale"},
        )
        assert r.status_code == 400
