# 1. Basis-Image mit Python
FROM python:3.11-slim

# 2. Arbeitsverzeichnis im Container erstellen
WORKDIR /app

# 3. Umgebungsvariablen
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# 4. Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Anwendungs-Code in den Container kopieren
COPY ./app .

# 6. Den Port freigeben, auf dem die App laufen wird
EXPOSE 4325

# 7. Der Befehl, um die Anwendung zu starten
CMD ["gunicorn", "--bind", "0.0.0.0:4325", "main:app"]