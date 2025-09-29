from pathlib import Path
import yaml

def load_models(path: str = "./crew/models.yml"):
    p = Path(path)
    if not p.exists():
        return {
            "ChiefIdeator": {"llm": "openai/gpt-4", "tools_llm": "openai/gpt-4o-mini"},
            "MacroAnalyst": {"llm": "anthropic/claude-3-5-sonnet-latest"},
            "QuantScreener": {"llm": "openai/gpt-4o-mini"},
            "RiskOfficer": {"llm": "anthropic/claude-3-5-sonnet-latest"},
            "FactualReviewer": {"llm": "anthropic/claude-3-5-sonnet-latest"},
        }
    return yaml.safe_load(p.read_text(encoding="utf-8"))