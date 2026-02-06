FROM python:3.12-slim

WORKDIR /app

# Installa solo le dipendenze server (no audio, no desktop)
COPY server-requirements.txt .
RUN pip install --no-cache-dir -r server-requirements.txt

# Copia i moduli necessari
COPY server.py .
COPY transcriber.py .
COPY cleaner.py .
COPY config.yaml .

# Porta del server
EXPOSE 8899

# Avvia il server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8899"]
