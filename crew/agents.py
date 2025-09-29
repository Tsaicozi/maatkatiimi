from crewai import Agent
from .tools import web_search_tools
from .memory import LocalMemory

mem = LocalMemory()

Researcher = Agent(
    role="Researcher",
    goal=(
        "Etsi luotettavat lähteet, tee lähdekritiikki, tallenna tiivistelmät muistioon"
    ),
    backstory=(
        "Kokenut tutkija, joka käyttää vain verifioituja lähteitä ja dokumentoi"
        " havainnot. Kirjoittaa lähdeviitteet ja varoitukset epävarmuuksista."
    ),
    tools=web_search_tools(),
    allow_delegation=False,
    memory=True,
)

Builder = Agent(
    role="Builder",
    goal=(
        "Toteuta muutokset koodiin pieninä, testattavina askelina projektin tyylioppaiden"
        " mukaisesti."
    ),
    backstory="Senior-tason ohjelmoija, joka optimoi luettavuuden ja testattavuuden.",
    tools=[],  # Cursor hoitaa koodieditorin, Builder ei tee ulkoverkkoa
    allow_delegation=False,
    memory=True,
)

Reviewer = Agent(
    role="Reviewer",
    goal=(
        "Arvioi tutkimus ja koodimuutokset. Varmista testit, tyyli, turvallisuus ja"
        " dokumentaatio ennen yhdistämistä."
    ),
    backstory="Pedantti katselmoija, joka ei pelkää palauttaa PR:ää korjattavaksi.",
    tools=[],
    allow_delegation=False,
    memory=True,
)