# 🔍 HELIUS BOT ANALYYSI RAPORTTI

## 📋 YHTEENVETO

Analysoin olemassa olevan `HeliusLogsNewTokensSource` -botin toimintaa ja sen integraatiota DiscoveryEngine-järjestelmään. Tämä raportti kattaa botin koodin rakenteen, suodatusarvot, toiminnallisuuden ja mahdolliset ongelmat.

---

## 🏗️ KOODIN RAKENNE JA TOIMINTA

### 📁 Tiedosto: `sources/helius_logs_newtokens.py`
**Koko:** 146 riviä  
**Luokka:** `HeliusLogsNewTokensSource`  
**Tarkoitus:** Real-time Solana token creation monitoring Helius WebSocket API:n kautta

### 🔧 Konstruktori ja Alustus
```python
def __init__(self, ws_url: str, programs: list[str]):
    self.ws_url = ws_url                    # Helius WebSocket URL
    self.programs = programs                # Seurattavat ohjelmat
    self._stop = asyncio.Event()           # Pysäytyseventti
    self._seen = set()                     # Nähdyt mint-osoitteet (deduplikointi)
    self._ws = None                        # WebSocket-yhteys
```

**Analyysi:**
- ✅ Yksinkertainen ja selkeä rakenne
- ✅ Asynkroninen Event-pohjainen pysäytys
- ✅ Deduplikointi `_seen` set:llä
- ⚠️ `_seen` set kasvaa loputtomiin (ei TTL:ää)

---

## 🎯 CORE TOIMINNALLISUUS

### 1. **WebSocket Yhteys**
```python
async with websockets.connect(self.ws_url) as ws:
    self._ws = ws
    
    # Subscribe to program logs
    for program_id in self.programs:
        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [program_id]},
                {"commitment": "confirmed"}
            ]
        }
```

**Analyysi:**
- ✅ Käyttää `logsSubscribe` -metodia (oikea lähestymistapa)
- ✅ `"confirmed"` commitment level (hyvä balanssi)
- ✅ Automaattinen reconnect-logiikka
- ⚠️ Kiinteä `id: 1` kaikille tilauksille (voisi aiheuttaa ongelmia)

### 2. **Mint-osoitteen Poiminta**
```python
def _extract_mint_from_logs(self, logs: list[str]) -> str | None:
    for log in logs:
        if "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke" in log:
            parts = log.split()
            if len(parts) > 4:
                for i, part in enumerate(parts):
                    if part == "invoke" and i + 1 < len(parts):
                        if i + 2 < len(parts):
                            return parts[i + 2]
```

**Analyysi:**
- ⚠️ **KRIITTINEN ONGELMA**: Mint-osoitteen poiminta on epäluotettava
- ❌ Olettaa että mint-osoite on aina parts[i + 2] -kohdassa
- ❌ Ei käsittele erilaisia log-formaatteja
- ❌ Voi poimia väärän osoitteen (esim. authority tai muu account)

### 3. **Symbolin Poiminta**
```python
def _extract_symbol_from_logs(self, logs: list[str]) -> str | None:
    for log in logs:
        if "symbol" in log.lower():
            match = re.search(r'symbol["\']?\s*[:=]\s*["\']?([A-Za-z0-9]+)', log, re.IGNORECASE)
            if match:
                return match.group(1)
```

**Analyysi:**
- ✅ Käyttää regex-pohjaista poimintaa
- ⚠️ Yksinkertainen pattern, voi missata kompleksisempia formaatteja
- ⚠️ Ei käsittele erikoismerkkejä symboleissa

---

## 🔍 SUODATUSARVOT JA KRITEERIT

### 🏢 **Konfiguraatio** (`config.py`)

#### Helius-spesifiset asetukset:
```python
class SourcesCfg:
    helius_logs: bool = True    # Helius logs käytössä

class FreshPassCfg:
    sources: tuple[str, ...] = ("pumpportal_ws","helius_logs")  # Fresh-pass lähteet

class DiscoveryCfg:
    helius_programs: list = ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]  # SPL Token
```

#### Yleiset suodatusarvot:
```python
class DiscoveryCfg:
    min_liq_usd: float = 3000.0           # Normaali min. likviditeetti
    min_liq_fresh_usd: float = 1200.0     # Tuoreiden tokenien min. likviditeetti  
    score_threshold: float = 0.65         # Min. pistemäärä hyväksymiseen
    max_top10_share: float = 0.95         # Max. top10 holder osuus (normaali)
    max_top10_share_fresh: float = 0.98   # Max. top10 holder osuus (tuore)
    fresh_window_sec: int = 90            # Tuoreus-ikkuna sekunteina
    trade_min_unique_buyers: int = 3      # Min. unique ostajat
    trade_min_trades: int = 5             # Min. kauppojen määrä
    candidate_ttl_sec: int = 600          # Kandidaatin elinaika (10 min)
```

### 🎯 **Discovery Engine Suodattimet**

#### 1. **Fresh-Pass Suodatin** (rivit 654-695)
```python
# WS-lähteiden burst-esto
if ts_now - last_seen < 0.8:           # Min. 0.8s väli eventien välillä
    return False

# Throttling per mint  
if count >= 4 and time_window < 10s:   # Max 4 eventtiä 10s sisällä
    return False

# Fresh-pass kriteerit
min_buyers = max(1, fresh_cfg.min_unique_buyers or 0)
min_trades = max(1, fresh_cfg.min_trades or 0)
ok = (buyers >= min_buyers) or ((buys + sells) >= min_trades)
```

#### 2. **Likviditeettisuodatin** (rivit 715-724)
```python
min_liq = min_liq_fresh_usd if fresh else min_liq_usd
if candidate.liquidity_usd < min_liq:
    return False  # Hylätään
```

#### 3. **Turvallisuussuodatin** (rivit 726-744)
```python
# LP-lukitus vaatimus
if require_lp_locked and not (candidate.lp_locked or candidate.lp_burned):
    controls_ok = False

# Authority renounced vaatimus  
if require_renounced and not (mint_authority_renounced and freeze_authority_renounced):
    controls_ok = False

if not controls_ok and not fresh:
    return False  # Hylätään (paitsi tuoreet)
```

#### 4. **Holder-konsentraatio** (rivit 752-760)
```python
max_share = max_top10_share_fresh if fresh else max_top10_share_norm
if candidate.top10_holder_share > max_share:
    return False  # Hylätään
```

---

## 🚀 INTEGRAATIO DISCOVERY ENGINEEN

### **Käyttöönotto** (`hybrid_trading_bot.py` rivit 1761-1768)
```python
if cfg.discovery.sources.helius_logs:
    from sources.helius_logs_newtokens import HeliusLogsNewTokensSource
    rpc_cfg = cfg.io.rpc or {}
    ws_url = rpc_cfg.get("ws_url") or "wss://mainnet.helius-rpc.com/?api-key=your-key"
    programs = getattr(cfg.discovery, "helius_programs", ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"])
    sources.append(HeliusLogsNewTokensSource(ws_url=ws_url, programs=programs))
```

### **TokenCandidate Luominen** (rivit 105-116)
```python
cand = TokenCandidate(
    mint=mint,
    symbol=symbol,  
    name=f"New Token {symbol}",
    first_seen=datetime.now(tz=ZoneInfo("Europe/Helsinki")),
    extra={
        "first_trade_ts": time.time(),
        "source": "helius_logs",
        "signature": signature,
        "program_id": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    }
)
```

**Analyysi:**
- ✅ Luo oikean TokenCandidate-objektin
- ✅ Asettaa Helsinki-aikavyöhykkeen
- ✅ Tallentaa transaktio-signatuurin
- ⚠️ Ei aseta likviditeetti/hinta tietoja (tehdään myöhemmin RPC:llä)

---

## 🎪 PISTEYTYS JA ANALYYSI

### **Pisteytysalgoritmi** (`discovery_engine.py` rivit 1010-1116)

#### 1. **Novelty Score** (ikäperusteinen)
```python
if age_min < 5:     novelty_score = 1.0    # Alle 5min = täysi piste
elif age_min < 15:  novelty_score = 0.8    # 5-15min
elif age_min < 60:  novelty_score = 0.6    # 15-60min  
else:               novelty_score = 0.3    # Yli tunti
```

#### 2. **Liquidity Score**
```python
if liquidity_usd >= 10000:  liquidity_score = 1.0
elif liquidity_usd >= 5000: liquidity_score = 0.8
else:                       liquidity_score = 0.6
```

#### 3. **Distribution Score**
```python
if top10_holder_share <= 0.5:  distribution_score = 1.0
elif top10_holder_share <= 0.7: distribution_score = 0.8
else:                           distribution_score = 0.5
```

#### 4. **Rug Risk Score** 
```python
rug_risk = 0.0
if not (mint_authority_renounced and freeze_authority_renounced):
    rug_risk += 0.3
if not (lp_locked or lp_burned):
    rug_risk += 0.2  
if top10_holder_share > 0.8:
    rug_risk += 0.2
```

#### 5. **Overall Score**
```python
base_score = (
    novelty_score * 0.25 +        # 25% paino
    liquidity_score * 0.2 +       # 20% paino
    distribution_score * 0.2 +    # 20% paino
    min(unique_buyers/50, 1.0) * 0.2 +  # 20% paino (50 ostajaa = täysi)
    min(buy_ratio/1.5, 1.0) * 0.15      # 15% paino (1.5 ratio = täysi)
)

# Bonukset
activity_bonus = 0.1 if (unique_buyers >= 20 and buys >= 20) else 0.05
momentum_bonus = 0.05 if (age_min < 2.0 and unique_buyers >= 5) else 0.03

overall_score = max(0.0, min(1.0, base_score - rug_risk_score + bonukset))
```

---

## ⚠️ TUNNISTETUT ONGELMAT JA RISKIT

### 🔴 **Kriittiset Ongelmat**

1. **Epäluotettava Mint-osoitteen Poiminta**
   - `_extract_mint_from_logs()` on liian yksinkertainen
   - Voi poimia väärän osoitteen (authority, recipient, tms.)
   - Ei käsittele erilaisia log-formaatteja

2. **Muistin Vuoto**
   - `_seen` set kasvaa loputtomiin
   - Ei TTL:ää tai siivousta vanhoille mint-osoitteille

3. **WebSocket ID Konflikti**
   - Kiinteä `id: 1` kaikille JSON-RPC kutsuille
   - Voi aiheuttaa ongelmia useammalla tilauksella

### 🟡 **Keskisuuret Ongelmat**

4. **Symbolin Poiminta Epäluotettava**
   - Yksinkertainen regex ei kata kaikkia tapauksia
   - Ei käsittele erikoismerkkejä

5. **Ei Virheenkäsittelyä Mint Validoinnille**
   - Ei tarkista onko poimittu osoite validi Solana-osoite
   - Ei validoi mint-osoitteen pituutta/formaattia

6. **Reconnect-logiikka Yksinkertainen**
   - 5s kiinteä viive uudelleenyhdistämisessä
   - Ei exponential backoff:ia

### 🟢 **Pienet Ongelmat**

7. **Logging Voisi Olla Informatiivisempi**
   - Ei kerro montako tokenia löydetty per päivä
   - Ei tilastoja onnistumisprosenteista

8. **Ei Konfiguroitavia Parametreja**
   - Burst-esto (0.8s) ja throttling (4/10s) kovakoodattu
   - Reconnect-viive (5s) kovakoodattu

---

## 📊 SUORITUSKYKY JA TEHOKKUUS

### **Vahvuudet:**
- ✅ Asynkroninen arkkitehtuuri - ei blokkaa
- ✅ WebSocket real-time - nopea reagointi
- ✅ Deduplikointi estää duplikaatit
- ✅ Graceful shutdown -tuki
- ✅ Metrics-integraatio

### **Heikkoudet:**
- ❌ Muistin käyttö kasvaa ajan myötä (`_seen` set)
- ❌ Epäluotettava mint-poiminta voi aiheuttaa false positive/negative
- ❌ Ei batch-prosessointia - yksi token kerrallaan

### **Resurssien Käyttö:**
- **Muisti:** Kasvaa ~32 bytes per nähdty mint (Base58 string)
- **CPU:** Matala, regex-prosessointi dominoi
- **Verkko:** WebSocket-yhteys + JSON parsing

---

## 🔧 SUOSITELLUT PARANNUKSET

### 🚨 **Prioriteetti 1 (Kriittinen)**

1. **Korjaa Mint-osoitteen Poiminta**
```python
def _extract_mint_from_logs(self, logs: list[str], accounts: list[str]) -> str | None:
    """Käytä transaction accounts-listaa mint-osoitteen poimintaan"""
    # Analysoi instruction data ja accounts yhdessä
    # Validoi että osoite on oikea mint (32 bytes, Base58)
```

2. **Lisää TTL `_seen` Set:ille**
```python
def __init__(self, ...):
    self._seen = {}  # mint -> timestamp
    self._seen_ttl = 3600  # 1 tunti TTL
    
def _cleanup_seen(self):
    """Siivoa vanhat merkinnät"""
    now = time.time()
    self._seen = {mint: ts for mint, ts in self._seen.items() 
                  if now - ts < self._seen_ttl}
```

### 🔶 **Prioriteetti 2 (Tärkeä)**

3. **Paranna WebSocket ID Hallintaa**
```python
def __init__(self, ...):
    self._request_id = 0
    
def _next_id(self):
    self._request_id += 1
    return self._request_id
```

4. **Lisää Mint-osoitteen Validointi**
```python
def _validate_mint_address(self, address: str) -> bool:
    """Validoi että osoite on oikea Solana mint"""
    try:
        from solders.pubkey import Pubkey
        Pubkey.from_string(address)
        return len(address) == 44  # Base58 Solana address
    except:
        return False
```

### 🔷 **Prioriteetti 3 (Hyödyllinen)**

5. **Paranna Symbolin Poimintaa**
```python
def _extract_symbol_from_logs(self, logs: list[str]) -> str | None:
    """Monipuolisempi symbolin poiminta"""
    patterns = [
        r'symbol["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'"symbol"\s*:\s*"([^"]+)"',
        r'InitializeMetadata.*symbol:\s*([A-Za-z0-9_-]+)'
    ]
    # Kokeile kaikkia patterneja
```

6. **Lisää Konfiguroitavuus**
```python
def __init__(self, ws_url: str, programs: list[str], 
             burst_threshold: float = 0.8,
             throttle_limit: int = 4,
             throttle_window: int = 10,
             reconnect_delay: int = 5):
```

---

## 📈 HELIUS API KÄYTTÖ JA RAJOITUKSET

### **Käytetyt Endpointit:**
- `logsSubscribe` - Program logs tilaus
- WebSocket connection - Real-time streaming

### **API Limits (arvio):**
- **Free Tier:** ~100 req/s
- **Pro Tier:** ~1000 req/s
- **WebSocket:** Rajoitettu samanaikaisten yhteyksien määrä

### **Optimointi Mahdollisuudet:**
1. **Batch Subscribe** - Tilaa useampi program yhdellä kutsulla
2. **Filter Optimization** - Käytä Heliuksen filttereitä vähentämään dataa
3. **Connection Pooling** - Jaa yhteys usean source:n kesken

---

## 🎯 TOIMINNALLISUUDEN ARVIOINTI

### **Toimii Hyvin:**
- ✅ Real-time uusien tokenien löytäminen
- ✅ WebSocket-yhteyden hallinta
- ✅ Asynkroninen prosessointi
- ✅ Metrics ja logging
- ✅ Integration Discovery Engineen

### **Toimii Osittain:**
- ⚠️ Mint-osoitteen poiminta (epäluotettava)
- ⚠️ Symbolin poiminta (yksinkertainen)
- ⚠️ Muistin hallinta (vuoto ajan myötä)

### **Ei Toimi:**
- ❌ Kompleksiset log-formaatit
- ❌ Pitkäaikainen muistin hallinta
- ❌ Virheellisten mint-osoitteiden suodatus

---

## 🏁 YHTEENVETO

`HeliusLogsNewTokensSource` on **toimiva mutta keskeneräinen** toteutus Solana token-seurantaan. Se tarjoaa hyvän perustan real-time token-löytämiselle, mutta sisältää useita kriittisiä ongelmia jotka voivat aiheuttaa:

1. **Väärät mint-osoitteet** - Johtaa virheellisiin analyyseihin
2. **Muistin vuodot** - Pitkäaikaisessa käytössä ongelma  
3. **Epäluotettava data** - Vaikuttaa koko Discovery Engine:n laatuun

### **Suositukset:**

🚨 **Välittömät toimenpiteet:**
- Korjaa mint-osoitteen poiminta käyttämällä transaction accounts-dataa
- Lisää TTL `_seen` set:ille muistivuodon estämiseksi
- Lisää mint-osoitteen validointi

🔶 **Lähiajan parannukset:**
- Paranna symbolin poimintaa
- Lisää konfiguroitavuutta
- Optimoi WebSocket ID hallintaa

📊 **Pitkän aikavälin:**
- Harkitse Helius DAS API:n käyttöä metadata-tietojen saamiseen
- Lisää batch-prosessointi tehokkuuden parantamiseksi
- Toteuta connection pooling useammalle source:lle

**Kokonaisarvio: 6/10** - Toimiva proof-of-concept, mutta tarvitsee merkittäviä parannuksia tuotantokäyttöön.
