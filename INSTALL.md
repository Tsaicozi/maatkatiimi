# Asennusohje - Enhanced Ideation Crew v2.0

## Vaihtoehto 1: Virtuaaliympäristö (Suositeltu)

```bash
# 1. Aktivoi virtuaaliympäristö
source venv/bin/activate

# 2. Asenna tarvittavat kirjastot
pip install -r requirements_minimal.txt

# 3. Testaa asennus
python -c "import enhanced_ideation_crew_v2; print('✅ Asennus onnistui!')"
```

## Vaihtoehto 2: Koko requirements (kaikki ominaisuudet)

```bash
# 1. Aktivoi virtuaaliympäristö
source venv/bin/activate

# 2. Asenna kaikki kirjastot
pip install -r requirements_enhanced.txt

# 3. Testaa asennus
python -c "import enhanced_ideation_crew_v2; print('✅ Asennus onnistui!')"
```

## Vaihtoehto 3: Manuaalinen asennus

```bash
# Aktivoi virtuaaliympäristö
source venv/bin/activate

# Asenna tärkeimmät kirjastot
pip install crewai crewai-tools python-dotenv pandas numpy scikit-learn yfinance requests joblib

# Vapaaehtoiset kirjastot
pip install textblob  # Sentimentti-analyysi
# pip install tensorflow  # Deep Learning (vapaaehtoinen)
```

## API-avaimet

Luo `.env`-tiedosto projektin juureen:

```env
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

## Testaus

```bash
# Testaa että kaikki toimii
python enhanced_ideation_crew_v2.py
```

## Virheenkäsittely

Jos saat virheitä:

1. **"No module named 'crewai'"** → Asenna: `pip install crewai crewai-tools`
2. **"No module named 'textblob'"** → Asenna: `pip install textblob`
3. **TensorFlow-virheet** → TensorFlow on vapaaehtoinen, koodi toimii ilman sitä
4. **API-virheet** → Tarkista että `.env`-tiedosto on olemassa ja sisältää oikeat avaimet
