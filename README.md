# 🎤 Whisprly — Il tuo Wispr Flow italiano

App per dettatura vocale in italiano con correzione automatica,
punteggiatura e adattamento del tono di voce.

**Architettura client-server**: il server gira in Docker (trascrizione + cleanup), il client gira su macOS (registrazione audio, hotkey, auto-paste).

## Come funziona

1. **Premi `Ctrl+Shift+Space`** per iniziare a registrare
2. **Premi di nuovo** per fermare la registrazione
3. L'audio viene inviato al server Docker
4. Il server trascrive con **OpenAI Whisper** e corregge con **Claude AI**
5. Il risultato viene **incollato automaticamente** nel campo di input attivo

## Requisiti

- Docker e Docker Compose
- Python 3.10+ (solo per il client)
- API Key OpenAI (per Whisper)
- API Key Anthropic (per Claude)
- PortAudio (solo macOS: `brew install portaudio`)

## Setup

```bash
# 1. Configura le API keys
cp .env.example .env
# Modifica .env con le tue API key

# 2. Avvia il server Docker
docker compose up -d

# 3. Installa il client (solo la prima volta)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Avvia il client
python client.py
```

## Uso

Il client mostra un'icona nella system tray. Da lì puoi:
- Vedere lo stato (idle / registrazione / elaborazione)
- Cambiare il tono di voce al volo
- Uscire dall'app

Il testo viene automaticamente incollato nel campo di input che ha il focus.

## Shortcut da tastiera

| Shortcut | Azione |
|---|---|
| `Ctrl+Shift+Space` | Avvia/ferma registrazione |
| `Ctrl+Shift+Q` | Esci dall'app |

## Configurazione

Modifica `config.yaml` per personalizzare:

- **Server URL** (`server.url`) — default: `http://localhost:8899`
- **Hotkey** di attivazione
- **Tono di voce** (professionale, informale, tecnico, creativo, diretto)
- **Toni custom** — aggiungi i tuoi nella sezione `custom_tones`
- **Istruzioni extra** per il cleanup del testo

## Server API

Il server espone queste API su `http://localhost:8899`:

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/health` | GET | Health check |
| `/tones` | GET | Toni disponibili |
| `/process` | POST | Pipeline completa: audio → testo pulito |
| `/transcribe` | POST | Solo trascrizione (Whisper) |
| `/clean` | POST | Solo cleanup (Claude) |

## Modalità standalone (senza Docker)

Se preferisci non usare Docker, puoi usare la modalità legacy:

```bash
# Assicurati che .env abbia le API keys
python main.py
```

In questa modalità tutto gira localmente, ma il testo viene solo copiato negli appunti (senza auto-paste).
