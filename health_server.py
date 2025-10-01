from __future__ import annotations

import logging
from aiohttp import web

from helius_token_scanner_bot import HeliusTokenScannerBot


class HealthServer:
    def __init__(self, bot: HeliusTokenScannerBot, host: str, port: int) -> None:
        self.bot = bot
        self.host = host
        self.port = port
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/trading", self.handle_trading_status)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logging.getLogger(__name__).info(
            "Health endpoint listening on http://%s:%s/health", self.host, self.port
        )
        logging.getLogger(__name__).info(
            "Trading status available on http://%s:%s/trading", self.host, self.port
        )

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def handle_health(self, request: web.Request) -> web.Response:
        data = await self.bot.health_check()
        return web.json_response(data)
    
    async def handle_trading_status(self, request: web.Request) -> web.Response:
        """Handle trading status endpoint"""
        try:
            trading_status = self.bot.get_trading_status()
            return web.json_response(trading_status)
        except Exception as e:
            return web.json_response({
                "error": f"Failed to get trading status: {e}",
                "trading_available": False
            }, status=500)
