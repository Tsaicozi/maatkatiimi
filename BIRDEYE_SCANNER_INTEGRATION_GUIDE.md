# 🔌 Birdeye Integration Guide for Token Scanner

## 📋 Pikaohje

### 1️⃣ **Varmista että Birdeye-avain toimii:**
```bash
python3 test_birdeye_key.py
```

### 2️⃣ **Päivitä Token Scanner käyttämään Birdeye-integraatiota:**
```bash
python3 update_scanner_birdeye.py
```

### 3️⃣ **Käynnistä Scanner:**
```bash
python3 real_solana_token_scanner.py
```

---

## 🛠️ Manuaalinen integrointi

### Vaihe 1: Lisää import
```python
# Lisää tiedoston alkuun
from birdeye_integration import birdeye
```

### Vaihe 2: Alusta integraatio
```python
class YourTokenScanner:
    async def __init__(self):
        # Alusta Birdeye integraatio
        await birdeye.initialize()
        self.birdeye = birdeye
```

### Vaihe 3: Käytä API-metodeja
```python
async def scan_birdeye_tokens(self):
    """Skannaa uusia tokeneita Birdeyestä"""
    
    # Hae uudet tokenit
    new_tokens = await self.birdeye.get_new_tokens(limit=50)
    
    if new_tokens:
        for token in new_tokens:
            # Hae lisätiedot
            token_info = await self.birdeye.get_token_info(token['address'])
            security = await self.birdeye.get_token_security(token['address'])
            
            # Käsittele token
            self.process_token(token_info, security)
```

---

## 📊 Käytettävissä olevat Birdeye-metodit

### `get_token_info(mint_address)`
Hakee tokenin perustiedot
```python
info = await birdeye.get_token_info("mint_address_here")
# Palauttaa: symbol, name, decimals, supply, etc.
```

### `get_token_price(mint_address)`
Hakee tokenin hinnan
```python
price = await birdeye.get_token_price("mint_address_here")
# Palauttaa: float (USD price)
```

### `get_token_security(mint_address)`
Hakee turvallisuustiedot
```python
security = await birdeye.get_token_security("mint_address_here")
# Palauttaa: freeze authority, mint authority, top holders, etc.
```

### `get_token_holders(mint_address)`
Hakee omistajatiedot
```python
holders = await birdeye.get_token_holders("mint_address_here")
# Palauttaa: top holders list with balances
```

### `get_new_tokens(limit=50)`
Hakee uusimmat tokenit
```python
new_tokens = await birdeye.get_new_tokens(limit=20)
# Palauttaa: lista uusimmista tokeneista
```

### `get_trending_tokens(limit=20)`
Hakee trending tokenit
```python
trending = await birdeye.get_trending_tokens()
# Palauttaa: lista suosituimmista tokeneista
```

---

## 🔄 Automaattinen päivitys

Aja tämä scripti päivittääksesi kaikki scannerit:

```python
#!/usr/bin/env python3
# update_scanner_birdeye.py

import asyncio
from pathlib import Path

async def update_scanner():
    """Päivitä scanner käyttämään Birdeye-integraatiota"""
    
    scanner_file = Path("real_solana_token_scanner.py")
    
    # Lue nykyinen koodi
    code = scanner_file.read_text()
    
    # Lisää import jos puuttuu
    if "from birdeye_integration import birdeye" not in code:
        lines = code.split('\n')
        # Etsi sopiva paikka importille
        for i, line in enumerate(lines):
            if line.startswith("import") or line.startswith("from"):
                continue
            else:
                # Lisää import tähän
                lines.insert(i, "from birdeye_integration import birdeye")
                break
        code = '\n'.join(lines)
    
    # Päivitä _scan_birdeye metodi
    # ... (koodi tähän)
    
    print("✅ Scanner päivitetty!")

if __name__ == "__main__":
    asyncio.run(update_scanner())
```

---

## ⚡ Optimoinnit

### 1. Välimuisti
```python
class TokenCache:
    def __init__(self, ttl=300):  # 5 min cache
        self.cache = {}
        self.ttl = ttl
    
    async def get_or_fetch(self, mint, fetcher):
        if mint in self.cache:
            data, timestamp = self.cache[mint]
            if time.time() - timestamp < self.ttl:
                return data
        
        data = await fetcher(mint)
        self.cache[mint] = (data, time.time())
        return data
```

### 2. Batch-pyynnöt
```python
async def fetch_multiple_tokens(self, mints):
    """Hae usean tokenin tiedot rinnakkain"""
    tasks = [
        self.birdeye.get_token_info(mint) 
        for mint in mints
    ]
    return await asyncio.gather(*tasks)
```

### 3. Rate limit -hallinta
```python
# Birdeye Key Manager hoitaa tämän automaattisesti!
# Ei tarvitse huolehtia rate limiteistä
```

---

## 🐛 Vianmääritys

### "No module named 'birdeye_integration'"
```bash
# Varmista että tiedosto on olemassa
ls birdeye_integration.py

# Jos puuttuu, lataa se
wget https://raw.githubusercontent.com/.../birdeye_integration.py
```

### "API key not found"
```bash
# Tarkista .env
grep BIRDEYE .env

# Lisää jos puuttuu
echo "BIRDEYE_API_KEY=d47f313bf3e249c9a4c476bba365a772" >> .env
```

### "Rate limit exceeded"
```bash
# Key Manager hoitaa automaattisesti
# Jos ongelma jatkuu, lisää useampia avaimia:
python3 setup_birdeye_keys.py
```

---

## 📈 Esimerkki: Täydellinen Scanner

```python
import asyncio
from birdeye_integration import birdeye
from datetime import datetime

class EnhancedSolanaScanner:
    def __init__(self):
        self.birdeye = None
        self.new_tokens = []
        
    async def initialize(self):
        """Alusta scanner"""
        await birdeye.initialize()
        self.birdeye = birdeye
        print("✅ Scanner valmis")
    
    async def scan(self):
        """Skannaa uusia tokeneita"""
        # 1. Hae uudet tokenit
        new_tokens = await self.birdeye.get_new_tokens(limit=50)
        
        # 2. Filtteröi ja analysoi
        for token in new_tokens:
            mint = token.get('address')
            
            # Hae turvallisuustiedot
            security = await self.birdeye.get_token_security(mint)
            
            # Tarkista turvallisuus
            if self.is_safe(security):
                # Hae hinta
                price = await self.birdeye.get_token_price(mint)
                
                # Lisää listaan
                self.new_tokens.append({
                    'mint': mint,
                    'symbol': token.get('symbol'),
                    'name': token.get('name'),
                    'price': price,
                    'security': security,
                    'found_at': datetime.now()
                })
        
        return self.new_tokens
    
    def is_safe(self, security):
        """Tarkista onko token turvallinen"""
        if not security:
            return False
        
        data = security.get('data', {})
        
        # Tarkista freeze authority
        if data.get('freezeAuthority'):
            return False
        
        # Tarkista mint authority
        if data.get('mintAuthority'):
            return False
        
        # Tarkista top 10 holders
        top10_share = data.get('top10HoldersPercent', 100)
        if top10_share > 50:  # Yli 50% top 10:llä
            return False
        
        return True

# Käyttö
async def main():
    scanner = EnhancedSolanaScanner()
    await scanner.initialize()
    
    while True:
        tokens = await scanner.scan()
        print(f"Löytyi {len(tokens)} uutta turvallista tokenia")
        
        for token in tokens[:5]:  # Näytä top 5
            print(f"  {token['symbol']}: ${token['price']:.6f}")
        
        await asyncio.sleep(60)  # Skannaa minuutin välein

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚀 Quick Start

1. **Kopioi esimerkki:**
```bash
cp BIRDEYE_SCANNER_INTEGRATION_GUIDE.md enhanced_scanner.py
```

2. **Muokkaa tarpeen mukaan**

3. **Käynnistä:**
```bash
python3 enhanced_scanner.py
```

---

## 📞 Tuki

Jos ongelmia:
1. Tarkista lokit: `tail -f *.log`
2. Testaa avain: `python3 test_birdeye_key.py`
3. Tarkista integraatio: `python3 test_birdeye_integration.py`