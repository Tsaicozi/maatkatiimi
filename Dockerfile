FROM python:3.11-slim

# Asenna system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Työhakemisto
WORKDIR /app

# Kopioi requirements ja asenna
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopioi kaikki tiedostot
COPY . .

# Exposaa portit
EXPOSE 8001 9109

# Aja botti
CMD ["python3", "run_helius_scanner.py"]
