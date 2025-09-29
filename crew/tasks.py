from crewai import Task
from .agents import Researcher, Builder, Reviewer
from .memory import mem

ResearchTask = Task(
    description=(
        "Selvitä ominaisuuden vaatimusmäärittely: {feature}. Tee 3–5 keskeistä"
        " löydöstä, riskit ja hyväksymiskriteerit. Lisää lähteet."
    ),
    expected_output=(
        "Markdown-raportti: Yhteenveto, Hyväksymiskriteerit, Riskit, Lähteet."
    ),
    agent=Researcher,
)

BuildTask = Task(
    description=(
        "Toteuta ominaisuus {feature} inkrementaalisesti. Luo tarvittavat tiedostot,"
        " muokkaa olemassa olevia ja tuota lyhyt CHANGELOG-ote."
    ),
    expected_output=(
        "Lista patch-askelia, koodipätkät ja TODO-testit. Ei suoraa deployta."
    ),
    agent=Builder,
)

ReviewTask = Task(
    description=(
        "Tarkasta tutkimus ja toteutus. Varmista että hyväksymiskriteerit täyttyvät,"
        " testit kattavat keskeiset polut ja dokumentaatio on ajan tasalla."
    ),
    expected_output=(
        "PR‑kommentit, hyväksyntä/korjauslista, julkaisuvalmiuden status."
    ),
    agent=Reviewer,
)