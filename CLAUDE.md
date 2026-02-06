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
| `client-electron/main.js` | Electron main process — window, hotkeys, IPC, auto-paste, dashboard |
| `client-electron/preload.js` | Context bridge between main and renderer processes |
| `client-electron/renderer/` | Floating widget UI + dashboard (history, tones, hotkey settings) |
| `client-electron/db.js` | SQLite persistence layer for transcription history (better-sqlite3) |
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
- **Dashboard**: Click the widget to open a dashboard with history, tone selector, and hotkey settings. Replaces the old settings window.
- **Transcription history**: Last 100 entries stored in SQLite (`better-sqlite3`) in Electron's userData directory. Each entry saves clean_text, raw_text, tone, and timestamp.
- **Tone state in main process**: The active tone is managed as a single source of truth in the Electron main process, synced to widget and dashboard via IPC.
- **Italian AI prompts**: The Claude system prompt, tone presets, Whisper context, and extra_instructions are kept in Italian since they are functional prompts for processing Italian text.

## Configuration

- **`config.yaml`**: Server URL, audio settings, hotkeys, Whisper/Claude model selection, tone presets, custom tones, and extra instructions. Stays at project root (shared by server and client).
- **`.env`**: API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) — both required, used by the server.

## Language

The app processes **Italian** text (Whisper language, tone prompts, cleanup instructions). AI-facing prompts are in Italian; code, comments, and documentation are in English.
