import json, os, time, tempfile, threading
from typing import Dict, Any

class PositionManager:
    def __init__(self, path: str = "open_positions.json"):
        self.path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    self._data = json.load(f)
        except Exception:
            self._data = {}

    def _atomic_write(self):
        d = json.dumps(self._data, separators=(",", ":"), ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(prefix=".pos_", dir=os.path.dirname(self.path) or ".")
        with os.fdopen(fd, "w") as f:
            f.write(d)
        os.replace(tmp, self.path)

    def add_position(self, mint: str, payload: Dict[str, Any]):
        with self._lock:
            self._data[mint] = payload
            self._atomic_write()

    def update_position(self, mint: str, patch: Dict[str, Any]):
        with self._lock:
            if mint in self._data:
                self._data[mint].update(patch)
                self._atomic_write()

    def close_position(self, mint: str, patch: Dict[str, Any]):
        with self._lock:
            if mint in self._data:
                self._data[mint].update(patch)
                self._data[mint]["status"] = "closed"
                self._data[mint]["closed_at"] = time.time()
                self._atomic_write()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def get(self, mint: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data.get(mint, {}))
