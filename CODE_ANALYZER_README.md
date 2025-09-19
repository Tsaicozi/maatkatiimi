# 🤖 OpenAI GPT-5 Koodianalyysi Agentti

Tämä agentti analysoi hybrid trading botin koodin OpenAI GPT-5 tekoälyllä.

## 🚀 Käynnistys

### 1. Asenna riippuvuudet
```bash
pip install -r requirements_analyzer.txt
```

### 2. Aseta OpenAI API avain
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

Tai luo `.env` tiedosto:
```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 3. Käynnistä analyysi
```bash
python code_analyzer_agent.py
```

## 📊 Analyysi tyypit

### Kattava analyysi (oletus)
- Koodin laatu
- Turvallisuus
- Suorituskyky
- Arkkitehtuuri
- Kehitysehdotukset

### Turvallisuusanalyysi
```python
analyzer.analyze_code_file("hybrid_trading_bot.py", "security")
```

### Suorituskykyanalyysi
```python
analyzer.analyze_code_file("hybrid_trading_bot.py", "performance")
```

### Arkkitehtuurianalyysi
```python
analyzer.analyze_code_file("hybrid_trading_bot.py", "architecture")
```

## 📈 Tulokset

Analyysi luo:
- `code_analysis_report_YYYYMMDD_HHMMSS.json` - Yksityiskohtainen raportti
- Konsoli yhteenveto
- Turvallisuusriskit
- Optimointimahdollisuudet
- Parannusehdotukset

## 🔧 Käyttöesimerkki

```python
from code_analyzer_agent import CodeAnalyzerAgent

# Alusta agentti
analyzer = CodeAnalyzerAgent(model="gpt-5")

# Analysoi yksittäinen tiedosto
result = analyzer.analyze_code_file("hybrid_trading_bot.py")

# Analysoi koko projekti
project_analysis = analyzer.analyze_entire_project()

# Tallenna raportti
analyzer.save_analysis_report("my_analysis.json")

# Tulosta yhteenveto
analyzer.print_summary()
```

## ⚠️ Huomioita

- Vaatii OpenAI API avaimen
- Vaatii pääsyn GPT-5:een
- Internet yhteys tarvitaan
- Analyysi voi kestää useita minuutteja

## 🎯 Analyysi kattaa

✅ **Turvallisuus**
- API avaimet kova koodattuina
- Input validointi
- Virheenkäsittely
- Sensitiivisten tietojen käsittely

✅ **Suorituskyky**
- Tehokkuus
- Muistin käyttö
- I/O operaatiot
- Async/await käyttö

✅ **Arkkitehtuuri**
- Koodin rakenne
- Design patterns
- Modularity
- Maintainability

✅ **Best Practices**
- Python konventiot
- Code quality
- Documentation
- Testing
