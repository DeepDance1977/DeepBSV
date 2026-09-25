FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten für den Build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Projektdateien kopieren
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Abhängigkeiten installieren
RUN pip install --no-cache-dir .

# Port für FastAPI freigeben
EXPOSE 8000

# Startbefehl für den Uvicorn Server
CMD ["uvicorn", "deepbsv.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
