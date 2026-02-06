<p align="center">
  <img src="assets/icon.png" alt="Whisprly" width="128">
</p>

# Whisprly

Voice dictation for Italian with AI-powered transcription and text cleanup.

Whisprly records your speech, transcribes it with **OpenAI Whisper**, cleans it up with **Anthropic Claude** (punctuation, grammar, tone), and auto-pastes the result into whatever input field you're focused on.

## Features

- **System-wide hotkey** — press to record, press again to stop
- **OpenAI Whisper** transcription optimized for Italian
- **Claude AI cleanup** — punctuation, grammar correction, tone adjustment
- **Auto-paste** into the focused input field (macOS)
- **System tray** icon with status indicator (green/red/orange) and tone selector
- **Multiple voice tones** — professional, informal, technical, creative, direct
- **Custom tones** — define your own in `config.yaml`
- **Client-server architecture** — server in Docker, client on macOS

## Architecture

```
Client (macOS)  ──HTTP──>  Server (Docker)  ──API──>  Whisper + Claude
 - Audio recording          - FastAPI REST API         - Transcription
 - Hotkeys                  - Transcription            - Text cleanup
 - System tray              - Text cleanup
 - Auto-paste
```

### Project Structure

```
core/           Shared modules (recorder, transcriber, cleaner, notifier)
server/         FastAPI server (runs in Docker)
client/         macOS client (audio, hotkeys, tray, auto-paste)
tests/          Test suite (pytest)
config.yaml     App configuration (shared by server and client)
```

### Components

| Module | Responsibility |
|---|---|
| `core/recorder.py` | Audio capture from microphone via `sounddevice`, outputs WAV bytes |
| `core/transcriber.py` | Sends audio to OpenAI Whisper API, returns raw Italian text |
| `core/cleaner.py` | Sends text to Claude API for correction, punctuation, and tone |
| `core/notifier.py` | macOS desktop notifications via `osascript` |
| `server/app.py` | FastAPI REST server — transcription and cleanup endpoints |
| `client/app.py` | macOS client — recording, hotkeys, tray, auto-paste via server |
| `client/legacy.py` | Standalone mode — full pipeline without Docker (no auto-paste) |

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.10+** (for the client)
- **macOS** (client uses osascript and sounddevice)
- **OpenAI API key** (for Whisper transcription)
- **Anthropic API key** (for Claude text cleanup)
- **PortAudio** — `brew install portaudio`

## Quick Start

```bash
# 1. Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY

# 2. Start the server (Docker)
docker compose up -d

# 3. Set up the client (first time only)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run the client
python client/app.py
```

## Usage

1. **Press the hotkey** (default: `Cmd Right`) to start recording
2. **Press again** to stop recording
3. Audio is sent to the Docker server
4. The server transcribes with Whisper and cleans up with Claude
5. The result is **auto-pasted** into the focused input field

### System Tray

The client shows a tray icon that changes color based on state:
- **Green** — idle, ready to record
- **Red** — recording in progress
- **Orange** — processing (transcription + cleanup)

From the tray menu you can:
- See current status
- Change the voice tone on the fly
- Quit the app

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd Right` (tap) | Toggle recording |
| `Ctrl+Shift+Q` | Quit |

Shortcuts are configurable in `config.yaml`.

## Configuration

Edit `config.yaml` to customize:

| Section | Options |
|---|---|
| `server.url` | Server address (default: `http://localhost:8899`) |
| `audio` | Sample rate, channels, audio format |
| `hotkeys` | Recording toggle and quit shortcuts |
| `whisper` | Model, language, temperature |
| `claude` | Model, max tokens |
| `tone.default` | Default voice tone |
| `tone.presets` | Built-in tone definitions |
| `tone.custom_tones` | Your custom tones |
| `extra_instructions` | Additional cleanup instructions for Claude |

### Custom Tones

Add your own tones in the `custom_tones` section of `config.yaml`:

```yaml
tone:
  custom_tones:
    social_media: >
      Riscrivi per un post social: breve, accattivante, con emoji dove serve.
      Massimo 280 caratteri.
```

## Server API

The server runs on `http://localhost:8899` and exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/tones` | GET | Available tones and default |
| `/transcribe` | POST | Audio file -> raw transcription (Whisper) |
| `/clean` | POST | Raw text -> cleaned text (Claude) |
| `/process` | POST | Full pipeline: audio -> cleaned text |

### Examples

```bash
# Health check
curl http://localhost:8899/health

# Full pipeline
curl -X POST http://localhost:8899/process \
  -F "audio=@recording.wav" \
  -F "tone=professionale"

# Transcription only
curl -X POST http://localhost:8899/transcribe \
  -F "audio=@recording.wav"

# Text cleanup only
curl -X POST http://localhost:8899/clean \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "ciao come stai io sto bene", "tone": "professionale"}'
```

## Legacy Mode (without Docker)

If you prefer not to use Docker, run standalone mode. This requires API keys configured locally and does not support auto-paste (text is copied to clipboard only):

```bash
# Make sure .env has your API keys
python client/legacy.py
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r dev-requirements.txt

# Run tests
pytest tests/ -v
```

### Project Dependencies

| File | Purpose |
|---|---|
| `requirements.txt` | Client dependencies (audio, desktop, HTTP) |
| `server-requirements.txt` | Server dependencies (FastAPI, APIs) |
| `dev-requirements.txt` | Test dependencies (pytest, httpx, FastAPI) |

## License

MIT
