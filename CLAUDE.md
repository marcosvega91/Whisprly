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

# 3. Run the client (macOS)
# First time:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install portaudio  # macOS prerequisite

# Run client
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
core/           Shared modules used by both server and client
server/         FastAPI server (runs in Docker)
client/         macOS client entry points
tests/          Test suite (pytest)
```

| Module | Responsibility |
|---|---|
| `core/recorder.py` | `AudioRecorder` class — captures microphone via `sounddevice.InputStream`, outputs WAV bytes |
| `core/transcriber.py` | `Transcriber` class — sends audio to OpenAI Whisper API, returns raw Italian text |
| `core/cleaner.py` | `TextCleaner` class — sends text + tone instructions to Claude API, returns corrected text |
| `core/notifier.py` | `notify()` function — macOS desktop notifications via osascript |
| `server/app.py` | FastAPI server — REST API for transcription and text cleanup, runs in Docker |
| `client/app.py` | macOS client — audio recording, system tray, hotkeys, sends audio to server, auto-pastes result |
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
- **Threading, not async**: Client uses daemon threads with locks for thread safety.
- **Hotkey debouncing**: 500ms debounce window in `HotkeyManager` to prevent double triggers.
- **Stateless processing**: No database or persistent storage. Audio is processed in-memory and discarded.
- **Dynamic tray icon**: Generated with Pillow — green (idle), red (recording), orange (processing).
- **Italian AI prompts**: The Claude system prompt, tone presets, Whisper context, and extra_instructions are kept in Italian since they are functional prompts for processing Italian text.

## Configuration

- **`config.yaml`**: Server URL, audio settings, hotkeys, Whisper/Claude model selection, tone presets, custom tones, and extra instructions. Stays at project root (shared by server and client).
- **`.env`**: API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) — both required, used by the server.

## Language

The app processes **Italian** text (Whisper language, tone prompts, cleanup instructions). AI-facing prompts are in Italian; code, comments, and documentation are in English.
