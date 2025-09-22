#!/usr/bin/env python3
"""
Yksinkertainen Birdeye integraatio rajoitetulle API-avaimelle
Käyttää vain toimivaa /defi/price endpointtia
"""

import os
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class BirdeyeSimple:
    """Minimalistinen Birdeye wrapper - vain hinta toimii"""
    
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY", "d47f313bf3e249c9a4c476bba365a772")
        self.initialized = False
        
    async def initialize(self):
        """Yhteensopivuus vanhalle koodille"""
        self.initialized = True
        logger.info("✅ Birdeye Simple initialized (limited API)")
        return True
    
    async def get_token_price(self, mint_address: str) -> Optional[float]:
        """Hae tokenin hinta - AINOA TOIMIVA METODI"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://public-api.birdeye.so/defi/price"
                headers = {"X-API-KEY": self.api_key, "Accept": "application/json"}
                params = {"address": mint_address}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            return data["data"].get("value", 0)
                    elif response.status == 429:
                        await asyncio.sleep(1)  # Rate limit
        except Exception as e:
            logger.debug(f"Price fetch error: {e}")
        return None
    
    # Dummy metodit yhteensopivuudelle - palauttavat None/tyhjää
    async def get_token_info(self, mint_address: str) -> Optional[Dict]:
        """EI TOIMI - palauttaa vain hinnan"""
        price = await self.get_token_price(mint_address)
        if price:
            return {"data": {"price": price, "address": mint_address}}
        return None
    
    async def get_token_security(self, mint_address: str) -> Optional[Dict]:
        """EI TOIMI rajoitetulla avaimella"""
        return None
    
    async def get_token_holders(self, mint_address: str) -> Optional[Dict]:
        """EI TOIMI rajoitetulla avaimella"""
        return None
    
    async def get_new_tokens(self, limit: int = 50) -> Optional[List]:
        """EI TOIMI rajoitetulla avaimella"""
        return []
    
    async def get_trending_tokens(self, limit: int = 20) -> Optional[List]:
        """EI TOIMI rajoitetulla avaimella"""
        return []
    
    class key_manager:
        """Dummy Key Manager yhteensopivuudelle"""
        @staticmethod
        async def get_key():
            return os.getenv("BIRDEYE_API_KEY", "d47f313bf3e249c9a4c476bba365a772")
        
        @staticmethod
        async def get_status():
            return {
                "total_keys": 1,
                "active_keys": 1,
                "current_key": "limited",
                "stats": {"total_requests": 0}
            }

# Singleton
birdeye = BirdeyeSimple()

print("⚠️ HUOM: Käytössä rajoitettu Birdeye API - vain hinnat toimivat!")
print("  Muut botit voivat käyttää tätä, mutta vain get_token_price() toimii.")
