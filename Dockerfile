FROM python:3.12-slim

WORKDIR /app

# Install server-only dependencies (no audio, no desktop)
COPY server-requirements.txt .
RUN pip install --no-cache-dir -r server-requirements.txt

# Copy shared core modules
COPY core/ core/

# Copy server module
COPY server/ server/

# Copy configuration
COPY config.yaml .

# Server port
EXPOSE 8899

# Start the server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8899"]
