<p align="center">
  <img src="assets/icon.png" alt="Whisprly" width="128">
</p>

# Whisprly

Voice dictation for Italian with AI-powered transcription and text cleanup.

Whisprly records your speech, transcribes it with **OpenAI Whisper**, cleans it up with **Anthropic Claude** (punctuation, grammar, tone), and auto-pastes the result into whatever input field you're focused on.

## Features

- **Floating widget** — animated icon with recording/processing states
- **System-wide hotkey** — press to record, press again to stop
- **OpenAI Whisper** transcription optimized for Italian
- **Claude AI cleanup** — punctuation, grammar correction, tone adjustment
- **Auto-paste** into the focused input field (macOS)
- **Dashboard** — history of past transcriptions, tone selector, hotkey settings
- **Transcription history** — last 100 entries saved locally with copy/delete
- **Multiple voice tones** — professional, informal, technical, creative, direct
- **Custom tones** — define your own in `config.yaml`
- **Client-server architecture** — server in Docker, client on macOS

## Architecture

```
Client (macOS)  ──HTTP──>  Server (Docker)  ──API──>  Whisper + Claude
 - Electron widget          - FastAPI REST API         - Transcription
 - Audio recording           - Transcription            - Text cleanup
 - Hotkeys                   - Text cleanup
 - Dashboard + History
 - Auto-paste
```

### Project Structure

```
client-electron/  Electron client — floating widget + dashboard (recommended)
core/             Shared modules (recorder, transcriber, cleaner, notifier)
server/           FastAPI server (runs in Docker)
client/           Python client (legacy, pystray-based)
tests/            Test suite (pytest)
config.yaml       App configuration (shared by server and client)
```

### Components

| Module | Responsibility |
|---|---|
| `client-electron/main.js` | Electron main process — window, hotkeys, IPC, auto-paste, dashboard |
| `client-electron/preload.js` | Context bridge between main and renderer processes |
| `client-electron/renderer/` | Floating widget UI, dashboard (history, tones, hotkey) |
| `client-electron/db.js` | SQLite persistence for transcription history |
| `core/recorder.py` | Audio capture from microphone via `sounddevice`, outputs WAV bytes |
| `core/transcriber.py` | Sends audio to OpenAI Whisper API, returns raw Italian text |
| `core/cleaner.py` | Sends text to Claude API for correction, punctuation, and tone |
| `core/notifier.py` | macOS desktop notifications via `osascript` |
| `server/app.py` | FastAPI REST server — transcription and cleanup endpoints |
| `client/app.py` | Python client (alternative to Electron) |
| `client/legacy.py` | Standalone mode — full pipeline without Docker (no auto-paste) |

## Prerequisites

- **Docker** and **Docker Compose**
- **Node.js 18+** (for the Electron client)
- **macOS** (client uses osascript for auto-paste)
- **OpenAI API key** (for Whisper transcription)
- **Anthropic API key** (for Claude text cleanup)

## Quick Start

```bash
# 1. Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY

# 2. Start the server (Docker)
docker compose up -d

# 3. Run the Electron client (recommended)
cd client-electron && npm install && npm start
```

### Alternative: Python Client

```bash
python -m venv venv && source venv/activate
pip install -r requirements.txt && brew install portaudio
python client/app.py
```

## Usage

1. **Press the hotkey** (default: `Cmd+Shift+Space`) to start recording
2. **Press again** to stop recording
3. Audio is sent to the Docker server
4. The server transcribes with Whisper and cleans up with Claude
5. The result is **auto-pasted** into the focused input field

### Floating Widget

The widget is a small icon in the bottom-right corner that changes based on state:
- **Breathing animation** — idle, ready to record
- **Pulsing red glow** — recording in progress
- **Orbiting dots** — processing (transcription + cleanup)
- **Bounce** — success, text pasted

**Click** the widget to open the dashboard. **Right-click** for a quick menu.

### Dashboard

Click the widget to open the dashboard with three sections:

- **History** — list of past transcriptions (last 100), each with copy and delete buttons
- **Voice Tone** — select the active tone for text cleanup
- **Hotkey** — configure the recording shortcut

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd+Shift+Space` | Toggle recording |
| `Ctrl+Shift+Q` | Quit |

Shortcuts are configurable from the dashboard or in `config.yaml`.

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
| `requirements.txt` | Python client dependencies (audio, desktop, HTTP) |
| `server-requirements.txt` | Server dependencies (FastAPI, APIs) |
| `dev-requirements.txt` | Test dependencies (pytest, httpx, FastAPI) |

## License

[MIT](LICENSE)
