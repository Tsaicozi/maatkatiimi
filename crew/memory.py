from pathlib import Path

class LocalMemory:
    def __init__(self, base_dir: str = "./.memory"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, ns: str, text: str):
        p = self.base / f"{ns}.md"
        with p.open("a", encoding="utf-8") as f:
            f.write(text.strip() + "\n\n")

    def load(self, ns: str) -> str:
        p = self.base / f"{ns}.md"
        if not p.exists():
            return ""
        return p.read_text(encoding="utf-8")