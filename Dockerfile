FROM python:3.11-slim

# Asenna curl healthcheck:ia varten
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Työhakemisto
WORKDIR /app

# Kopioi requirements ja asenna riippuvuudet
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopioi sovelluskoodi
COPY . .

# Käyttäjä (ei root)
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Expose metrics port
EXPOSE 9108

# Healthcheck
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=5 \
    CMD curl -f http://127.0.0.1:9108/metrics || exit 1

# Käynnistä bot
CMD ["python3", "automatic_hybrid_bot.py"]

