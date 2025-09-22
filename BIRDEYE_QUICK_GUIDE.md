# 🚀 Birdeye API Key - Pikaohje

## Jos sinulla on jo BIRDEYE_API_KEY .env-tiedostossa:

### 1. Testaa että avain toimii:
```bash
python3 test_birdeye_key.py
```

### 2. Käynnistä Key Manager:
```bash
python3 birdeye_key_manager.py
```

### 3. Tai käytä Quick Start -menua:
```bash
./quick_start_birdeye.sh
```

## Jos .env-tiedostoa ei ole:

### 1. Luo .env-tiedosto:
```bash
python3 create_env.py
```
Scripti kysyy Birdeye API-avaimen ja luo .env-tiedoston.

### 2. Tai lisää manuaalisesti:
Luo `.env`-tiedosto ja lisää:
```
BIRDEYE_API_KEY=your_api_key_here
```

## Integrointi botteihin:

### Automaattinen:
```bash
python3 birdeye_integration.py patch
```

### Tai manuaalinen:
```python
# Lisää botin alkuun:
from birdeye_integration import birdeye

# Käytä metodeja:
token_info = await birdeye.get_token_info("mint_address")
```

## Ongelmatilanteet:

### "API-avain ei toimi":
1. Tarkista että avain on oikein kirjoitettu
2. Tarkista että avain on aktiivinen Birdeyessä
3. Testaa: `python3 test_birdeye_key.py`

### "Rate limit":
- Key Manager hoitaa tämän automaattisesti
- Jos ongelma jatkuu, lisää useampia avaimia

### "Ei löydy .env-tiedostoa":
```bash
python3 create_env.py
```

## Status ja valvonta:

### Näytä avainten tila:
```bash
python3 birdeye_integration.py status
```

### Käynnistä valvontabotti:
```bash
python3 birdeye_key_manager.py
```

## 🎯 Hyödyt:

✅ **Ei kovakoodattuja avaimia** - Turvallinen  
✅ **Automaattinen rate limit -hallinta** - Ei keskeytyksiä  
✅ **Avainten kierto** - Maksimoi läpimenon  
✅ **Integroitu valvonta** - Näet mitä tapahtuu  

---

**Vinkki**: Jos sinulla on jo toimiva BIRDEYE_API_KEY .env-tiedostossa, Key Manager lataa sen automaattisesti käynnistyessään!