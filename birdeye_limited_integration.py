#!/usr/bin/env python3
"""
Birdeye Limited Integration - Workaround rajoitetulle API-avaimelle
Käyttää vain toimivia endpointteja ja täydentää muilla lähteillä
"""

import os
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class BirdeyeLimitedAPI:
    """
    Rajoitettu Birdeye API wrapper
    Käyttää vain Price-endpointtia (ainoa toimiva)
    """
    
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY", "d47f313bf3e249c9a4c476bba365a772")
        self.base_url = "https://public-api.birdeye.so"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_price(self, mint_address: str) -> Optional[float]:
        """
        Hae tokenin hinta (AINOA TOIMIVA ENDPOINT)
        """
        try:
            url = f"{self.base_url}/defi/price"
            headers = {
                "X-API-KEY": self.api_key,
                "Accept": "application/json"
            }
            params = {"address": mint_address}
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data["data"].get("value", 0)
                elif response.status == 429:
                    logger.warning("⚠️ Rate limit - odota hetki")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            
        return None


class EnhancedTokenScanner:
    """
    Token Scanner joka käyttää useita lähteitä
    korvaamaan Birdeye API:n rajoitukset
    """
    
    def __init__(self):
        self.birdeye = BirdeyeLimitedAPI()
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        await self.birdeye.__aenter__()
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        await self.birdeye.__aexit__(*args)
        if self.session:
            await self.session.close()
    
    async def get_token_data(self, mint_address: str) -> Dict:
        """
        Hae token data useista lähteistä
        """
        token_data = {
            "mint": mint_address,
            "price": None,
            "price_source": None,
            "metadata": {},
            "dex_data": {},
            "security": {}
        }
        
        # 1. Hae hinta Birdeyestä (toimii)
        price = await self.birdeye.get_price(mint_address)
        if price:
            token_data["price"] = price
            token_data["price_source"] = "birdeye"
            self.logger.info(f"✅ Birdeye price: ${price:.6f}")
        
        # 2. Hae DexScreener data (ilmainen)
        dex_data = await self.get_dexscreener_data(mint_address)
        if dex_data:
            token_data["dex_data"] = dex_data
            if not token_data["price"] and dex_data.get("priceUsd"):
                token_data["price"] = float(dex_data["priceUsd"])
                token_data["price_source"] = "dexscreener"
            self.logger.info(f"✅ DexScreener data haettu")
        
        # 3. Hae Jupiter price (ilmainen)
        jupiter_price = await self.get_jupiter_price(mint_address)
        if jupiter_price and not token_data["price"]:
            token_data["price"] = jupiter_price
            token_data["price_source"] = "jupiter"
            self.logger.info(f"✅ Jupiter price: ${jupiter_price:.6f}")
        
        # 4. Hae Solscan data (ilmainen, rajoitettu)
        solscan_data = await self.get_solscan_data(mint_address)
        if solscan_data:
            token_data["metadata"].update(solscan_data)
            self.logger.info(f"✅ Solscan metadata haettu")
        
        return token_data
    
    async def get_dexscreener_data(self, mint_address: str) -> Optional[Dict]:
        """
        Hae data DexScreeneristä (ilmainen, ei API-avainta)
        """
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("pairs"):
                        # Palauta eniten likviditeettiä omaava pari
                        pairs = sorted(data["pairs"], 
                                     key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), 
                                     reverse=True)
                        if pairs:
                            return pairs[0]
        except Exception as e:
            logger.debug(f"DexScreener error: {e}")
            
        return None
    
    async def get_jupiter_price(self, mint_address: str) -> Optional[float]:
        """
        Hae hinta Jupiter Aggregatorista
        """
        try:
            url = f"https://price.jup.ag/v4/price?ids={mint_address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and mint_address in data["data"]:
                        return data["data"][mint_address].get("price", 0)
        except Exception as e:
            logger.debug(f"Jupiter error: {e}")
            
        return None
    
    async def get_solscan_data(self, mint_address: str) -> Optional[Dict]:
        """
        Hae metadata Solscanista (rajoitettu ilmainen)
        """
        try:
            url = f"https://public-api.solscan.io/token/meta?tokenAddress={mint_address}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"Solscan error: {e}")
            
        return None
    
    async def scan_new_tokens(self) -> List[Dict]:
        """
        Skannaa uusia tokeneita käyttäen ilmaisia lähteitä
        """
        new_tokens = []
        
        # 1. DexScreener latest tokens
        try:
            url = "https://api.dexscreener.com/latest/dex/search?q=SOL"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("pairs"):
                        for pair in data["pairs"][:10]:
                            token_data = {
                                "mint": pair.get("baseToken", {}).get("address"),
                                "symbol": pair.get("baseToken", {}).get("symbol"),
                                "name": pair.get("baseToken", {}).get("name"),
                                "price": float(pair.get("priceUsd", 0)),
                                "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                                "volume": float(pair.get("volume", {}).get("h24", 0)),
                                "priceChange": float(pair.get("priceChange", {}).get("h24", 0)),
                                "source": "dexscreener",
                                "pairAddress": pair.get("pairAddress")
                            }
                            
                            # Täydennä Birdeye-hinnalla jos mahdollista
                            birdeye_price = await self.birdeye.get_price(token_data["mint"])
                            if birdeye_price:
                                token_data["birdeye_price"] = birdeye_price
                            
                            new_tokens.append(token_data)
                            
        except Exception as e:
            logger.error(f"Token scan error: {e}")
        
        return new_tokens


async def test_limited_api():
    """
    Testaa rajoitettu API
    """
    print("\n🔧 BIRDEYE LIMITED API TEST")
    print("="*50)
    
    async with EnhancedTokenScanner() as scanner:
        # Test SOL
        print("\n📊 Testing SOL data:")
        sol_data = await scanner.get_token_data("So11111111111111111111111111111111111111112")
        
        print(f"  Price: ${sol_data['price']:.2f}")
        print(f"  Source: {sol_data['price_source']}")
        
        if sol_data["dex_data"]:
            print(f"  Liquidity: ${sol_data['dex_data'].get('liquidity', {}).get('usd', 0):,.0f}")
            print(f"  Volume 24h: ${sol_data['dex_data'].get('volume', {}).get('h24', 0):,.0f}")
        
        # Scan new tokens
        print("\n🔍 Scanning new tokens:")
        tokens = await scanner.scan_new_tokens()
        
        print(f"  Found {len(tokens)} tokens")
        
        for token in tokens[:3]:
            print(f"\n  {token['symbol']}:")
            print(f"    Price: ${token['price']:.8f}")
            print(f"    Liquidity: ${token['liquidity']:,.0f}")
            print(f"    Volume: ${token['volume']:,.0f}")
            if token.get("birdeye_price"):
                print(f"    Birdeye: ${token['birdeye_price']:.8f}")
    
    print("\n" + "="*50)
    print("✅ WORKAROUND TOIMII!")
    print("\nKäytä tätä kunnes saat täyden Birdeye API-avaimen")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_limited_api())