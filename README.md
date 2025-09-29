# CrewAI + Cursor Starter

> **Oikea multi‑agentti orkestrointi** (CrewAI) ja Cursor editorina/human‑in‑the‑loopina. Mukana mallit, roolit, prosessit, työkalurajaukset, muistikerros ja valvontalokit.

## Kansiopuu

```
repo/
├─ .env.example
├─ README.md
├─ pyproject.toml   # vaihtoehtona requirements.txt
├─ requirements.txt # käytä jompaakumpaa
├─ crew/
│  ├─ __init__.py
│  ├─ crew.py              # perus crew
│  ├─ crew_invest.py       # sijoitus crew
│  ├─ agents.py            # perus agentit
│  ├─ agents_invest.py     # sijoitus agentit  
│  ├─ tasks.py             # perus tasks
│  ├─ tasks_invest.py      # sijoitus tasks
│  ├─ tools.py
│  ├─ memory.py            # perus muisti
│  ├─ memory_invest.py     # idea registry
│  ├─ settings.py          # malli-asetukset
│  ├─ models.yml           # per-agentti mallit
│  └─ config.yml
├─ run.py                  # perus crew runner
├─ run_idea.py             # sijoitus crew runner
├─ Makefile
└─ docker-compose.yml
```

## Pikastartti

### 1. Asennus
```bash
# Kopioi .env.example -> .env ja lisää API-avaimet
cp .env.example .env

# Asenna riippuvuudet
pip install -r requirements.txt
# TAI
uv pip install -r requirements.txt
```

### 2. Perus CrewAI käyttö
```bash
# Yksinkertainen feature-kehitys
python run.py "feature: lisää kirjautumissivu"

# TAI Makefile
make run
```

### 3. Investment Ideation Crew (Fin-IDEA)
```bash
# Sijoitusideointi
python run_idea.py "brief: EU data center REITit hyötyvät AI‑kysynnästä 2025–2027"

# TAI Makefile
make run-idea
```

## Cursor-integraatio

### Project Rules lisäykset:
```
- Builder‑agentti: saa muokata vain app/ ja src/, ei tests/.
- Reviewer‑agentti: kommentoi, muokkaa vain tests/ ja docs/.
```

### Työpaja:
1. **Crew tuottaa tutkimusrapsan** → tallenna `docs/research.md`
2. **Builder tekee pienet patchit** → Cursor näyttää diffit
3. **Reviewer antaa hyväksynnän** → yhdistä PR

## LLM‑asetukset

### Monimallinen kokoonpano
Muokkaa `crew/models.yml` – jokaiselle agentille oma malli:

```yaml
ChiefIdeator:
  llm: openai/gpt-4
  tools_llm: openai/gpt-4o-mini
MacroAnalyst:
  llm: anthropic/claude-3-5-sonnet-latest
QuantScreener:
  llm: openai/gpt-4o-mini
RiskOfficer:
  llm: anthropic/claude-3-5-sonnet-latest
FactualReviewer:
  llm: anthropic/claude-3-5-sonnet-latest
```

## Investment Ideation Crew (Fin‑IDEA)

### Prosessi
1. **Intake (Chief Ideator)** – v0 teesi + kriteerit + muistihaku
2. **Fan‑out** – Theme (Claude) | Screen (GPT-4o-mini) | Risk (Claude)  
3. **Synthesize (Chief Ideator)** – yhdistä & pisteytä
4. **Reviewer‑gate (Factual Reviewer)** – faktat & compliance, final‑status

### Agentit
- **Chief Ideator (CI):** johtaa ideointia, muotoilee hypoteesit, hyväksymiskriteerit
- **Macro/Theme Analyst (MA):** makro‑ ja toimialateemat, katalyytit, ajurit
- **Quant Screener (QS):** datavetoinen seulonta, yksinkertaiset backtestit
- **Risk Officer (RO):** riskit, skenaariot, drawdown‑analyysi
- **Factual Reviewer (FR):** lähdekritiikki, datapolku, compliance

### Arviointirubriikki (0–5 pistettä)
- **Uutuusarvo** (edge)
- **Todennettavuus** (data, testattavuus)  
- **Asymmetria** (yläpotentiaali vs. alariski)
- **Katalyytit** (ajurit & aikataulu)
- **Likviditeetti/Toteutettavuus**
- **Soveltuvuus mandaatille** 
- **Selkeys** (teesi 1–2 lauseessa)

### Muisti & oppiminen
- **Idearekisteri**: `.memory/ideas/` JSON-tiedostot
- **Post‑mortem‑silmukka**: suljetut ideat → opit → sääntöpäivitykset
- **Vektorimuisti** (valinnainen): Chroma/FAISS

## Käytännön esimerkit

### Perus feature
```bash
python run.py "feature: lisää käyttäjäprofiilin muokkaus"
```

### Sijoitusidea
```bash  
python run_idea.py "brief: Euroopan logistiikkakeskukset hyötyvät e-kaupan kasvusta"
```

### Docker käyttö
```bash
docker-compose up crew        # perus crew
docker-compose up crew-invest # sijoitus crew
```

## API-avaimet (.env)

```bash
# LLM-palvelut
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
XAI_API_KEY=

# Haku-/web-työkalut
SERPER_API_KEY=
TAVILY_API_KEY=

# Markkinadata (sijoituscrewlle)
ALPHAVANTAGE_API_KEY=
FRED_API_KEY=
```

## Laajennusvinkit

### Observability
- `LOG_LEVEL=DEBUG` ja ohjaa stdout CI:hin
- Lisää `rich` konsoli-outputtiin

### Muisti
- Vaihda `memory.kind: chroma` tai lisää Redis
- Vektorimuisti samankaltaisille ideoille

### Työkalut  
- Salli vain tarvittavat työkalut
- Pidä avaimet `.env`:ssä
- Lisää markkinadata-työkaluja sijoituscrewlle

### Prosessi
- `process.kind: parallel` + reviewer‑gate isoissa featuissa
- Fan-out → synthesize pattern monimutkaisemmille tehtäville

## Operatiiviset käytännöt (Fin-IDEA)

### Kynnysarvot
- Julkaise "active" vain jos kokonaispiste ≥ 20/35
- Riskisuhde hyväksyttävä

### Seuranta
- Viikkoraportti (watchlist/active)
- Automaattiset muistiinpanot hinnan/katalyytin muuttuessa

### Oppiminen
- Jokainen suljettu idea → post‑mortem
- Säännön/malli‑päivitykset

> **Huomautus**: Ei henkilökohtaista sijoitusneuvontaa. Käytä aina omaa harkintaa ja konsultoi ammattilaisia.

---

**Valmis!** Tämä paketti on tarkoitettu kevyeksi mutta tuotantokelpoiseksi pohjaksi, jota voit laajentaa tarpeen mukaan.