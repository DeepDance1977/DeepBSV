# Offizielles Python 3.11 Image als Basis
FROM python:3.11-slim

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# System-Abhängigkeiten installieren (falls benötigt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten kopieren und installieren
COPY pyproject.toml ./
# Falls du eine requirements.txt hast, alternativ pip install -r requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install -e .

# Den restlichen Quellcode kopieren
COPY . .

# Port freigeben, auf dem der Stratum-Server lauscht
EXPOSE 3333

# Standardbefehl zum Starten der Anwendung (passe den Pfad an dein Hauptskript an, falls nötig)
CMD ["python", "-m", "deepbsv.main"]
