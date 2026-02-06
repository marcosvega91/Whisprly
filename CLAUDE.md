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
python client.py

# Legacy mode (standalone, no Docker):
python main.py
```

There are no tests, no build step, no linter configured.

## Architecture

**Client-Server split**: Client (macOS) → HTTP → Server (Docker) → APIs (Whisper + Claude)

| Module | Responsibility |
|---|---|
| `server.py` | FastAPI server — REST API for transcription and text cleanup, runs in Docker |
| `client.py` | macOS client — audio recording, system tray, hotkeys, sends audio to server, auto-pastes result |
| `main.py` | Legacy standalone mode — full pipeline without Docker (original monolithic app) |
| `recorder.py` | `AudioRecorder` class — captures microphone via `sounddevice.InputStream`, outputs WAV bytes in memory |
| `transcriber.py` | `Transcriber` class — sends audio to OpenAI Whisper API, returns raw Italian text |
| `cleaner.py` | `TextCleaner` class — sends text + tone instructions to Claude API, returns corrected text |
| `notifier.py` | `notify()` function — cross-platform desktop notifications via plyer |

### Server API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/tones` | GET | Available tones and default |
| `/transcribe` | POST | Audio → raw text (Whisper) |
| `/clean` | POST | Raw text → clean text (Claude) |
| `/process` | POST | Full pipeline: audio → clean text |

### Docker Setup

- `Dockerfile` — Python 3.12-slim, server-only dependencies
- `docker-compose.yml` — Service on port 8899, reads `.env` for API keys
- `server-requirements.txt` — Minimal deps for server (no audio/desktop libs)

## Key Design Decisions

- **Client-server architecture**: Server in Docker for portability; client on host for hardware access (mic, clipboard, hotkeys).
- **Auto-paste**: Client copies to clipboard then simulates Cmd+V via AppleScript to paste into the focused input field.
- **Threading, not async**: Client uses daemon threads with locks for thread safety.
- **Hotkey debouncing**: 500ms debounce window in `HotkeyManager` to prevent double triggers.
- **Stateless processing**: No database or persistent storage. Audio is processed in-memory and discarded.
- **Dynamic tray icon**: Generated with Pillow — green (idle), red (recording), orange (processing).

## Configuration

- **`config.yaml`**: Server URL, audio settings, hotkeys, Whisper/Claude model selection, tone presets, custom tones, and extra instructions.
- **`.env`**: API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) — both required, used by the server.

## Language

The app is configured for **Italian** (Whisper language, tone prompts, cleanup instructions). The README is also in Italian.
