# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisprly is a Python voice dictation app for Italian. It uses a **client-server architecture**: the server runs in Docker (handles Whisper transcription + Claude cleanup), while a lightweight client runs on macOS (handles audio recording, hotkeys, and auto-paste into the focused input field).

## Running the App

```bash
# 1. Setup .env with API keys
cp .env.example .env  # Add OPENAI_API_KEY and ANTHROPIC_API_KEY

# 2. Start the server (Docker)
docker compose up -d

# 3. Run the Electron client (recommended)
cd client-electron && npm install && npm start

# Alternative: Python client (requires portaudio)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && brew install portaudio
python client/app.py

# Legacy mode (standalone, no Docker):
python client/legacy.py
```

## Running Tests

```bash
pip install -r dev-requirements.txt
pytest tests/ -v
```

## Architecture

**Client-Server split**: Client (macOS) -> HTTP -> Server (Docker) -> APIs (Whisper + Claude)

### Project Structure

```
core/               Shared modules used by server and Python clients
server/             FastAPI server (runs in Docker)
client-electron/    Electron client — floating widget with animations (recommended)
client/             Python client (legacy, pystray-based)
assets/             Shared assets (app icon)
tests/              Test suite (pytest)
```

| Module | Responsibility |
|---|---|
| `client-electron/main.js` | Electron main process — window, hotkeys, IPC, auto-paste, context menu |
| `client-electron/preload.js` | Context bridge between main and renderer processes |
| `client-electron/renderer/` | Floating widget UI — HTML/CSS animations, audio recording, state machine |
| `core/recorder.py` | `AudioRecorder` class — captures microphone via `sounddevice.InputStream`, outputs WAV bytes |
| `core/transcriber.py` | `Transcriber` class — sends audio to OpenAI Whisper API, returns raw Italian text |
| `core/cleaner.py` | `TextCleaner` class — sends text + tone instructions to Claude API, returns corrected text |
| `core/notifier.py` | `notify()` function — macOS desktop notifications via osascript |
| `server/app.py` | FastAPI server — REST API for transcription and text cleanup, runs in Docker |
| `client/app.py` | Python client (pystray) — alternative to Electron client |
| `client/legacy.py` | Legacy standalone mode — full pipeline without Docker (no auto-paste) |

### Server API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/tones` | GET | Available tones and default |
| `/transcribe` | POST | Audio -> raw text (Whisper) |
| `/clean` | POST | Raw text -> clean text (Claude) |
| `/process` | POST | Full pipeline: audio -> clean text |

### Docker Setup

- `Dockerfile` — Python 3.12-slim, copies `core/` and `server/` directories
- `docker-compose.yml` — Service on port 8899, reads `.env` for API keys
- `server-requirements.txt` — Minimal deps for server (no audio/desktop libs)

## Key Design Decisions

- **Client-server architecture**: Server in Docker for portability; client on host for hardware access (mic, clipboard, hotkeys).
- **Auto-paste**: Client copies to clipboard then simulates Cmd+V via AppleScript to paste into the focused input field.
- **Electron floating widget**: Frameless transparent window with CSS animations — breathing (idle), pulsing glow rings (recording), orbiting dots (processing).
- **Audio via Web Audio API**: Electron renderer captures mic at 16kHz mono, encodes to WAV, sends to server.
- **Hotkey debouncing**: 500ms debounce window to prevent double triggers.
- **Stateless processing**: No database or persistent storage. Audio is processed in-memory and discarded.
- **Italian AI prompts**: The Claude system prompt, tone presets, Whisper context, and extra_instructions are kept in Italian since they are functional prompts for processing Italian text.

## Configuration

- **`config.yaml`**: Server URL, audio settings, hotkeys, Whisper/Claude model selection, tone presets, custom tones, and extra instructions. Stays at project root (shared by server and client).
- **`.env`**: API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) — both required, used by the server.

## Language

The app processes **Italian** text (Whisper language, tone prompts, cleanup instructions). AI-facing prompts are in Italian; code, comments, and documentation are in English.
