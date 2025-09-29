from crewai import Agent, LLM
from .tools import web_search_tools
from .settings import load_models

models = load_models()
common = dict(allow_delegation=False, memory=True)

ChiefIdeator = Agent(
    role="Chief Ideator",
    goal=("Muodosta sijoitusideat ja hyväksymiskriteerit. Hyödynnä muistia ja"
          " samankaltaisten ideoiden oppeja. Tee selkeä teesi."),
    backstory="PM‑tason ideoitsija, kurinalainen, datasidonnainen.",
    llm=LLM(model=models["ChiefIdeator"]["llm"]),
    function_calling_llm=LLM(model=models["ChiefIdeator"].get("tools_llm", models["ChiefIdeator"]["llm"])),
    tools=web_search_tools(),
    **common,
)

MacroAnalyst = Agent(
    role="Macro/Theme Analyst",
    goal="Tutki makro- ja toimialateemat, katalyytit, ajurit ja riskit.",
    backstory="Makroekonomisti ja toimiala‑analyytikko.",
    llm=LLM(model=models["MacroAnalyst"]["llm"]),
    tools=web_search_tools(),
    **common,
)

QuantScreener = Agent(
    role="Quant Screener",
    goal="Seulo universumi ja tee nopeat tilastot/backtestit.",
    backstory="Datavetoinen kvantti.",
    llm=LLM(model=models["QuantScreener"]["llm"]),
    tools=[],
    **common,
)

RiskOfficer = Agent(
    role="Risk Officer",
    goal="Mallinna downside, skenaariot ja positiorajat.",
    backstory="Riskienhallinnan ammattilainen.",
    llm=LLM(model=models["RiskOfficer"]["llm"]),
    tools=[],
    **common,
)

FactualReviewer = Agent(
    role="Factual Reviewer",
    goal="Lähdekritiikki ja compliance‑tarkistus.",
    backstory="Pedantti faktantarkistaja.",
    llm=LLM(model=models["FactualReviewer"]["llm"]),
    tools=web_search_tools(),
    **common,
)