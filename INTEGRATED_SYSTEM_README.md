# 🤖 Integroitu KehitysSysteemi

Tämä systeemi yhdistää GPT-5 koodin analysoijan ja keittäjän yhdeksi tehokkaaksi kehitysympäristöksi.

## 🏗️ Systeemin Komponentit

### 1. **CodeAnalyzerAgent** (`code_analyzer_agent.py`)
- Analysoi koodin turvallisuutta, suorituskykyä ja arkkitehtuuria
- GPT-5 tekoäly analyysi
- Kattavat raportit JSON muodossa

### 2. **CodeChefAgent** (`code_chef_agent.py`)
- Keittää uutta korkealaatuista Python koodia
- Parantaa olemassa olevaa koodia
- Luo uusia featureita
- GPT-5 tekoäly kehitys

### 3. **IntegratedDevelopmentSystem** (`integrated_development_system.py`)
- Yhdistää analysoijan ja keittäjän
- Automaattinen analyysi + parannus workflow
- Projektin laajuinen analyysi ja parannus

## 🚀 Käyttö

### Perus Käynnistys

```bash
# Aseta OpenAI API avain
echo "OPENAI_API_KEY=your_api_key_here" >> .env

# Käynnistä analysoija
python3 code_analyzer_agent.py

# Käynnistä keittäjä
python3 code_chef_agent.py

# Käynnistä integroitu systeemi
python3 integrated_development_system.py
```

### Workflow Esimerkit

#### 1. Analysoi ja Paranna Yksi Tiedosto

```python
from integrated_development_system import IntegratedDevelopmentSystem
import asyncio

async def analyze_and_improve_file():
    system = IntegratedDevelopmentSystem()
    
    result = await system.analyze_and_improve(
        "telegram_bot_integration.py",
        improvement_focus="Turvallisuus ja suorituskyky"
    )
    
    print("Analyysi ja parannus valmis!")

asyncio.run(analyze_and_improve_file())
```

#### 2. Luo Uusi Feature

```python
async def create_new_feature():
    system = IntegratedDevelopmentSystem()
    
    result = await system.create_feature_with_analysis(
        "Luo Telegram bot integraatio joka tukee MarkdownV2 muotoilua",
        target_file="telegram_bot_v2.py"
    )
    
    print("Feature luotu ja analysoitu!")

asyncio.run(create_new_feature())
```

#### 3. Koko Projektin Analyysi ja Parannus

```python
async def improve_entire_project():
    system = IntegratedDevelopmentSystem()
    
    project_files = [
        'telegram_bot_integration.py',
        'hybrid_trading_bot.py',
        'real_solana_token_scanner.py'
    ]
    
    result = await system.full_project_analysis_and_improvement(project_files)
    
    print("Koko projekti analysoitu ja parannettu!")

asyncio.run(improve_entire_project())
```

## 📊 Analyysi Tyypit

### Comprehensive Analyysi (Oletus)
- Koodin laatu
- Turvallisuusriskit
- Suorituskykyongelmat
- Arkkitehtuuriongelmat
- Best practices
- Parannusehdotukset

### Security Analyysi
```python
analyzer = CodeAnalyzerAgent()
result = analyzer.analyze_code_file("file.py", "security")
```

### Performance Analyysi
```python
analyzer = CodeAnalyzerAgent()
result = analyzer.analyze_code_file("file.py", "performance")
```

## 🍳 Koodin Keittäminen

### Luo Uusi Feature
```python
chef = CodeChefAgent()
result = await chef.create_feature(
    "Luo risk management engine joka laskee position sizing",
    target_file="risk_engine.py"
)
```

### Paranna Olemassa Olevaa Koodia
```python
chef = CodeChefAgent()
result = await chef.improve_code(
    "telegram_bot_integration.py",
    "Lisää Markdown-escaping ja viestin pituusrajan tarkistus"
)
```

### Keitä Koodia Vaatimusten Mukaan
```python
chef = CodeChefAgent()
result = await chef.cook_code(
    "Luo async HTTP client joka tukee retry logic ja circuit breaker",
    target_file="http_client.py"
)
```

## 📈 Raportit

### Analyysi Raportit
- `code_analysis_report_YYYYMMDD_HHMMSS.json`
- Kattava analyysi kaikista tiedostoista
- Turvallisuus, suorituskyky, arkkitehtuuri

### Kehitys Raportit
- `code_development_history_YYYYMMDD_HHMMSS.json`
- Kaikki kehitetty koodi
- Parannusehdotukset ja toteutukset

### Sessio Raportit
- `development_sessions_YYYYMMDD_HHMMSS.json`
- Integroidut analyysi + kehitys sessiot
- Projektin laajuinen raportti

## 🔧 Konfiguraatio

### Environment Variables
```bash
# OpenAI API avain (pakollinen)
OPENAI_API_KEY=your_api_key_here

# Telegram bot (jos käytät)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Malli Konfiguraatio
```python
# Käytä GPT-4 (oletus)
system = IntegratedDevelopmentSystem(model="gpt-4")

# Käytä GPT-5 (jos saatavilla)
system = IntegratedDevelopmentSystem(model="gpt-5")
```

## 🎯 Käyttötapaukset

### 1. Legacy Koodin Parannus
- Analysoi vanha koodi
- Identifioi ongelmat
- Luo parannusehdotukset
- Implementoi parannukset

### 2. Uuden Koodin Kehitys
- Määrittele vaatimukset
- Keitä korkealaatuista koodia
- Analysoi luotu koodi
- Iteroi ja paranna

### 3. Koodin Refaktorointi
- Analysoi nykyinen arkkitehtuuri
- Identifioi parannusmahdollisuudet
- Refaktoroi koodi
- Validoi muutokset

### 4. Turvallisuus Audit
- Analysoi turvallisuusriskit
- Identifioi vulnerabilitetit
- Korjaa ongelmat
- Validoi korjaukset

## 📋 Best Practices

### Analyysi
- Analysoi aina ennen muutoksia
- Käytä comprehensive analyysiä
- Tallenna raportit
- Seuraa parannusehdotuksia

### Kehitys
- Määrittele vaatimukset selkeästi
- Käytä type hints
- Implementoi error handling
- Lisää dokumentaatio

### Integrointi
- Käytä async/await
- Tallenna kehityshistoria
- Iteroi ja paranna
- Testaa muutokset

## 🚨 Troubleshooting

### API Virheet
```bash
# Tarkista API avain
echo $OPENAI_API_KEY

# Tarkista .env tiedosto
cat .env | grep OPENAI_API_KEY
```

### Muistin Ongelmat
- Käytä pienempiä tiedostoja
- Jaa suuret projektit osiin
- Käytä streaming analyysiä

### Suorituskyky
- Käytä async/await
- Rajoita samanaikaisia pyyntöjä
- Käytä caching

## 📞 Tuki

Jos kohtaat ongelmia:
1. Tarkista API avaimet
2. Katso logitiedostot
3. Tarkista tiedostojen oikeudet
4. Käytä debug tilaa

---

**Integroitu KehitysSysteemi - GPT-5 Powered Development Environment** 🚀
