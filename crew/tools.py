from crewai_tools import SerperDevTool, TavilySearchTool
from typing import List

# Valitse vain ne työkalut, joita tarvitset (rajoita agentin "toimintasäde")

def web_search_tools() -> List:
    tools = []
    try:
        tools.append(SerperDevTool())  # vaatii SERPER_API_KEY:n
    except Exception:
        pass
    try:
        tools.append(TavilySearchTool())  # vaatii TAVILY_API_KEY:n
    except Exception:
        pass
    return tools