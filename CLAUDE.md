# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Whisprly is a Python desktop application for Italian voice dictation. It runs as a system tray app and uses OpenAI Whisper for speech-to-text and Anthropic Claude for text cleanup/correction. The result is copied to the clipboard.

## Running the App

```bash
# Setup (first time)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add OPENAI_API_KEY and ANTHROPIC_API_KEY

# macOS prerequisite: brew install portaudio

# Run
python main.py
```

There are no tests, no build step, no linter configured.

## Architecture

The app follows a linear pipeline: **Record → Transcribe → Clean → Clipboard**.

| Module | Responsibility |
|---|---|
| `main.py` | App entry point, system tray (pystray), state machine (IDLE/RECORDING/PROCESSING), hotkey management (pynput), tone selection menu, orchestrates the full pipeline |
| `recorder.py` | `AudioRecorder` class — captures microphone via `sounddevice.InputStream`, outputs WAV bytes in memory |
| `transcriber.py` | `Transcriber` class — sends audio to OpenAI Whisper API, returns raw Italian text |
| `cleaner.py` | `TextCleaner` class — sends text + tone instructions to Claude API, returns corrected text |
| `notifier.py` | `notify()` function — cross-platform desktop notifications via plyer |

## Key Design Decisions

- **Threading, not async**: All background work (recording, API calls, notifications) uses daemon threads with locks for thread safety.
- **Hotkey debouncing**: 500ms debounce window in `HotkeyManager` to prevent double triggers.
- **Stateless processing**: No database or persistent storage. Audio is processed in-memory and discarded.
- **Dynamic tray icon**: Generated with Pillow — green (idle), red (recording), orange (processing).

## Configuration

- **`config.yaml`**: Audio settings, hotkeys, Whisper/Claude model selection, tone presets (professionale/informale/tecnico/creativo/diretto), custom tones, and extra instructions for text cleanup.
- **`.env`**: API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) — both required.

## Language

The app is configured for **Italian** (Whisper language, tone prompts, cleanup instructions). The README is also in Italian.
