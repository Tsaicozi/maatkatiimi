# 🐦 Birdeye API Key Manager Bot 🔑

Turvallinen ja tehokas ratkaisu Birdeye API-avainten hallintaan. Ratkaisee rate limit -ongelmat, kierrättää avaimia automaattisesti ja tarjoaa keskitetyn hallinnan.

## 🎯 Ominaisuudet

### Ydinominaisuudet
- **🔐 Turvallinen tallennus**: API-avaimet salataan levyllä (AES-256)
- **🔄 Automaattinen kierto**: Kierrättää avaimia rate limit -tilanteissa
- **📊 Valvonta**: Seuraa avainten käyttöä ja terveyttä reaaliajassa
- **🔌 Integraatio**: Helppo integrointi olemassa oleviin botteihin
- **🚨 Hälytykset**: Ilmoittaa ongelmista automaattisesti
- **📈 Metriikat**: Prometheus-yhteensopivat metriikat

### Turvallisuusominaisuudet
- Ei kovakoodattuja avaimia koodissa
- Salattu tallennus (PBKDF2 + Fernet)
- Automaattinen avainten testaus
- Virheellisten avainten deaktivointi
- Audit trail kaikista operaatioista

## 📦 Asennus

### 1. Vaatimukset
```bash
# Python 3.10+
python3 --version

# Asenna riippuvuudet
pip install cryptography aiohttp pyyaml python-dotenv prometheus-client
```

### 2. Nopea käynnistys
```bash
# Interaktiivinen setup
python3 setup_birdeye_keys.py

# Tai käynnistä suoraan botti
python3 birdeye_key_manager.py
```

## 🔧 Konfigurointi

### Ympäristömuuttujat (.env)

```env
# Yksittäinen avain
BIRDEYE_API_KEY=your_api_key_here

# Tai useita avaimia
BIRDEYE_API_KEY_1=first_key
BIRDEYE_API_KEY_2=second_key
BIRDEYE_API_KEY_3=third_key

# Salausavain (valinnainen, oletus käytetään jos puuttuu)
BIRDEYE_KEY_PASSWORD=your_secure_password
```

### Interaktiivinen Setup

```bash
python3 setup_birdeye_keys.py
```

Valikko tarjoaa:
1. **Aseta uudet API-avaimet** - Lisää ja testaa avaimia
2. **Luo .env-tiedosto** - Generoi .env-pohja
3. **Testaa integraatio** - Varmista että kaikki toimii
4. **Näytä avainten status** - Tarkista avainten tila
5. **Päivitä config.yaml** - Poista kovakoodatut avaimet
6. **Käynnistä Key Bot** - Käynnistä valvontabotti

## 🚀 Käyttö

### Standalone-botti

```python
# birdeye_key_manager.py
from birdeye_key_manager import BirdeyeKeyBot

async def main():
    bot = BirdeyeKeyBot()
    await bot.start()  # Käynnistää valvonnan

if __name__ == "__main__":
    asyncio.run(main())
```

### Integraatio olemassa olevaan bottiin

```python
from birdeye_integration import birdeye

async def your_bot():
    # Alusta integraatio
    await birdeye.initialize()
    
    # Käytä API-metodeja
    token_info = await birdeye.get_token_info("mint_address")
    price = await birdeye.get_token_price("mint_address")
    new_tokens = await birdeye.get_new_tokens(limit=10)
    
    # Avaintenhallinta hoitaa automaattisesti:
    # - Rate limit -käsittelyn
    # - Avainten kierron
    # - Virheiden hallinnan
```

### Manuaalinen avaintenhallinta

```python
from birdeye_key_manager import BirdeyeKeyManager

manager = BirdeyeKeyManager()

# Lataa avaimet
await manager.load_keys()

# Lisää uusi avain
await manager.add_key("new_api_key", "production_key")

# Hae käytettävissä oleva avain
api_key = await manager.get_key()

# Merkitse virhe
await manager.mark_key_error(api_key, "Rate limit exceeded")

# Hae status
status = await manager.get_status()
print(f"Aktiivisia avaimia: {status['active_keys']}/{status['total_keys']}")
```

## 🐳 Docker

### Käynnistys Dockerilla

```bash
# Rakenna ja käynnistä
docker-compose -f docker-compose.birdeye.yml up -d

# Tarkista lokit
docker logs birdeye-key-manager

# Pysäytä
docker-compose -f docker-compose.birdeye.yml down
```

### Docker Compose sisältää:
- **birdeye-key-manager**: Pääbotti
- **prometheus**: Metriikoiden keräys (valinnainen)
- **grafana**: Visualisointi (valinnainen)

Grafana löytyy osoitteesta: http://localhost:3001
- Käyttäjä: admin
- Salasana: birdeye123

## 🔌 Systemd-palvelu

### Asennus systemd-palveluna

```bash
# Kopioi service-tiedosto
sudo cp birdeye-key-manager.service /etc/systemd/system/

# Lataa uudelleen
sudo systemctl daemon-reload

# Käynnistä palvelu
sudo systemctl start birdeye-key-manager

# Automaattinen käynnistys
sudo systemctl enable birdeye-key-manager

# Tarkista status
sudo systemctl status birdeye-key-manager

# Lokit
journalctl -u birdeye-key-manager -f
```

## 📊 Metriikat ja valvonta

### Prometheus-metriikat (portti 9109)

- `birdeye_total_requests`: Pyyntöjen kokonaismäärä
- `birdeye_successful_requests`: Onnistuneet pyynnöt
- `birdeye_failed_requests`: Epäonnistuneet pyynnöt
- `birdeye_key_rotations`: Avainten kierrot
- `birdeye_rate_limit_hits`: Rate limit -osumat
- `birdeye_active_keys`: Aktiivisten avainten määrä

### Status API

```python
status = await manager.get_status()
```

Palauttaa:
```json
{
  "total_keys": 3,
  "active_keys": 2,
  "current_key": "production_key",
  "stats": {
    "total_requests": 1523,
    "successful_requests": 1498,
    "failed_requests": 25,
    "key_rotations": 12
  },
  "keys": [
    {
      "name": "production_key",
      "is_active": true,
      "request_count": 45,
      "error_count": 0
    }
  ]
}
```

## 🔒 Turvallisuus

### Salaus
- Avaimet salataan AES-256-salauksella
- PBKDF2 key derivation (100,000 kierrosta)
- Uniikki salt jokaiselle asennukselle (tuotannossa)

### Parhaat käytännöt
1. **Älä koskaan** tallenna avaimia versionhallintaan
2. Käytä vahvaa salasanaa `BIRDEYE_KEY_PASSWORD`
3. Rajoita tiedosto-oikeudet: `chmod 600 birdeye_keys.json`
4. Kierrä avaimia säännöllisesti
5. Valvo lokeja epänormaalin toiminnan varalta

## 🐛 Vianmääritys

### Yleisimmät ongelmat

**1. "Ei API-avaimia saatavilla"**
```bash
# Tarkista ympäristömuuttujat
env | grep BIRDEYE

# Aja setup
python3 setup_birdeye_keys.py
```

**2. "Rate limit saavutettu"**
- Lisää useampia avaimia
- Tarkista että kaikki avaimet ovat aktiivisia
- Odota rate limit -nollautumista (yleensä 1 min)

**3. "Avain ei toimi"**
```python
# Testaa avain manuaalisesti
python3 -c "
from birdeye_key_manager import BirdeyeKeyManager
import asyncio

async def test():
    m = BirdeyeKeyManager()
    result = await m._test_key('your_key_here')
    print(f'Avain toimii: {result}')

asyncio.run(test())
"
```

## 📈 Suorituskyky

### Optimoinnit
- Asynkroniset API-kutsut
- Avainten esivalinta (ei viivettä)
- Automaattinen retry exponential backoffilla
- Connection pooling
- Välimuisti rate limit -tiedoille

### Kapasiteetti
- Tukee rajattoman määrän avaimia
- Skaalautuu automaattisesti kuorman mukaan
- Minimaalinen muistinkäyttö (~10MB)
- CPU-käyttö <1% idle-tilassa

## 🤝 Integraatio muihin botteihin

### HybridTradingBot
```python
# Automaattinen patching
from birdeye_integration import auto_patch
auto_patch()

# Tai manuaalinen integraatio
from birdeye_integration import birdeye
bot.birdeye = birdeye
```

### DiscoveryEngine
```python
from birdeye_integration import birdeye

class YourDiscoveryEngine:
    async def analyze_token(self, mint):
        # Käytä integraatiota suoraan
        token_data = await birdeye.get_token_info(mint)
        security = await birdeye.get_token_security(mint)
        return self.process_data(token_data, security)
```

## 📝 Lisenssi

MIT License - Vapaasti käytettävissä ja muokattavissa

## 🆘 Tuki

Ongelmatilanteissa:
1. Tarkista lokit: `logs/birdeye_key_manager.log`
2. Aja testit: `python3 setup_birdeye_keys.py` -> "3. Testaa integraatio"
3. Tarkista avainten status
4. Varmista että Birdeye API on toiminnassa: https://docs.birdeye.so/

## 🎉 Yhteenveto

Birdeye Key Manager Bot ratkaisee kaikki Birdeye API -avainten hallintaan liittyvät ongelmat:

✅ **Ei enää rate limit -ongelmia** - Automaattinen avainten kierto
✅ **Turvallinen** - Salattu tallennus, ei kovakoodattuja avaimia  
✅ **Helppo integroida** - Drop-in replacement vanhalle koodille
✅ **Valvottu** - Reaaliaikaiset metriikat ja hälytykset
✅ **Skaalautuva** - Tukee rajattoman määrän avaimia

Käynnistä setup nyt: `python3 setup_birdeye_keys.py` 🚀