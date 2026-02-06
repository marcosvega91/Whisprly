# 🎤 Whisprly — Il tuo Wispr Flow italiano

App desktop system-wide per dettatura vocale in italiano con correzione automatica,
punteggiatura e adattamento del tono di voce.

## Come funziona

1. **Premi `Ctrl+Shift+Space`** (o il tuo hotkey personalizzato) per iniziare a registrare
2. **Premi di nuovo** per fermare la registrazione
3. L'audio viene trascritto da **OpenAI Whisper**
4. Il testo viene pulito e corretto da **Claude AI** (punteggiatura, errori, tono)
5. Il risultato viene **copiato negli appunti** e puoi incollarlo ovunque

## Requisiti

- Python 3.10+
- API Key OpenAI (per Whisper)
- API Key Anthropic (per Claude)
- PortAudio (per la registrazione audio)

### Installazione PortAudio

**macOS:**
```bash
brew install portaudio
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev
```

**Windows:**
PyAudio include già i binari necessari.

## Setup

```bash
cd whisprly
python -m venv venv
source venv/bin/activate  # Linux/macOS
# oppure: venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Copia e configura il file .env
cp .env.example .env
# Modifica .env con le tue API key
```

## Configurazione

Modifica `config.yaml` per personalizzare:

- **Hotkey** di attivazione
- **Tono di voce** (professionale, informale, tecnico, creativo...)
- **Istruzioni custom** per il cleanup del testo
- **Lingua** preferita
- **Modello** Claude da usare

## Uso

```bash
python main.py
```

L'icona apparirà nella system tray. Da lì puoi:
- Vedere lo stato (idle / registrazione / elaborazione)
- Cambiare il tono di voce al volo
- Uscire dall'app

## Shortcut da tastiera

| Shortcut | Azione |
|---|---|
| `Ctrl+Shift+Space` | Avvia/ferma registrazione |
| `Ctrl+Shift+Q` | Esci dall'app |
