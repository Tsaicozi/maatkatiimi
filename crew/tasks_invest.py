from crewai import Task
from .agents_invest import ChiefIdeator, MacroAnalyst, QuantScreener, RiskOfficer, FactualReviewer
from .memory_invest import IdeaRegistry

ideas = IdeaRegistry()

Intake = Task(
    description=(
        "Muotoile sijoitusidea otsikolla ja teesillä syötteestä: {brief}."
        " Hae muistista samankaltaiset ideat ja opit. Määritä hyväksymiskriteerit."
    ),
    expected_output=(
        "IC‑draft v0: Teesi (≤2 lausetta), Mandaatin soveltuvuus, Katalyytit,"
        " Hyväksymiskriteerit, Vertailut (aiemmat ideat)."
    ),
    agent=ChiefIdeator,
)

# FAN‑OUT (rinnakkaiset syventävät tehtävät)
Theme = Task(
    description=("Laadi makro/toimiala‑osio: ajurit, riskit, ajallinen kehys."),
    expected_output="Makro/teema‑analyysi 5–8 kohtaa + lähteet.",
    agent=MacroAnalyst,
)

Screen = Task(
    description=(
        "Määritä universumi, tee perusseula ja nopea backtest/tilasto (jos soveltuu)."
    ),
    expected_output="Ticker‑lista tai basket + tilastot (perus).",
    agent=QuantScreener,
)

Risk = Task(
    description=("Kuvaa downside‑skenaariot, stop‑kriteerit ja positiorajat."),
    expected_output="Riskimatriisi + suojasuunnitelma.",
    agent=RiskOfficer,
)

# SYNTHESIZE (yhdistä fan‑outin tulokset yhdeksi IC‑draftiksi)
Synthesize = Task(
    description=(
        "Yhdistä Intake+Theme+Screen+Risk tulokset IC‑draft v1:ksi."
        " Tee pisteytys (0–5) uutuus, todennettavuus, asymmetria, katalyytit,"
        " toteutettavuus, soveltuvuus, selkeys → laske summa ja päätösehdotus."
    ),
    expected_output=(
        "IC‑draft v1 + pisteet + päätösehdotus (watchlist/active/reject)"
    ),
    agent=ChiefIdeator,
)

# REVIEWER GATE (faktat & compliance portti)
Review = Task(
    description=(
        "Faktantarkistus ja compliance‑check. Lisää lähdeviitteet, korjaa väitteet"
        " tarvittaessa. Palauta korjauslista, jos hylkäät."
    ),
    expected_output="Review‑muistio + check‑lista + final‑status.",
    agent=FactualReviewer,
)