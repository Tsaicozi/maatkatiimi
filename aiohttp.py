from __future__ import annotations

import json as _json


class _Content:
    async def readany(self):
        return b""


class ClientResponse:
    def __init__(self, status: int = 200, payload: dict | None = None):
        self.status = status
        self._payload = payload or {"ok": True, "result": []}
        self.content = _Content()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return _json.dumps(self._payload)

    async def json(self):
        return self._payload


class ClientSession:
    def __init__(self, *_, **__):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *_, **__):
        return ClientResponse(200, {"ok": True})

    async def get(self, *_, **__):
        return ClientResponse(200, {"ok": True, "result": []})


class TCPConnector:
    def __init__(self, *_, **__):
        pass

