"""
Whisprly Server — API REST per trascrizione e cleanup testo.
Gira in Docker e gestisce le chiamate a Whisper e Claude.
"""

import os
import sys
import yaml
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from transcriber import Transcriber
from cleaner import TextCleaner


# ─── Configurazione ──────────────────────────────────────────────

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("❌ config.yaml non trovato!")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_tone_instruction(config: dict, tone_name: str) -> str:
    tone_cfg = config.get("tone", {})
    presets = tone_cfg.get("presets", {})
    if tone_name in presets:
        return presets[tone_name]
    custom = tone_cfg.get("custom_tones", {}) or {}
    if tone_name in custom:
        return custom[tone_name]
    return f"Riscrivi il testo con un tono {tone_name}."


def get_available_tones(config: dict) -> list[str]:
    tone_cfg = config.get("tone", {})
    tones = list(tone_cfg.get("presets", {}).keys())
    custom = tone_cfg.get("custom_tones", {}) or {}
    tones.extend(custom.keys())
    return tones


# ─── Stato globale ───────────────────────────────────────────────

config: dict = {}
transcriber: Transcriber
cleaner: TextCleaner


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global config, transcriber, cleaner

    load_dotenv(Path(__file__).parent / ".env")
    config = load_config()

    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not openai_key or openai_key.startswith("sk-your"):
        print("❌ OPENAI_API_KEY non configurata!")
        sys.exit(1)
    if not anthropic_key or anthropic_key.startswith("sk-ant-your"):
        print("❌ ANTHROPIC_API_KEY non configurata!")
        sys.exit(1)

    whisper_cfg = config.get("whisper", {})
    transcriber = Transcriber(
        api_key=openai_key,
        model=whisper_cfg.get("model", "whisper-1"),
        language=whisper_cfg.get("language", "it"),
        temperature=whisper_cfg.get("temperature", 0.0),
    )

    claude_cfg = config.get("claude", {})
    cleaner = TextCleaner(
        api_key=anthropic_key,
        model=claude_cfg.get("model", "claude-sonnet-4-20250514"),
        max_tokens=claude_cfg.get("max_tokens", 4096),
    )

    print("✅ Whisprly Server avviato")
    yield
    print("👋 Whisprly Server chiuso")


app = FastAPI(
    title="Whisprly Server",
    description="API per trascrizione vocale e cleanup testo",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Modelli ─────────────────────────────────────────────────────

class CleanRequest(BaseModel):
    raw_text: str
    tone: str = "professionale"

class CleanResponse(BaseModel):
    clean_text: str

class TranscribeResponse(BaseModel):
    raw_text: str

class ProcessResponse(BaseModel):
    raw_text: str
    clean_text: str

class TonesResponse(BaseModel):
    tones: list[str]
    default: str


# ─── Endpoints ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/tones", response_model=TonesResponse)
async def get_tones():
    tones = get_available_tones(config)
    default = config.get("tone", {}).get("default", "professionale")
    return TonesResponse(tones=tones, default=default)


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Audio troppo breve")

    raw_text = transcriber.transcribe(audio_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Nessun testo rilevato")

    return TranscribeResponse(raw_text=raw_text)


@app.post("/clean", response_model=CleanResponse)
async def clean_text(request: CleanRequest):
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="Testo vuoto")

    tone_instruction = get_tone_instruction(config, request.tone)
    extra_instructions = config.get("extra_instructions", "")

    clean = cleaner.clean(
        raw_text=request.raw_text,
        tone_instruction=tone_instruction,
        extra_instructions=extra_instructions,
    )
    return CleanResponse(clean_text=clean)


@app.post("/process", response_model=ProcessResponse)
async def process_audio(
    audio: UploadFile = File(...),
    tone: str = Form("professionale"),
):
    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Audio troppo breve")

    # Step 1: Trascrizione
    raw_text = transcriber.transcribe(audio_bytes)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Nessun testo rilevato")

    print(f"📝 Trascrizione: {raw_text}")

    # Step 2: Cleanup
    tone_instruction = get_tone_instruction(config, tone)
    extra_instructions = config.get("extra_instructions", "")

    clean_text = cleaner.clean(
        raw_text=raw_text,
        tone_instruction=tone_instruction,
        extra_instructions=extra_instructions,
    )

    print(f"✨ Pulito: {clean_text}")

    return ProcessResponse(raw_text=raw_text, clean_text=clean_text)
