import io
import struct
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def sample_config():
    """Load the actual config.yaml for testing."""
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_audio_bytes():
    """Generate minimal valid WAV bytes for testing."""
    sample_rate = 16000
    num_samples = 16000  # 1 second of silence
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))   # PCM format
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(b"\x00" * data_size)

    return buf.getvalue()


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI transcription response."""
    response = MagicMock()
    response.text = "  Ciao mondo  "
    return response


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic messages response."""
    block = MagicMock()
    block.type = "text"
    block.text = "Testo pulito e corretto."
    response = MagicMock()
    response.content = [block]
    return response
