from pathlib import Path
import json, uuid, datetime as dt

class IdeaRegistry:
    def __init__(self, base="./.memory/ideas"):
        self.base = Path(base); self.base.mkdir(parents=True, exist_ok=True)

    def create(self, title: str, thesis: str, tags: list[str]):
        idea_id = str(uuid.uuid4())[:8]
        payload = {
            "id": idea_id,
            "title": title,
            "thesis": thesis,
            "tags": tags,
            "status": "proposed",
            "created": dt.date.today().isoformat(),
            "history": []
        }
        (self.base / f"{idea_id}.json").write_text(json.dumps(payload, indent=2), "utf-8")
        return idea_id

    def update(self, idea_id: str, **fields):
        p = self.base / f"{idea_id}.json"
        data = json.loads(p.read_text("utf-8"))
        data.update(fields)
        p.write_text(json.dumps(data, indent=2), "utf-8")
        return data

    def append_note(self, idea_id: str, note: str):
        p = self.base / f"{idea_id}.json"
        data = json.loads(p.read_text("utf-8"))
        data.setdefault("history", []).append({"ts": dt.datetime.utcnow().isoformat(), "note": note})
        p.write_text(json.dumps(data, indent=2), "utf-8")

    def load(self, idea_id: str):
        p = self.base / f"{idea_id}.json"
        return json.loads(p.read_text("utf-8"))

    def list_all(self):
        """Lista kaikki ideat"""
        ideas = []
        for p in self.base.glob("*.json"):
            try:
                data = json.loads(p.read_text("utf-8"))
                ideas.append(data)
            except:
                continue
        return sorted(ideas, key=lambda x: x.get("created", ""), reverse=True)