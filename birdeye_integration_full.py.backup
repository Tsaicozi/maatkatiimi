#!/usr/bin/env python3
"""
Birdeye API Integration Module
Integroi BirdeyeKeyManager olemassa oleviin botteihin
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

# Lisää projektikansio polkuun
sys.path.insert(0, str(Path(__file__).parent))

from birdeye_key_manager import BirdeyeKeyManager, BirdeyeAPIWrapper

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Helsinki")


class BirdeyeIntegration:
    """
    Integraatioluokka joka korvaa vanhan Birdeye API -käytön
    """
    
    def __init__(self):
        self.key_manager = BirdeyeKeyManager()
        self.api_wrapper = BirdeyeAPIWrapper(self.key_manager)
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Alusta avaintenhallinta"""
        if self._initialized:
            return True
            
        try:
            # Lataa avaimet
            success = await self.key_manager.load_keys()
            if not success:
                logger.error("❌ Birdeye-avainten lataus epäonnistui")
                
                # Yritä lisätä avain ympäristömuuttujasta
                env_key = os.getenv("BIRDEYE_API_KEY")
                if env_key:
                    await self.key_manager.add_key(env_key, "env_primary")
                    success = True
                    
            self._initialized = success
            
            if success:
                status = await self.key_manager.get_status()
                logger.info(f"✅ Birdeye Integration valmis: {status['total_keys']} avainta")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Alustusvirhe: {e}")
            return False
    
    async def get_token_info(self, mint_address: str) -> Optional[Dict]:
        """Hae tokenin tiedot Birdeyesta"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = f"https://public-api.birdeye.so/v1/token/{mint_address}"
        params = {"chain": "solana"}
        
        return await self.api_wrapper.request("GET", url, params=params)
    
    async def get_token_price(self, mint_address: str) -> Optional[float]:
        """Hae tokenin hinta"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = f"https://public-api.birdeye.so/v1/token/price"
        params = {
            "chain": "solana",
            "address": mint_address
        }
        
        result = await self.api_wrapper.request("GET", url, params=params)
        if result and "data" in result:
            return result["data"].get("value")
        return None
    
    async def get_token_security(self, mint_address: str) -> Optional[Dict]:
        """Hae tokenin turvallisuustiedot"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = f"https://public-api.birdeye.so/v1/token/security"
        params = {
            "chain": "solana",
            "address": mint_address
        }
        
        return await self.api_wrapper.request("GET", url, params=params)
    
    async def get_token_holders(self, mint_address: str) -> Optional[Dict]:
        """Hae tokenin omistajatiedot"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = f"https://public-api.birdeye.so/v1/token/holder"
        params = {
            "chain": "solana",
            "address": mint_address,
            "offset": 0,
            "limit": 20
        }
        
        return await self.api_wrapper.request("GET", url, params=params)
    
    async def get_new_tokens(self, limit: int = 50) -> Optional[list]:
        """Hae uusimmat tokenid"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = "https://public-api.birdeye.so/v1/token/new_listing"
        params = {
            "chain": "solana",
            "limit": limit,
            "sort": "created_at",
            "order": "desc"
        }
        
        result = await self.api_wrapper.request("GET", url, params=params)
        if result and "data" in result:
            return result["data"].get("items", [])
        return None
    
    async def get_trending_tokens(self, limit: int = 20) -> Optional[list]:
        """Hae trending-tokenit"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = "https://public-api.birdeye.so/v1/token/trending"
        params = {
            "chain": "solana",
            "limit": limit
        }
        
        result = await self.api_wrapper.request("GET", url, params=params)
        if result and "data" in result:
            return result["data"].get("items", [])
        return None
    
    async def search_tokens(self, query: str) -> Optional[list]:
        """Etsi tokeneita nimellä tai symbolilla"""
        if not self._initialized:
            if not await self.initialize():
                return None
        
        url = "https://public-api.birdeye.so/v1/token/search"
        params = {
            "chain": "solana",
            "keyword": query,
            "limit": 10
        }
        
        result = await self.api_wrapper.request("GET", url, params=params)
        if result and "data" in result:
            return result["data"].get("items", [])
        return None
    
    def get_api_key(self) -> Optional[str]:
        """
        Yhteensopivuusmetodi vanhoille boteille.
        HUOM: Tämä on deprecated, käytä mieluummin metodeja suoraan.
        """
        logger.warning("⚠️ get_api_key() on vanhentunut, käytä integraatiometodeja")
        # Palauta None, jotta botit käyttäisivät integraatiota
        return None


# Singleton-instanssi helppoa käyttöä varten
birdeye = BirdeyeIntegration()


# Päivitä HybridTradingBot käyttämään uutta integraatiota
def patch_hybrid_trading_bot():
    """
    Monkey-patch HybridTradingBot käyttämään uutta Birdeye-integraatiota
    """
    try:
        from hybrid_trading_bot import HybridTradingBot
        
        # Tallenna alkuperäiset metodit
        original_init = HybridTradingBot.__init__
        original_get_token_data = HybridTradingBot.get_token_data_from_birdeye
        
        def new_init(self, *args, **kwargs):
            """Päivitetty __init__"""
            original_init(self, *args, **kwargs)
            # Korvaa birdeye_api_key uudella integraatiolla
            self.birdeye_integration = birdeye
            self.birdeye_api_key = None  # Ei käytä vanhaa avainta
            logger.info("✅ HybridTradingBot käyttää uutta Birdeye-integraatiota")
        
        async def new_get_token_data(self, mint_address: str) -> Optional[Dict]:
            """Päivitetty get_token_data_from_birdeye"""
            try:
                # Käytä uutta integraatiota
                token_info = await self.birdeye_integration.get_token_info(mint_address)
                if not token_info:
                    return None
                
                # Hae turvallisuustiedot
                security = await self.birdeye_integration.get_token_security(mint_address)
                
                # Hae omistajatiedot
                holders = await self.birdeye_integration.get_token_holders(mint_address)
                
                # Yhdistä tiedot
                return {
                    "token_info": token_info,
                    "security": security,
                    "holders": holders,
                    "fetched_at": datetime.now(TZ).isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Virhe token-datan haussa: {e}")
                return None
        
        # Korvaa metodit
        HybridTradingBot.__init__ = new_init
        HybridTradingBot.get_token_data_from_birdeye = new_get_token_data
        
        logger.info("✅ HybridTradingBot patched onnistuneesti")
        return True
        
    except ImportError:
        logger.warning("⚠️ HybridTradingBot ei löydy, skipping patch")
        return False
    except Exception as e:
        logger.error(f"❌ Patching epäonnistui: {e}")
        return False


# Päivitä BirdeyeWSNewListingsSource käyttämään uutta integraatiota
def patch_birdeye_ws_source():
    """
    Päivitä BirdeyeWSNewListingsSource käyttämään avaintenhallintaa
    """
    try:
        from sources.birdeye_ws_newlistings import BirdeyeWSNewListingsSource
        
        original_init = BirdeyeWSNewListingsSource.__init__
        
        def new_init(self, ws_url: str = "wss://public-api.birdeye.so/socket", api_key: str | None = None):
            """Päivitetty __init__ joka hakee avaimen automaattisesti"""
            # Jos avainta ei annettu, hae se managerista
            if not api_key:
                # Tämä on synkroninen kutsu async-kontekstissa, joten käytä asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Jos loop käynnissä, luo task
                    task = asyncio.create_task(birdeye.key_manager.get_key())
                    api_key = None  # Käytä None nyt, päivitetään myöhemmin
                else:
                    # Jos ei loopia, suorita synkronisesti
                    api_key = loop.run_until_complete(birdeye.key_manager.get_key())
            
            original_init(self, ws_url, api_key)
            self._key_manager = birdeye.key_manager
            logger.info("✅ BirdeyeWSNewListingsSource käyttää avaintenhallintaa")
        
        BirdeyeWSNewListingsSource.__init__ = new_init
        
        logger.info("✅ BirdeyeWSNewListingsSource patched onnistuneesti")
        return True
        
    except ImportError:
        logger.warning("⚠️ BirdeyeWSNewListingsSource ei löydy")
        return False
    except Exception as e:
        logger.error(f"❌ WS source patching epäonnistui: {e}")
        return False


# Automaattinen patchaus importin yhteydessä
def auto_patch():
    """Patchaa kaikki tunnetut Birdeye-käyttäjät"""
    results = {
        "hybrid_trading_bot": patch_hybrid_trading_bot(),
        "birdeye_ws_source": patch_birdeye_ws_source()
    }
    
    success_count = sum(1 for v in results.values() if v)
    logger.info(f"📊 Patching tulokset: {success_count}/{len(results)} onnistui")
    
    return results


# Testifunktio
async def test_integration():
    """Testaa Birdeye-integraatio"""
    print("\n🧪 Testataan Birdeye-integraatiota...")
    
    # Alusta
    if not await birdeye.initialize():
        print("❌ Alustus epäonnistui")
        return False
    
    # Hae status
    status = await birdeye.key_manager.get_status()
    print(f"\n📊 Avainten status:")
    print(f"  - Avaimia: {status['total_keys']}")
    print(f"  - Aktiivisia: {status['active_keys']}")
    
    # Testaa API-kutsu (esim. USDC)
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    print(f"\n🔍 Haetaan USDC tiedot...")
    
    token_info = await birdeye.get_token_info(usdc_mint)
    if token_info:
        print(f"✅ Token info haettu: {token_info.get('data', {}).get('symbol', 'Unknown')}")
    else:
        print("❌ Token info haku epäonnistui")
    
    # Testaa hinta
    price = await birdeye.get_token_price(usdc_mint)
    if price:
        print(f"✅ Hinta: ${price}")
    else:
        print("❌ Hinnan haku epäonnistui")
    
    # Testaa uudet tokenit
    print(f"\n🆕 Haetaan uusia tokeneita...")
    new_tokens = await birdeye.get_new_tokens(limit=5)
    if new_tokens:
        print(f"✅ Löytyi {len(new_tokens)} uutta tokenia")
        for token in new_tokens[:3]:
            print(f"  - {token.get('symbol', 'Unknown')}: {token.get('name', 'Unknown')}")
    else:
        print("❌ Uusien tokenien haku epäonnistui")
    
    print("\n✅ Testit suoritettu")
    return True


# CLI-käyttö
async def main():
    """CLI pääohjelma"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Birdeye API Integration Manager")
    parser.add_argument("command", choices=["test", "patch", "status", "add-key"],
                       help="Komento suoritettavaksi")
    parser.add_argument("--key", help="API-avain (add-key komennolla)")
    parser.add_argument("--name", help="Avaimen nimi (add-key komennolla)")
    
    args = parser.parse_args()
    
    if args.command == "test":
        await test_integration()
        
    elif args.command == "patch":
        results = auto_patch()
        print(f"\n📊 Patching tulokset:")
        for module, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {module}")
            
    elif args.command == "status":
        if not await birdeye.initialize():
            print("❌ Alustus epäonnistui")
            return
            
        status = await birdeye.key_manager.get_status()
        print(f"\n📊 Birdeye API Status:")
        print(f"  Avaimia yhteensä: {status['total_keys']}")
        print(f"  Aktiivisia: {status['active_keys']}")
        print(f"  Nykyinen avain: {status['current_key']}")
        print(f"\n  Tilastot:")
        for key, value in status['stats'].items():
            print(f"    - {key}: {value}")
        print(f"\n  Avaimet:")
        for key in status['keys']:
            active = "✅" if key['is_active'] else "❌"
            print(f"    {active} {key['name']}: {key['request_count']} pyyntöä")
            
    elif args.command == "add-key":
        if not args.key:
            print("❌ Anna avain --key parametrilla")
            return
            
        if not await birdeye.initialize():
            print("❌ Alustus epäonnistui")
            return
            
        success = await birdeye.key_manager.add_key(args.key, args.name)
        if success:
            print(f"✅ Avain lisätty: {args.name or 'uusi_avain'}")
        else:
            print("❌ Avaimen lisäys epäonnistui")


if __name__ == "__main__":
    # Lataa .env jos on
    env_path = Path(".env")
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv()
    
    # Aseta lokitus
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suorita pääohjelma
    asyncio.run(main())