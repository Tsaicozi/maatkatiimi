"""
Raydium New Pools Source
Kuuntelee Raydium DEX:n uusia pool-tapahtumia WebSocket:in kautta
"""

import asyncio
import logging
import time
import contextlib
from typing import Optional, Dict, Any
from discovery_engine import TokenCandidate

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RaydiumNewPoolsSource:
    """
    Raydium new pools data source
    
    Kuuntelee WebSocket eventeitä ja muuntaa ne TokenCandidate objekteiksi
    """
    
    def __init__(self, ws_client):
        """
        Alusta Raydium source
        
        Args:
            ws_client: WebSocket client instance
        """
        self.ws_client = ws_client
        self.running = False
        
        logger.info("RaydiumNewPoolsSource alustettu")

    async def start(self) -> None:
        """Käynnistä data lähde"""
        self.running = True
        logger.info("🚀 RaydiumNewPoolsSource käynnistetty")

    async def stop(self) -> None:
        """Sammuta data lähde"""
        self.running = False
        logger.info("🛑 RaydiumNewPoolsSource sammutettu")

    async def get_new_tokens(self) -> list[TokenCandidate]:
        """
        Hae uudet tokenit (ei käytetä tässä toteutuksessa)
        
        Returns:
            Tyhjä lista - data tulee WebSocket:in kautta
        """
        return []

    async def run(self, queue: asyncio.Queue[TokenCandidate]) -> None:
        """
        Pääsilmukka - kuuntelee WebSocket eventeitä ja puskee TokenCandidate:ja
        
        Args:
            queue: Queue johon TokenCandidate objektit pusketaan
        """
        logger.info("🎯 RaydiumNewPoolsSource run() käynnistetty")
        
        if self.ws_client is None:
            logger.warning("Raydium WS-klientti puuttuu (ws_client=None) – lähde ohitetaan.")
            return
        
        try:
            # Tilaa new pools eventit
            await self.ws_client.subscribe_new_pools()
            
            # Kuuntele eventeitä
            async for event in self.ws_client.listen():
                if not self.running:
                    break
                
                try:
                    # Muunna event TokenCandidate:ksi
                    candidate = await self._parse_new_pool_event(event)
                    if candidate:
                        # Puskee queueen
                        await queue.put(candidate)
                        logger.debug(f"✅ TokenCandidate lisätty queueen: {candidate.symbol}")
                    
                except Exception as e:
                    logger.error(f"Virhe käsiteltäessä Raydium eventiä: {e}")
                    continue
                    
        except asyncio.CancelledError:
            # TÄRKEÄÄ: sulje WebSocket ja kupla ulos
            logger.info("🛑 RaydiumNewPoolsSource run() peruttu - suljetaan WebSocket")
            with contextlib.suppress(Exception):
                await self.ws_client.unsubscribe_new_pools()
            raise  # Kupla ulos jotta task päättyy
        except Exception as e:
            logger.error(f"Kriittinen virhe RaydiumNewPoolsSource run():ssa: {e}")
            await asyncio.sleep(0.2)  # Lyhyt tauko virheiden välillä
        finally:
            # Varmista että WebSocket tilaus perutaan
            with contextlib.suppress(Exception):
                await self.ws_client.unsubscribe_new_pools()

    async def _parse_new_pool_event(self, event: Dict[str, Any]) -> Optional[TokenCandidate]:
        """
        Muunna Raydium new pool event TokenCandidate:ksi
        
        Args:
            event: WebSocket event data
            
        Returns:
            TokenCandidate objekti tai None jos parsing epäonnistuu
        """
        try:
            # Raydium event rakenteen oletukset (täytyy mukauttaa todellisen API:n mukaan)
            # Oletetaan että event sisältää pool-tiedot
            
            # Hae perustiedot eventistä
            # TÄRKEÄÄ: Mukauta nämä kentät todellisen Raydium API:n mukaan
            mint_address = event.get('mint') or event.get('tokenMint') or event.get('baseMint')
            pool_address = event.get('pool') or event.get('poolId') or event.get('address')
            
            # Symbol ja name (voi olla saatavilla tai ei)
            symbol = event.get('symbol') or event.get('baseSymbol') or event.get('tokenSymbol', 'UNKNOWN')
            name = event.get('name') or event.get('baseName') or event.get('tokenName', 'Unknown Token')
            
            # Decimals (usein saatavilla)
            decimals = event.get('decimals') or event.get('baseDecimals') or 6  # Default 6
            
            # Likviditeetti tiedot
            liquidity_usd = event.get('liquidity') or event.get('liquidityUsd') or 0.0
            
            # Holder jakelu (ei todennäköisesti saatavilla suoraan)
            top10_holder_share = event.get('top10HolderShare') or 0.0
            
            # Authority tiedot (ei todennäköisesti saatavilla suoraan)
            mint_authority_renounced = event.get('mintAuthorityRenounced', False)
            freeze_authority_renounced = event.get('freezeAuthorityRenounced', False)
            
            # LP tiedot
            lp_locked = event.get('lpLocked', False)
            lp_burned = event.get('lpBurned', False)
            
            # Varmista että vaadittavat kentät löytyvät
            if not mint_address:
                logger.warning("Raydium event: mint address puuttuu")
                return None
            
            if not pool_address:
                logger.warning("Raydium event: pool address puuttuu")
                return None
            
            # Luo TokenCandidate
            candidate = TokenCandidate(
                mint=mint_address,
                symbol=symbol,
                name=name,
                decimals=decimals,
                liquidity_usd=float(liquidity_usd),
                top10_holder_share=float(top10_holder_share),
                lp_locked=bool(lp_locked),
                lp_burned=bool(lp_burned),
                mint_authority_renounced=bool(mint_authority_renounced),
                freeze_authority_renounced=bool(freeze_authority_renounced),
                age_minutes=0.0,  # Uusi pool
                unique_buyers_5m=0,  # Ei vielä dataa
                buy_sell_ratio=1.0,  # Neutral
                source="raydium_newpools",
                first_seen=time.time()
            )
            
            logger.info(f"✅ Raydium TokenCandidate luotu: {candidate.symbol} (mint: {candidate.mint[:8]}...)")
            return candidate
            
        except Exception as e:
            logger.error(f"Virhe parsin Raydium eventiä: {e}")
            logger.debug(f"Event data: {event}")
            return None

    def _extract_pool_metadata(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Poimi pool metadata eventistä
        
        Args:
            event: Raw event data
            
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        # Pool perustiedot
        metadata['pool_address'] = event.get('pool') or event.get('poolId')
        metadata['pool_type'] = event.get('poolType') or event.get('type')
        
        # Token perustiedot
        metadata['base_mint'] = event.get('baseMint') or event.get('mint')
        metadata['quote_mint'] = event.get('quoteMint') or event.get('quoteToken')
        
        # Pricing tiedot
        metadata['initial_price'] = event.get('initialPrice') or event.get('price')
        metadata['price_change'] = event.get('priceChange') or event.get('change')
        
        # Volume tiedot
        metadata['volume_24h'] = event.get('volume24h') or event.get('volume')
        metadata['volume_usd'] = event.get('volumeUsd') or event.get('volumeUSD')
        
        # Timestamp
        metadata['created_at'] = event.get('createdAt') or event.get('timestamp') or time.time()
        
        return metadata

    async def _validate_pool_event(self, event: Dict[str, Any]) -> bool:
        """
        Validoi että pool event sisältää tarvittavat tiedot
        
        Args:
            event: Event data
            
        Returns:
            True jos event on validi
        """
        required_fields = ['mint', 'pool']
        alternative_fields = [
            ['tokenMint', 'poolId'],
            ['baseMint', 'address']
        ]
        
        # Tarkista vaaditut kentät
        for field in required_fields:
            if field in event and event[field]:
                return True
        
        # Tarkista vaihtoehtoiset kentät
        for alt_fields in alternative_fields:
            if all(event.get(field) for field in alt_fields):
                return True
        
        logger.warning("Raydium event ei sisällä vaadittuja kenttiä")
        return False

    async def _enrich_candidate_from_event(self, candidate: TokenCandidate, event: Dict[str, Any]) -> None:
        """
        Rikasoi TokenCandidate lisätiedoilla eventistä
        
        Args:
            candidate: TokenCandidate objekti
            event: Raw event data
        """
        try:
            # Volume tiedot
            volume_24h = event.get('volume24h') or event.get('volume')
            if volume_24h:
                candidate._rpc_data_cache['volume_24h'] = float(volume_24h)
            
            # Price tiedot
            price = event.get('price') or event.get('initialPrice')
            if price:
                candidate._rpc_data_cache['price'] = float(price)
            
            # Pool tiedot
            pool_type = event.get('poolType') or event.get('type')
            if pool_type:
                candidate._rpc_data_cache['pool_type'] = pool_type
            
            # Market cap (jos saatavilla)
            market_cap = event.get('marketCap') or event.get('fdv')
            if market_cap:
                candidate._rpc_data_cache['market_cap'] = float(market_cap)
            
            logger.debug(f"TokenCandidate rikastettu: {candidate.symbol}")
            
        except Exception as e:
            logger.warning(f"Virhe rikastettaessa TokenCandidate: {e}")

# Test function
async def test_raydium_source():
    """Testaa RaydiumNewPoolsSource"""
    logger.info("🧪 Testataan RaydiumNewPoolsSource...")
    
    # Mock WebSocket client
    class MockWSClient:
        async def subscribe_new_pools(self):
            logger.info("Mock: Tilattu new pools")
        
        async def unsubscribe_new_pools(self):
            logger.info("Mock: Tilaus peruttu")
        
        async def listen(self):
            # Simuloi muutama event
            mock_events = [
                {
                    'mint': 'test_mint_123',
                    'pool': 'test_pool_456',
                    'symbol': 'TEST',
                    'name': 'Test Token',
                    'decimals': 6,
                    'liquidity': 5000.0,
                    'volume24h': 1000.0
                },
                {
                    'baseMint': 'test_mint_789',
                    'poolId': 'test_pool_012',
                    'baseSymbol': 'TEST2',
                    'baseName': 'Test Token 2',
                    'baseDecimals': 9,
                    'liquidityUsd': 7500.0
                }
            ]
            
            for event in mock_events:
                yield event
                await asyncio.sleep(0.1)
    
    # Luo source ja testaa
    ws_client = MockWSClient()
    source = RaydiumNewPoolsSource(ws_client)
    
    queue = asyncio.Queue()
    
    try:
        await source.start()
        
        # Aja lyhyesti
        task = asyncio.create_task(source.run(queue))
        await asyncio.sleep(0.5)
        task.cancel()
        
        # Tarkista queue
        candidates = []
        while not queue.empty():
            candidate = await queue.get()
            candidates.append(candidate)
        
        logger.info(f"Löydettiin {len(candidates)} TokenCandidate:ja")
        for candidate in candidates:
            logger.info(f"  {candidate.symbol}: {candidate.mint[:8]}...")
        
    finally:
        await source.stop()

if __name__ == "__main__":
    asyncio.run(test_raydium_source())
