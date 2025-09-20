#!/usr/bin/env python3
"""
Hybrid Trading Bot - Oikeat tokenit, Demo valuutta
Skannaa oikeita Solana tokeneita oikeasta markkinasta mutta käyttää demo valuuttaa kaupoissa
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, is_dataclass
from typing import List, Dict, Optional, Any, Callable, Set
import random
import os
from collections import deque
from dotenv import load_dotenv
from telegram_bot_integration import TelegramBot
from config import load_config

# PumpPortal Trading Client import
try:
    from integrations.pump_portal_client import PumpPortalTradingClient
except Exception:
    from pump_portal_client import PumpPortalTradingClient
from metrics import metrics

# DiscoveryEngine integration - siirretään __init__:iin
DISCOVERY_ENGINE_AVAILABLE = False
TokenCandidate = None

# PumpPortal integration
try:
    from pumpportal_integration import PumpPortalAnalyzer, PumpPortalClient
    PUMPPORTAL_AVAILABLE = True
except ImportError:
    PUMPPORTAL_AVAILABLE = False

# Lataa environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HybridToken:
    """Hybrid token dataclass - oikeat tiedot, demo trading"""
    symbol: str
    name: str
    address: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_24h: float
    price_change_7d: float
    liquidity: float
    holders: int
    fresh_holders_1d: int
    fresh_holders_7d: int
    age_minutes: int
    social_score: float
    technical_score: float
    momentum_score: float
    risk_score: float
    timestamp: str
    # Oikeat markkina tiedot
    real_price: float
    real_volume: float
    real_liquidity: float
    dex: str
    pair_address: str

class HybridTokenScanner:
    """Skannaa oikeita Solana tokeneita tai generoi mock-dataa offline-tilassa"""

    def __init__(self, telegram=None, offline_mode: bool | None = None):
        offline_env = (os.getenv("HYBRID_BOT_OFFLINE") or "").strip().lower()
        self.offline_mode = bool(offline_mode if offline_mode is not None else offline_env in {"1", "true", "yes", "on"})
        # DexScreener API endpointit dokumentaation mukaan
        self.dexscreener_base_url = "https://api.dexscreener.com"
        self.dexscreener_search_url = "https://api.dexscreener.com/latest/dex/search"
        self.dexscreener_pairs_url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        self.birdeye_url = "https://public-api.birdeye.so/public/v1/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50"
        self.coingecko_url = "https://pro-api.coingecko.com/api/v3/simple/price"
        self.moralis_url = "https://deep-index.moralis.io/api/v2/solana/mainnet/token/So11111111111111111111111111111111111111112/metadata"
        
        # Uudet Solana DEX API:t
        self.jupiter_url = "https://quote-api.jup.ag/v6"
        self.raydium_url = "https://api.raydium.io/v2"
        self.orca_url = "https://api.orca.so/v1"
        self.coinmarketcap_url = "https://pro-api.coinmarketcap.com/v1"
        self.cryptocompare_url = "https://min-api.cryptocompare.com/data"
        self.coinpaprika_url = "https://api.coinpaprika.com/v1"
        
        
        self.session = None

        # API avaimet
        self.birdeye_api_key = os.getenv('BIRDEYE_API_KEY')
        self.moralis_api_key = os.getenv('MORALIS_API_KEY')
        self.dexscreener_api_key = os.getenv('DEXSCREENER_API_KEY')
        self.coinmarketcap_api_key = os.getenv('COINMARKETCAP_API_KEY')
        self.cryptocompare_api_key = os.getenv('CRYPTOCOMPARE_API_KEY')
        
        # API health tracking
        self.api_health = {
            'dexscreener': True,
            'coinmarketcap': True,
            'cryptocompare': True,
            'pumpportal': True
        }
        
        # Backoff tracking
        self.backoff_delays = {
            'pumpportal': 1,
            'pumpfun': 1
        }
        self.last_success = {
            'pumpportal': time.time(),
            'pumpfun': time.time()
        }
        
        # Stats tracking
        self.recent_hot_candidates = []
        
        # Per-mint cooldown Telegramissa
        self.telegram_cooldown = {}  # mint -> timestamp
        
        # Burn-in seuranta
        self.hot_candidates_history = []  # [(timestamp, count), ...]
        self.cycle_durations = []  # [duration, ...]
        self.rpc_errors_history = []  # [(timestamp, error_count), ...]
        self.last_hour_reset = time.time()
        
        # Live-kauppa gate
        self.live_trading_enabled = False
        self.max_drawdown_today = 0.0
        self.daily_pnl_history = []  # [(timestamp, pnl), ...]
        
        # Telegram komentojen käsittely
        self.telegram_muted_until = 0  # timestamp
        self.manual_approvals = {}  # mint -> (timestamp, ttl_hours)
        
        # API health tarkistetaan _check_api_health metodissa
        
        # Telegram bot (injektoitu tai luotu)
        self.telegram_bot = telegram or TelegramBot()

        # DiscoveryEngine - alustetaan vain kerran
        self._de_started = False
        self.discovery_engine = None

        # REST-lähteet voidaan kytkeä helposti pois
        self.enable_rest_sources = bool(os.getenv("HYBRID_ENABLE_REST_SOURCES", "").lower() in {"1","true","yes","on"})

        # PumpPortal analyzer
        self.pump_portal_analyzer = None
        if PUMPPORTAL_AVAILABLE and not self.offline_mode:
            try:
                self.pump_portal_analyzer = PumpPortalAnalyzer()
                logger.info("✅ PumpPortal analyzer alustettu")
            except Exception as e:
                logger.warning(f"⚠️ PumpPortal analyzer alustus epäonnistui: {e}")
                self.pump_portal_analyzer = None

    async def __aenter__(self):
        if not self.offline_mode:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def scan_real_tokens(self) -> List[HybridToken]:
        """Skannaa oikeita Solana tokeneita"""
        if self.offline_mode:
            tokens = self._generate_mock_tokens()
            logger.info("🧪 Offline mode: luotiin %d synteettistä tokenia", len(tokens))
            return tokens
        logger.info("🔍 Skannataan oikeita Solana tokeneita oikeista markkinoista...")

        tokens = []
        
        if self.enable_rest_sources:
            try:
                dexscreener_tokens = await self._scan_dexscreener()
                tokens.extend(dexscreener_tokens)
                logger.info(f"✅ DexScreener: Löydettiin {len(dexscreener_tokens)} tokenia")
            except Exception as e:
                logger.warning(f"DexScreener API virhe: {e}")

            try:
                birdeye_tokens = await self._scan_birdeye()
                tokens.extend(birdeye_tokens)
                logger.info(f"✅ Birdeye: Löydettiin {len(birdeye_tokens)} tokenia")
            except Exception as e:
                logger.warning(f"Birdeye API virhe: {e}")
        else:
            logger.debug("REST-lähteet (DexScreener/Birdeye) poistettu käytöstä")
        
        # Moralis API poistettu - ei toimi
        # try:
        #     moralis_tokens = await self._scan_moralis()
        #     tokens.extend(moralis_tokens)
        #     logger.info(f"✅ Moralis: Löydettiin {len(moralis_tokens)} tokenia")
        # except Exception as e:
        #     logger.warning(f"Moralis API virhe: {e}")
        
        # Yritä CoinGecko API:ta Solana tokeneille
        try:
            coingecko_tokens = await self._scan_coingecko()
            tokens.extend(coingecko_tokens)
            logger.info(f"✅ CoinGecko: Löydettiin {len(coingecko_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"CoinGecko API virhe: {e}")
        
        # Yritä Jupiter API:ta uusille tokeneille
        try:
            jupiter_tokens = await self._scan_jupiter()
            tokens.extend(jupiter_tokens)
            logger.info(f"✅ Jupiter: Löydettiin {len(jupiter_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"Jupiter API virhe: {e}")
        
        # Yritä Raydium API:ta
        try:
            raydium_tokens = await self._scan_raydium()
            tokens.extend(raydium_tokens)
            logger.info(f"✅ Raydium: Löydettiin {len(raydium_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"Raydium API virhe: {e}")
        
        # Yritä CoinPaprika API:ta
        try:
            coinpaprika_tokens = await self._scan_coinpaprika()
            tokens.extend(coinpaprika_tokens)
            logger.info(f"✅ CoinPaprika: Löydettiin {len(coinpaprika_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"CoinPaprika API virhe: {e}")
        
        # Yritä CoinMarketCap API:ta
        try:
            coinmarketcap_tokens = await self._scan_coinmarketcap()
            tokens.extend(coinmarketcap_tokens)
            logger.info(f"✅ CoinMarketCap: Löydettiin {len(coinmarketcap_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"CoinMarketCap API virhe: {e}")
        
        # Yritä CryptoCompare API:ta
        try:
            cryptocompare_tokens = await self._scan_cryptocompare()
            tokens.extend(cryptocompare_tokens)
            logger.info(f"✅ CryptoCompare: Löydettiin {len(cryptocompare_tokens)} tokenia")
        except Exception as e:
            logger.warning(f"CryptoCompare API virhe: {e}")
        
        # Yritä Pump.fun API:ta ultra-fresh tokeneille
        try:
            pump_tokens = await self._scan_pump_fun()
            tokens.extend(pump_tokens)
            logger.info(f"✅ Pump.fun: Löydettiin {len(pump_tokens)} tokenia")
        except Exception as e:
            if "530" in str(e):
                logger.debug(f"Pump.fun API palvelin ei vastaa (530) - ohitetaan")
            else:
                logger.warning(f"Pump.fun API virhe: {e}")
        
        # Yritä PumpPortal WebSocket:ia ultra-fresh tokeneille
        try:
            if self.pump_portal_analyzer and self._is_source_healthy('pumpportal'):
                await self._wait_backoff('pumpportal')
                pump_portal_tokens = await self._scan_pump_portal()
                tokens.extend(pump_portal_tokens)
                self._update_backoff('pumpportal', True)
                logger.info(f"✅ PumpPortal: Löydettiin {len(pump_portal_tokens)} tokenia")
            elif not self._is_source_healthy('pumpportal'):
                logger.warning("⚠️ PumpPortal source unhealthy, skipataan")
        except Exception as e:
            self._update_backoff('pumpportal', False)
            logger.warning(f"PumpPortal API virhe: {e}")
        
        
        # Jos ei löytynyt oikeita tokeneita, palauta tyhjä lista
        if not tokens:
            logger.warning("❌ Ei löytynyt oikeita tokeneita API:sta")
            return []
        
        # Suodata ultra-fresh tokeneita (käytä on-chain aikaleimoja)
        ultra_fresh_tokens = [t for t in tokens if self._is_ultra_fresh(t)]
        
        logger.info(f"✅ Löydettiin {len(ultra_fresh_tokens)} ultra-fresh Solana tokenia")
        return ultra_fresh_tokens

    def _generate_mock_tokens(self) -> List[HybridToken]:
        """Generoi deterministisen pienen joukon tokeneita offline-testeihin"""
        now = datetime.utcnow().isoformat()
        tokens: List[HybridToken] = []
        for idx in range(1, 6):
            base_price = round(random.uniform(0.4, 2.5), 4)
            market_cap = base_price * random.uniform(200_000, 750_000)
            liquidity = random.uniform(15_000, 60_000)
            volume_24h = random.uniform(50_000, 250_000)
            momentum = round(random.uniform(0.3, 0.95), 3)
            technical = round(random.uniform(0.25, 0.9), 3)
            risk = round(random.uniform(0.05, 0.4), 3)
            tokens.append(HybridToken(
                symbol=f"MOCK{idx}",
                name=f"Mock Token {idx}",
                address=f"MockMint{idx:04d}",
                price=base_price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=round(random.uniform(-0.2, 0.4) * 100, 2),
                price_change_7d=round(random.uniform(-0.3, 0.6) * 100, 2),
                liquidity=liquidity,
                holders=random.randint(120, 1800),
                fresh_holders_1d=random.randint(20, 150),
                fresh_holders_7d=random.randint(40, 300),
                age_minutes=random.randint(3, 45),
                social_score=round(random.uniform(0.1, 0.9), 3),
                technical_score=technical,
                momentum_score=momentum,
                risk_score=risk,
                timestamp=now,
                real_price=base_price * random.uniform(0.95, 1.05),
                real_volume=volume_24h,
                real_liquidity=liquidity,
                dex=random.choice(["Pump.fun", "Raydium", "Jupiter"]),
                pair_address=f"MockPair{idx:04d}"
            ))
        return tokens
    
    def _age_minutes(self, cand) -> Optional[float]:
        """Laske ikä minuuteissa. Tukee sekä TokenCandidatea että dictiä."""
        try:
            extra = getattr(cand, "extra", None) or (cand.get("extra") if isinstance(cand, dict) else {}) or {}
            ts = (
                extra.get("first_pool_ts")
                or extra.get("first_trade_ts")
                or getattr(cand, "first_seen_ts", None)
                or (cand.get("first_seen_ts") if isinstance(cand, dict) else None)
            )
            if not ts:
                return None  # ⬅️ tärkein muutos: EI 0.0
            return max(0.0, (time.time() - float(ts)) / 60.0)
        except Exception as e:
            logger.warning(f"_age_minutes virhe: {e}; palautetaan None")
            return None
    
    def _is_ultra_fresh(self, token: HybridToken) -> bool:
        """
        Tarkista onko token ultra-fresh (≤ 10 minuuttia) - vain on-chain aikaleimoilla
        
        Args:
            token: HybridToken objekti
            
        Returns:
            True jos token on ultra-fresh
        """
        # Tarkista että on on-chain aikaleima
        extra = getattr(token, "extra", None) or {}
        ts = extra.get("first_pool_ts") or extra.get("first_trade_ts")
        if not ts:
            return False  # ⬅️ vain on-chain-lähteet
        
        # Ultra-fresh ehto: ikä <= 10.0 minuuttia
        age_min = (time.time() - ts) / 60.0
        return age_min <= 10.0
    
    
    async def _ping_json(self, url: str, headers: dict = None) -> int:
        """
        Ping JSON endpoint ja palauta HTTP status
        
        Args:
            url: URL johon pingataan
            headers: HTTP headers
            
        Returns:
            HTTP status code tai 599 jos virhe
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers or {}, timeout=5) as response:
                    return response.status
        except Exception:
            return 599
    
    async def _check_api_health(self):
        """Tarkista API health ja päivitä tilat"""
        # CoinMarketCap health check
        if self.coinmarketcap_api_key:
            cmc_status = await self._ping_json("https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")
            self.api_health['coinmarketcap'] = 200 <= cmc_status < 300
        
        # DexScreener health check
        if self.dexscreener_api_key:
            dex_status = await self._ping_json("https://api.dexscreener.com/latest/dex/tokens/")
            self.api_health['dexscreener'] = 200 <= dex_status < 300
        
        # CryptoCompare health check
        if self.cryptocompare_api_key:
            cc_status = await self._ping_json("https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD")
            self.api_health['cryptocompare'] = 200 <= cc_status < 300
        
        # PumpPortal health check
        if PUMPPORTAL_AVAILABLE:
            pp_status = await self._ping_json("https://frontend-api.pump.fun/coins?order=market_cap&limit=1")
            self.api_health['pumpportal'] = 200 <= pp_status < 300
        
        # Health logi tapahtuu _check_api_health metodissa
        
        # Päivitä source health metriikat
        try:
            from metrics import metrics
            if metrics:
                for source in ['pumpportal', 'pumpfun']:
                    health = 1 if self._is_source_healthy(source) else 0
                    metrics.source_health.labels(source=source).set(health)
        except Exception:
            pass
    
    def _update_backoff(self, source: str, success: bool):
        """Päivitä backoff delay"""
        if success:
            self.backoff_delays[source] = 1  # Reset
            self.last_success[source] = time.time()
        else:
            # Kasvata backoff (1, 2, 4, 8, 16, 30s max)
            self.backoff_delays[source] = min(30, self.backoff_delays[source] * 2)
    
    async def _wait_backoff(self, source: str):
        """Odota backoff delay"""
        delay = self.backoff_delays[source]
        if delay > 1:
            logger.warning(f"⏳ Backoff {source}: {delay}s")
            await asyncio.sleep(delay)
    
    def _is_source_healthy(self, source: str) -> bool:
        """Tarkista onko lähde terve"""
        time_since_success = time.time() - self.last_success[source]
        return time_since_success < 300  # 5 min
    
    async def _scan_dexscreener(self) -> List[HybridToken]:
        """Skannaa DexScreener API:sta uusia Solana tokeneita - KORJATTU"""
        tokens = []
        
        try:
            # Käytä DexScreener latest pairs endpointia uusille tokeneille - korjattu
            url = "https://api.dexscreener.com/latest/dex/tokens/solana"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('pairs'):
                        # Suodata ultra-fresh parit (viimeisen 1h sisällä luodut)
                        current_time = int(time.time() * 1000)  # Millisekunteina
                        ultra_fresh_pairs = []
                        
                        for pair in data['pairs']:
                            if pair.get('pairCreatedAt'):
                                created_at = pair['pairCreatedAt']
                                age_ms = current_time - created_at
                                age_hours = age_ms / (1000 * 60 * 60)
                                
                                # Ultra-fresh: viimeisen 1 tunnin sisällä
                                if age_hours < 1:
                                    ultra_fresh_pairs.append(pair)
                        
                        # Jos ei ultra-fresh paria, ota fresh parit (24h)
                        if not ultra_fresh_pairs:
                            for pair in data['pairs']:
                                if pair.get('pairCreatedAt'):
                                    created_at = pair['pairCreatedAt']
                                    age_ms = current_time - created_at
                                    age_hours = age_ms / (1000 * 60 * 60)
                                    
                                    if age_hours < 24:
                                        ultra_fresh_pairs.append(pair)
                        
                        # Ota top 20 fresh paria
                        for pair in ultra_fresh_pairs[:20]:
                            token = self._parse_dexscreener_pair(pair)
                            if token:
                                tokens.append(token)
                                
                elif response.status == 429:
                    logger.warning("DexScreener API rate limit")
                else:
                    logger.warning(f"DexScreener API virhe: {response.status}")
                    
        except Exception as e:
            logger.debug(f"DexScreener API virhe: {e}")
        
        return tokens
    
    async def _scan_birdeye(self) -> List[HybridToken]:
        """Skannaa Birdeye API:sta uusia Solana tokeneita - KORJATTU"""
        tokens = []
        
        try:
            # Birdeye latest tokens endpoint - korjattu
            url = "https://public-api.birdeye.so/public/v1/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-API-KEY': 'your_api_key_here'
            }
            if self.birdeye_api_key:
                headers['X-API-KEY'] = self.birdeye_api_key
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data', {}).get('tokens'):
                        for token_data in data['data']['tokens'][:20]:  # Ota top 20
                            token = self._parse_birdeye_token(token_data)
                            if token:
                                tokens.append(token)
                elif response.status == 429:
                    logger.warning("Birdeye API rate limit")
                else:
                    logger.warning(f"Birdeye API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"Birdeye API virhe: {e}")
        
        return tokens
    
    async def _scan_moralis(self) -> List[HybridToken]:
        """Skannaa Moralis API:sta Solana tokeneita"""
        tokens = []
        
        try:
            # Moralis Solana token metadata (SOL token)
            url = self.moralis_url
            headers = {
                'X-API-Key': self.moralis_api_key,
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        # Parsii SOL token metadata
                        token = self._parse_moralis_token(data)
                        if token:
                            tokens.append(token)
                elif response.status == 429:
                    logger.warning("Moralis API rate limit")
                else:
                    logger.warning(f"Moralis API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"Moralis API virhe: {e}")
        
        return tokens
    
    async def _scan_coingecko(self) -> List[HybridToken]:
        """Skannaa CoinGecko API:sta Solana tokeneita"""
        tokens = []
        
        try:
            # CoinGecko Solana tokens
            api_key = os.getenv('COINGECKO_API_KEY')
            if not api_key:
                logger.warning("CoinGecko API key puuttuu")
                return tokens
                
            url = "https://pro-api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=solana-ecosystem&order=market_cap_desc&per_page=50&page=1&sparkline=false"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'x-cg-pro-api-key': api_key
            }
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    for token_data in data[:20]:  # Ota top 20
                        token = self._parse_coingecko_token(token_data)
                        if token:
                            tokens.append(token)
                elif response.status == 429:
                    logger.warning("CoinGecko API rate limit")
                else:
                    logger.warning(f"CoinGecko API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"CoinGecko API virhe: {e}")
        
        return tokens
    
    async def _scan_jupiter(self) -> List[HybridToken]:
        """Skannaa Jupiter API:sta Solana tokeneita"""
        tokens = []
        
        try:
            # Jupiter token list - käytä oikeaa endpointia
            url = "https://token.jup.ag/strict"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        # Ota top 20 tokenia
                        for i, token_info in enumerate(data[:20]):
                            token = self._parse_jupiter_token_new(token_info)
                            if token:
                                tokens.append(token)
                elif response.status == 404:
                    logger.warning("Jupiter API: Endpoint ei löytynyt (404)")
                elif response.status == 429:
                    logger.warning("Jupiter API: Rate limit (429)")
                elif response.status == 403:
                    logger.warning("Jupiter API: Ei oikeuksia (403)")
                else:
                    logger.warning(f"Jupiter API virhe: {response.status}")
        except aiohttp.ClientError as e:
            logger.warning(f"Jupiter API pyyntövirhe: {e}")
        except Exception as e:
            logger.warning(f"Jupiter API virhe: {e}")
        
        return tokens
    
    async def _scan_raydium(self) -> List[HybridToken]:
        """Skannaa Raydium API:sta Solana tokeneita"""
        tokens = []
        
        try:
            # Raydium pool list
            url = f"{self.raydium_url}/main/pairs"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        # Ota top 20 paria
                        for pair in data[:20]:
                            token = self._parse_raydium_pair(pair)
                            if token:
                                tokens.append(token)
                elif response.status == 429:
                    logger.warning("Raydium API rate limit")
                else:
                    logger.warning(f"Raydium API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"Raydium API virhe: {e}")
        
        return tokens
    
    async def _scan_coinpaprika(self) -> List[HybridToken]:
        """Skannaa CoinPaprika API:sta Solana tokeneita"""
        tokens = []
        
        try:
            # CoinPaprika Solana tokens
            url = f"{self.coinpaprika_url}/coins"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        # Suodata Solana tokeneita
                        solana_tokens = [t for t in data if 'solana' in t.get('type', '').lower()][:20]
                        for token_data in solana_tokens:
                            token = self._parse_coinpaprika_token(token_data)
                            if token:
                                tokens.append(token)
                elif response.status == 429:
                    logger.warning("CoinPaprika API rate limit")
                else:
                    logger.warning(f"CoinPaprika API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"CoinPaprika API virhe: {e}")
        
        return tokens
    
    async def _scan_cryptocompare(self) -> List[HybridToken]:
        """Skannaa CryptoCompare API:sta Solana tokeneita"""
        tokens = []

        if not self.cryptocompare_api_key:
            logger.debug("CryptoCompare API avain puuttuu")
            return tokens

        try:
            # CryptoCompare top coins by market cap
            url = f"{self.cryptocompare_url}/data/top/mktcapfull"
            params = {
                'limit': 50,
                'tsym': 'USD',
                'api_key': self.cryptocompare_api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'Data' in data and isinstance(data['Data'], list):
                            # Ota top 20 tokenia
                            top_tokens = data['Data'][:20] if len(data['Data']) > 20 else data['Data']
                            for item in top_tokens:
                                token = self._parse_cryptocompare_token(item)
                                if token:
                                    tokens.append(token)
                    elif response.status == 429:
                        logger.warning("CryptoCompare API rate limit")
                    else:
                        logger.warning(f"CryptoCompare API virhe: {response.status}")
        except Exception as e:
            logger.debug(f"CryptoCompare API virhe: {e}")
        
        return tokens
    
    async def _scan_coinmarketcap(self) -> List[HybridToken]:
        """Skannaa CoinMarketCap API:sta Solana tokeneita"""
        tokens = []
        
        if not self.coinmarketcap_api_key:
            logger.debug("CoinMarketCap API avain puuttuu")
            return tokens
        
        try:
            # CoinMarketCap Solana tokens
            url = f"{self.coinmarketcap_url}/cryptocurrency/listings/latest"
            headers = {
                'X-CMC_PRO_API_KEY': self.coinmarketcap_api_key,
                'Accept': 'application/json'
            }
            params = {
                'start': 1,
                'limit': 100,
                'convert': 'USD'
            }
            
            async with self.session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data:
                        # Suodata Solana tokeneita
                        solana_tokens = [t for t in data['data'] if 'solana' in t.get('platform', {}).get('name', '').lower()][:20]
                        for token_data in solana_tokens:
                            token = self._parse_coinmarketcap_token(token_data)
                            if token:
                                tokens.append(token)
                elif response.status == 401:
                    logger.warning("CoinMarketCap API: Virheellinen API avain (401)")
                    self.api_health['coinmarketcap'] = False
                elif response.status == 429:
                    logger.warning("CoinMarketCap API: Rate limit (429)")
                elif response.status == 403:
                    logger.warning("CoinMarketCap API: Ei oikeuksia (403)")
                else:
                    logger.warning(f"CoinMarketCap API virhe: {response.status}")
        except aiohttp.ClientError as e:
            logger.warning(f"CoinMarketCap API pyyntövirhe: {e}")
        except Exception as e:
            logger.warning(f"CoinMarketCap API virhe: {e}")
        
        return tokens
    
    async def _scan_pump_fun(self) -> List[HybridToken]:
        """Skannaa Pump.fun API:sta ultra-fresh tokeneita - KORJATTU"""
        tokens = []
        
        try:
            # Pump.fun API - käytä oikeaa endpointia
            url = "https://frontend-api.pump.fun/coins?order=market_cap&limit=50"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://pump.fun/',
                'Origin': 'https://pump.fun'
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        for token_data in data[:20]:  # Ota top 20
                            token = self._parse_pump_fun_token(token_data)
                            if token:
                                tokens.append(token)
                elif response.status == 429:
                    logger.warning("Pump.fun API rate limit")
                elif response.status == 530:
                    logger.debug("Pump.fun API palvelin ei vastaa (530) - ohitetaan")
                else:
                    logger.warning(f"Pump.fun API virhe: {response.status}")
        except Exception as e:
            if "530" in str(e):
                logger.debug("Pump.fun API palvelin ei vastaa (530) - ohitetaan")
            else:
                logger.debug(f"Pump.fun API virhe: {e}")
        
        return tokens
    
    async def _scan_pump_portal(self) -> List[HybridToken]:
        """Skannaa PumpPortal WebSocket:sta ultra-fresh tokeneita"""
        tokens = []
        
        if not self.pump_portal_analyzer:
            return tokens
        
        try:
            # Hae hot tokenit PumpPortal:sta
            hot_tokens_result = self.pump_portal_analyzer.get_hot_tokens(20)
            
            # Käsittele sekä list- että dict-muotoiset vastaukset
            if isinstance(hot_tokens_result, list):
                hot_tokens = hot_tokens_result
            elif isinstance(hot_tokens_result, dict):
                if 'error' in hot_tokens_result:
                    logger.warning(f"PumpPortal hot tokens virhe: {hot_tokens_result['error']}")
                    return tokens
                hot_tokens = hot_tokens_result.get('hot_tokens', [])
            else:
                logger.warning(f"PumpPortal: Odottamaton vastaustyyppi: {type(hot_tokens_result)}")
                return tokens
            
            for token_data in hot_tokens:
                if not isinstance(token_data, dict):
                    logger.warning(f"PumpPortal: Skipataan ei-dict token_data: {type(token_data)}")
                    continue
                    
                token = self._parse_pump_portal_token(token_data)
                if token:
                    tokens.append(token)
                    
        except Exception as e:
            logger.warning(f"PumpPortal skanning virhe: {e}")
        
        return tokens
    
    def _parse_pump_portal_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii PumpPortal token datan"""
        try:
            token_address = token_data.get('token_address', '')
            if not token_address:
                return None
            
            # Generoi symbol ja name token addressista
            symbol = token_address[:8].upper()
            name = f"Token_{symbol}"
            
            # Ota volyymi-datasta
            volume_24h = float(token_data.get('volume_24h', 0))
            buy_volume = float(token_data.get('buy_volume', 0))
            sell_volume = float(token_data.get('sell_volume', 0))
            buy_sell_ratio = float(token_data.get('buy_sell_ratio', 1.0))
            
            # Laske hinta ja market cap (simuloidaan)
            price = volume_24h / 1000000 if volume_24h > 0 else 0.001
            market_cap = volume_24h * 10 if volume_24h > 0 else 10000
            
            # Generoi muut tiedot
            price_change_24h = random.uniform(-50, 200)  # Simuloi muutos
            price_change_7d = random.uniform(-80, 500)
            liquidity = volume_24h * 0.1
            holders = random.randint(10, 1000)
            fresh_holders_1d = random.randint(1, 100)
            fresh_holders_7d = random.randint(5, 500)
            age_minutes = random.randint(1, 60)  # Ultra-fresh
            
            # Laske skorit
            social_score = min(buy_sell_ratio * 0.3, 1.0)
            technical_score = min(volume_24h / 1000000, 1.0)
            momentum_score = min(buy_sell_ratio, 1.0)
            risk_score = max(0, 1.0 - (volume_24h / 10000000))
            
            return HybridToken(
                symbol=symbol,
                name=name,
                address=token_address,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                price_change_7d=price_change_7d,
                liquidity=liquidity,
                holders=holders,
                fresh_holders_1d=fresh_holders_1d,
                fresh_holders_7d=fresh_holders_7d,
                age_minutes=age_minutes,
                social_score=social_score,
                technical_score=technical_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                timestamp=datetime.now().isoformat(),
                # Oikeat tiedot
                real_price=price,
                real_volume=volume_24h,
                real_liquidity=liquidity,
                dex="PumpPortal",
                pair_address=token_address
            )
            
        except Exception as e:
            logger.debug(f"PumpPortal token parsing virhe: {e}")
            return None
    
    def _parse_pump_fun_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii Pump.fun token datan"""
        try:
            symbol = token_data.get('symbol', '').upper()
            name = token_data.get('name', '')
            address = token_data.get('mint', '')
            
            # Oikeat tiedot Pump.fun:sta
            price = float(token_data.get('usd_market_cap', 0)) / float(token_data.get('total_supply', 1))
            market_cap = float(token_data.get('usd_market_cap', 0))
            volume_24h = float(token_data.get('volume_24h', 0))
            
            # Laske ikä millisekunteina
            created_timestamp = token_data.get('created_timestamp', 0)
            current_time = int(time.time() * 1000)
            age_ms = current_time - created_timestamp
            age_minutes = age_ms / (1000 * 60)
            
            # Generoi muut tiedot
            price_change_24h = random.uniform(10, 400)  # Ultra-fresh tokenit
            holders = random.randint(50, 500)
            liquidity = random.uniform(5000, 50000)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                age_minutes=age_minutes,
                holders=holders,
                liquidity=liquidity,
                social_score=random.uniform(0.4, 0.9),
                technical_score=random.uniform(0.5, 0.9),
                risk_score=random.uniform(0.0, 0.2),
                momentum_score=random.uniform(0.6, 0.9),
                address=address,
                price_change_7d=random.uniform(10, 400),
                fresh_holders_1d=random.randint(5, 20),
                fresh_holders_7d=random.randint(15, 50),
                timestamp=int(time.time()),
                real_price=price,
                real_volume=volume_24h,
                real_liquidity=liquidity,
                dex="Pump.fun",
                pair_address=address
            )
        except Exception as e:
            logger.debug(f"Pump.fun token parsing virhe: {e}")
            return None
    
    def _parse_cryptocompare_token(self, data: Dict) -> Optional[HybridToken]:
        """Parsii CryptoCompare token datan"""
        try:
            coin_info = data.get('CoinInfo', {})
            raw_data = data.get('RAW', {}).get('USD', {})
            
            if not coin_info or not raw_data:
                return None
            
            symbol = coin_info.get('Name', '')
            name = coin_info.get('FullName', '')
            price = raw_data.get('PRICE', 0)
            market_cap = raw_data.get('MKTCAP', 0)
            volume_24h = raw_data.get('TOTALVOLUME24H', 0)
            price_change_24h = raw_data.get('CHANGEPCT24HOUR', 0)
            
            # Generoi mock data
            age_minutes = random.randint(1, 5)
            holders = random.randint(100, 10000)
            liquidity = random.randint(10000, 1000000)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                age_minutes=age_minutes,
                holders=holders,
                liquidity=liquidity,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.9),
                risk_score=random.uniform(0.0, 0.3),
                momentum_score=random.uniform(0.2, 0.8),
                entry_score=0.0
            )
        except Exception as e:
            logger.debug(f"CryptoCompare token parsing virhe: {e}")
            return None
    
    def _parse_coingecko_trending_token(self, data: Dict) -> Optional[HybridToken]:
        """Parsii CoinGecko trending token datan"""
        try:
            symbol = data.get('symbol', '').upper()
            name = data.get('name', '')
            market_cap_rank = data.get('market_cap_rank', 999)
            
            # Generoi mock data trending tokeneille
            price = random.uniform(0.001, 100.0)
            market_cap = random.uniform(1000000, 1000000000)
            volume_24h = random.uniform(100000, 10000000)
            price_change_24h = random.uniform(-20, 50)
            age_minutes = random.randint(1, 3)  # Ultra-fresh trending tokens
            holders = random.randint(100, 10000)
            liquidity = random.uniform(50000, 500000)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                age_minutes=age_minutes,
                holders=holders,
                liquidity=liquidity,
                social_score=random.uniform(0.7, 0.95),  # Trending = korkea social buzz
                technical_score=random.uniform(0.6, 0.9),
                risk_score=random.uniform(0.0, 0.2),
                momentum_score=random.uniform(0.5, 0.9),
                entry_score=0.0
            )
        except Exception as e:
            logger.debug(f"CoinGecko trending token parsing virhe: {e}")
            return None
    
    def _parse_coinmarketcap_token(self, data: Dict) -> Optional[HybridToken]:
        """Parsii CoinMarketCap token datan"""
        try:
            return HybridToken(
                symbol=data.get('symbol', ''),
                name=data.get('name', ''),
                address=data.get('platform', {}).get('token_address', ''),
                price=float(data.get('quote', {}).get('USD', {}).get('price', 0)),
                market_cap=float(data.get('quote', {}).get('USD', {}).get('market_cap', 0)),
                volume_24h=float(data.get('quote', {}).get('USD', {}).get('volume_24h', 0)),
                price_change_24h=float(data.get('quote', {}).get('USD', {}).get('percent_change_24h', 0)),
                price_change_7d=float(data.get('quote', {}).get('USD', {}).get('percent_change_7d', 0)),
                liquidity=float(data.get('quote', {}).get('USD', {}).get('volume_24h', 0)) * 0.1,
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=random.randint(1, 60),
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                real_price=float(data.get('quote', {}).get('USD', {}).get('price', 0)),
                real_volume=float(data.get('quote', {}).get('USD', {}).get('volume_24h', 0)),
                real_liquidity=float(data.get('quote', {}).get('USD', {}).get('volume_24h', 0)) * 0.1,
                dex='CoinMarketCap',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"CoinMarketCap token parsing virhe: {e}")
            return None
    
    async def get_real_time_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Hae real-time hinnat CoinGecko API:sta"""
        prices = {}
        if self.offline_mode:
            for symbol in symbols:
                prices[symbol] = round(random.uniform(0.5, 2.0), 4)
            return prices

        try:
            # CoinGecko coin ID mapping
            coin_mapping = {
                'BONK': 'bonk',
                'WIF': 'dogwifcoin',
                'JUP': 'jupiter-exchange-solana',
                'MYRO': 'myro',
                'POPCAT': 'popcat',
                'SLERF': 'slerf',
                'BOME': 'book-of-meme',
                'MEW': 'cat-in-a-dogs-world',
                'ACT': 'achain',
                'FIDA': 'bonfida'
            }
            
            # Kerää coin ID:t
            coin_ids = []
            for symbol in symbols:
                if symbol in coin_mapping:
                    coin_ids.append(coin_mapping[symbol])
            
            if not coin_ids:
                return prices
            
            # Hae hinnat
            api_key = os.getenv('COINGECKO_API_KEY')
            if not api_key:
                logger.warning("CoinGecko API key puuttuu - käytetään mock hintoja")
                for symbol in symbols:
                    prices[symbol] = round(random.uniform(0.5, 2.0), 4)
                return prices
                
            url = f"{self.coingecko_url}?ids={','.join(coin_ids)}&vs_currencies=usd"
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'x-cg-pro-api-key': api_key
            }
            
            async with self.session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    for symbol, coin_id in coin_mapping.items():
                        if coin_id in data and 'usd' in data[coin_id]:
                            prices[symbol] = data[coin_id]['usd']
                elif response.status == 429:
                    logger.warning("CoinGecko API rate limit - käytetään mock hintoja")
                else:
                    logger.warning(f"CoinGecko API virhe: {response.status}")
        
        except Exception as e:
            logger.debug(f"CoinGecko API virhe: {e}")
        
        return prices
    
    def _parse_dexscreener_pair(self, pair_data: Dict) -> Optional[HybridToken]:
        """Parsii DexScreener pair datan HybridToken:ksi"""
        try:
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            
            # Varmista että on Solana token
            if base_token.get('chainId') != 'solana':
                return None
            
            # Oikeat markkina tiedot
            real_price = float(pair_data.get('priceUsd', 0))
            real_volume = float(pair_data.get('volume', {}).get('h24', 0))
            real_liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
            
            # Demo tiedot (simuloi ultra-fresh token)
            age_minutes = random.randint(1, 5)
            demo_price = real_price * random.uniform(0.8, 1.2)  # ±20% variaatio
            demo_market_cap = real_liquidity * random.uniform(0.5, 2.0)
            
            # Skip tokens without proper symbol or name
            if not base_token.get('symbol') or not base_token.get('name'):
                return None
            
            return HybridToken(
                symbol=base_token.get('symbol'),
                name=base_token.get('name'),
                address=base_token.get('address', ''),
                price=demo_price,
                market_cap=demo_market_cap,
                volume_24h=real_volume * random.uniform(0.5, 1.5),
                price_change_24h=float(pair_data.get('priceChange', {}).get('h24', 0)),
                price_change_7d=float(pair_data.get('priceChange', {}).get('h7', 0)),
                liquidity=real_liquidity,
                holders=random.randint(50, 1000),
                fresh_holders_1d=random.randint(5, 50),
                fresh_holders_7d=random.randint(20, 200),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                # Oikeat tiedot
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_liquidity,
                dex=pair_data.get('dexId', 'unknown'),
                pair_address=pair_data.get('pairAddress', '')
            )
        except Exception as e:
            logger.debug(f"Virhe DexScreener parsin käsittelyssä: {e}")
            return None
    
    def _parse_birdeye_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii Birdeye token datan HybridToken:ksi"""
        try:
            # Oikeat markkina tiedot
            real_price = float(token_data.get('price', 0))
            real_volume = float(token_data.get('v24hUSD', 0))
            real_liquidity = float(token_data.get('liquidity', 0))
            
            # Demo tiedot
            age_minutes = random.randint(1, 5)
            demo_price = real_price * random.uniform(0.8, 1.2)
            demo_market_cap = real_liquidity * random.uniform(0.5, 2.0)
            
            # Skip tokens without proper symbol or name
            if not token_data.get('symbol') or not token_data.get('name'):
                return None
            
            return HybridToken(
                symbol=token_data.get('symbol'),
                name=token_data.get('name'),
                address=token_data.get('address', ''),
                price=demo_price,
                market_cap=demo_market_cap,
                volume_24h=real_volume * random.uniform(0.5, 1.5),
                price_change_24h=float(token_data.get('priceChange24h', 0)),
                price_change_7d=float(token_data.get('priceChange7d', 0)),
                liquidity=real_liquidity,
                holders=random.randint(50, 1000),
                fresh_holders_1d=random.randint(5, 50),
                fresh_holders_7d=random.randint(20, 200),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                # Oikeat tiedot
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_liquidity,
                dex='birdeye',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"Virhe Birdeye token parsin käsittelyssä: {e}")
            return None
    
    def _parse_moralis_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii Moralis token datan HybridToken:ksi"""
        try:
            # Moralis SOL token metadata
            symbol = token_data.get('symbol', 'SOL')
            name = token_data.get('name', 'Solana')
            address = 'So11111111111111111111111111111111111111112'  # SOL token address
            
            # Mock tiedot koska Moralis ei palauta hintoja
            real_price = random.uniform(0.001, 10.0)
            real_volume = random.uniform(1000, 1000000)
            real_liquidity = random.uniform(10000, 10000000)
            
            age_minutes = random.randint(1, 60)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                address=address,
                price=real_price,
                market_cap=real_liquidity * random.uniform(0.5, 2.0),
                volume_24h=real_volume,
                price_change_24h=random.uniform(-50, 200),
                price_change_7d=random.uniform(-80, 500),
                liquidity=real_liquidity,
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_liquidity,
                dex='moralis',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"Virhe Moralis token parsin käsittelyssä: {e}")
            return None
    
    def _parse_coingecko_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii CoinGecko token datan HybridToken:ksi"""
        try:
            # Oikeat markkina tiedot
            real_price = float(token_data.get('current_price', 0))
            real_volume = float(token_data.get('total_volume', 0))
            real_market_cap = float(token_data.get('market_cap', 0))
            
            # Laske ikä (mock data koska CoinGecko ei palauta tätä)
            age_minutes = random.randint(1, 60)
            
            # Laske skorit
            social_score = min(0.9, max(0.1, real_volume / 1000000))
            technical_score = min(0.9, max(0.1, real_market_cap / 1000000000))
            momentum_score = min(0.9, max(0.1, abs(float(token_data.get('price_change_percentage_24h', 0))) / 100))
            risk_score = max(0.1, min(0.9, 1 - (real_market_cap / 1000000000)))
            
            # Skip tokens without proper symbol or name
            if not token_data.get('symbol') or not token_data.get('name'):
                return None
            
            return HybridToken(
                symbol=token_data.get('symbol').upper(),
                name=token_data.get('name'),
                address=token_data.get('id', ''),
                price=real_price,
                market_cap=real_market_cap,
                volume_24h=real_volume,
                price_change_24h=float(token_data.get('price_change_percentage_24h', 0)),
                price_change_7d=float(token_data.get('price_change_percentage_7d_in_currency', 0)),
                liquidity=real_volume * 0.1,  # Arvio
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=age_minutes,
                social_score=social_score,
                technical_score=technical_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                timestamp=datetime.now().isoformat(),
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_volume * 0.1,
                dex='coingecko',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"Virhe CoinGecko token parsin käsittelyssä: {e}")
            return None
    
    def _parse_jupiter_token_new(self, token_info: Dict) -> Optional[HybridToken]:
        """Parsii Jupiter token datan uudesta API:sta"""
        try:
            symbol = token_info.get('symbol', '')
            name = token_info.get('name', '')
            address = token_info.get('address', '')
            
            # Generoi mock data uusille tokeneille
            price = random.uniform(0.001, 100.0)
            market_cap = random.uniform(1000000, 1000000000)
            volume_24h = random.uniform(100000, 10000000)
            price_change_24h = random.uniform(-20, 50)
            age_minutes = random.randint(1, 5)  # Ultra-fresh
            holders = random.randint(100, 10000)
            liquidity = random.uniform(50000, 500000)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_24h=price_change_24h,
                age_minutes=age_minutes,
                holders=holders,
                liquidity=liquidity,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.9),
                risk_score=random.uniform(0.0, 0.3),
                momentum_score=random.uniform(0.2, 0.8),
                address=address,
                price_change_7d=random.uniform(-20, 50),
                fresh_holders_1d=random.randint(5, 20),
                fresh_holders_7d=random.randint(15, 50),
                timestamp=int(time.time()),
                real_price=price,
                real_volume=volume_24h,
                real_liquidity=liquidity,
                dex="Jupiter",
                pair_address=address
            )
        except Exception as e:
            logger.debug(f"Jupiter token parsing virhe: {e}")
            return None
    
    def _parse_jupiter_token(self, address: str, token_info: Dict) -> Optional[HybridToken]:
        """Parsii Jupiter token datan HybridToken:ksi"""
        try:
            # Jupiter token tiedot
            symbol = token_info.get('symbol')
            name = token_info.get('name')
            
            # Skip tokens without proper symbol or name
            if not symbol or not name:
                return None
            
            # Mock tiedot koska Jupiter ei palauta hintoja
            real_price = random.uniform(0.001, 10.0)
            real_volume = random.uniform(1000, 1000000)
            real_liquidity = random.uniform(10000, 10000000)
            
            age_minutes = random.randint(1, 60)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                address=address,
                price=real_price,
                market_cap=real_liquidity * random.uniform(0.5, 2.0),
                volume_24h=real_volume,
                price_change_24h=random.uniform(-50, 200),
                price_change_7d=random.uniform(-80, 500),
                liquidity=real_liquidity,
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_liquidity,
                dex='jupiter',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"Virhe Jupiter token parsin käsittelyssä: {e}")
            return None
    
    def _parse_raydium_pair(self, pair_data: Dict) -> Optional[HybridToken]:
        """Parsii Raydium pair datan HybridToken:ksi"""
        try:
            base_mint = pair_data.get('baseMint', '')
            quote_mint = pair_data.get('quoteMint', '')
            base_symbol = pair_data.get('baseSymbol')
            quote_symbol = pair_data.get('quoteSymbol', 'USDC')
            
            # Skip if no base symbol
            if not base_symbol:
                return None
            
            # Ota base token jos se ei ole USDC/SOL
            if quote_symbol in ['USDC', 'USDT', 'SOL']:
                symbol = base_symbol
                name = pair_data.get('baseName')
                address = base_mint
            else:
                symbol = quote_symbol
                name = pair_data.get('quoteName')
                address = quote_mint
            
            # Skip tokens without proper name
            if not name:
                return None
            
            # Mock tiedot
            real_price = random.uniform(0.001, 10.0)
            real_volume = random.uniform(1000, 1000000)
            real_liquidity = float(pair_data.get('liquidity', 0))
            
            age_minutes = random.randint(1, 60)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                address=address,
                price=real_price,
                market_cap=real_liquidity * random.uniform(0.5, 2.0),
                volume_24h=real_volume,
                price_change_24h=random.uniform(-50, 200),
                price_change_7d=random.uniform(-80, 500),
                liquidity=real_liquidity,
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_liquidity,
                dex='raydium',
                pair_address=pair_data.get('id', '')
            )
        except Exception as e:
            logger.debug(f"Virhe Raydium pair parsin käsittelyssä: {e}")
            return None
    
    def _parse_coinpaprika_token(self, token_data: Dict) -> Optional[HybridToken]:
        """Parsii CoinPaprika token datan HybridToken:ksi"""
        try:
            # CoinPaprika token tiedot
            symbol = token_data.get('symbol')
            name = token_data.get('name')
            
            # Skip tokens without proper symbol or name
            if not symbol or not name:
                return None
            address = token_data.get('id', '')
            
            # Mock tiedot
            real_price = random.uniform(0.001, 10.0)
            real_volume = random.uniform(1000, 1000000)
            real_market_cap = random.uniform(100000, 1000000000)
            
            age_minutes = random.randint(1, 60)
            
            return HybridToken(
                symbol=symbol,
                name=name,
                address=address,
                price=real_price,
                market_cap=real_market_cap,
                volume_24h=real_volume,
                price_change_24h=random.uniform(-50, 200),
                price_change_7d=random.uniform(-80, 500),
                liquidity=real_volume * 0.1,
                holders=random.randint(100, 10000),
                fresh_holders_1d=random.randint(10, 100),
                fresh_holders_7d=random.randint(50, 500),
                age_minutes=age_minutes,
                social_score=random.uniform(0.3, 0.9),
                technical_score=random.uniform(0.4, 0.8),
                momentum_score=random.uniform(0.2, 0.9),
                risk_score=random.uniform(0.1, 0.7),
                timestamp=datetime.now().isoformat(),
                real_price=real_price,
                real_volume=real_volume,
                real_liquidity=real_volume * 0.1,
                dex='coinpaprika',
                pair_address=''
            )
        except Exception as e:
            logger.debug(f"Virhe CoinPaprika token parsin käsittelyssä: {e}")
            return None


class HybridTradingBot:
    """Hybrid Trading Bot - Oikeat tokenit, Demo valuutta"""

    def __init__(self, telegram=None, offline_mode: bool | None = None):
        offline_env = (os.getenv("HYBRID_BOT_OFFLINE") or "").strip().lower()
        self.offline_mode = bool(offline_mode if offline_mode is not None else offline_env in {"1", "true", "yes", "on"})
        self.portfolio = {
            'cash': 10000.0,  # Demo valuutta
            'positions': {},
            'total_value': 10000.0,
            'total_pnl': 0.0,
            'trades_count': 0,
            'win_rate': 0.0
        }
        
        # Trading parametrit
        self.max_positions = 15
        self.base_position_size = 100.0  # $100 per position
        self.take_profit = 0.10  # 10% (testausta varten)
        self.stop_loss = 0.05    # 5% (testausta varten)
        self.max_age_minutes = 5
        
        # Riskinhallinta parametrit
        self.max_portfolio_risk = 0.20  # 20% max portfolio risk
        self.volatility_multiplier = 1.0
        self.correlation_threshold = 0.7  # Max correlation between positions
        
        # Telegram bot (injektoitu tai luotu)
        self.telegram = telegram
        self.telegram_bot = telegram or TelegramBot()

        # API health seuranta
        self.api_health = {
            'coinmarketcap': False,
            'dexscreener': False,
            'cryptocompare': False,
            'pumpportal': False,
        }
        if self.offline_mode:
            for key in self.api_health:
                self.api_health[key] = True

        # Telegram cooldown ja backoff
        import time
        self.telegram_muted_until = 0.0
        # Hae cooldown konffista, fallback 900
        try:
            cfg = self._cfg or load_config()
            self._telegram_cooldown_sec = int(getattr(getattr(cfg,"telegram",None),"cooldown_seconds", 900))
        except Exception:
            self._telegram_cooldown_sec = 900

        # (valinnainen) viive backoffille
        self._telegram_backoff_sec = 1.0  # kasvaa virheissä max 30s
        
        # Per-mint cooldown Telegram ilmoituksille
        self._mint_cooldown: dict[str, float] = {}
        config = load_config()
        self._mint_cooldown_sec: int = config.telegram.mint_cooldown_seconds if hasattr(config, 'telegram') else 1800
        
        # Hot candidates historia
        from collections import deque
        self.hot_candidates_history = getattr(self, 'hot_candidates_history', deque(maxlen=1000))
        self.recent_hot_candidates = getattr(self, 'recent_hot_candidates', deque(maxlen=100))
        self.hot_candidate_count_history = deque(maxlen=200)
        self.cycle_durations = []
        self.daily_pnl_history = []
        self.max_drawdown_today = 0.0
        self.live_trading_enabled = False

        # Telegram viestien dedupe
        self._last_summary_signature = None
        self._last_hot_candidate_signature = None

        # DiscoveryEngine - alustetaan myöhemmin _ensure_discovery_started:ssa
        self._de_started = False
        self.discovery_engine = None
        self._cfg = None  # cachetaan config
        
        # Trading client
        self._trade_client = None
        self._trade_cooldown_sec = 1800
        self._last_trade_ts_by_mint = {}
        self._trade_lock: Optional[asyncio.Lock] = None
        self._sniper_sell_tasks: Dict[str, asyncio.Task] = {}
        self._sniper_seen_mints: Set[str] = set()
        self._sniper_first_seen: Dict[str, float] = {}
        self._sniper_positions: Dict[str, Dict[str, Any]] = {}
        self._sniper_candidates: Dict[str, Any] = {}
        self._sniper_attempt_log: Dict[str, float] = {}
        self._ws_trade_metrics: Dict[str, Dict[str, Any]] = {}

        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0
        }
        
        # Burn-in testing ja live trading gate
        self.hot_candidates_history = deque(maxlen=1000)  # [(ts, mint, score)]
        self.recent_hot_candidates = deque(maxlen=100)    # pelkkä mint- FIFO
        self._last_source_ok = {}                         # esim. {"pumpportal": True}

    def _can_send_telegram(self) -> bool:
        import time
        return time.time() >= float(getattr(self,"telegram_muted_until",0.0) or 0.0)

    def _mute_telegram(self, seconds: int | float):
        import time
        self.telegram_muted_until = time.time() + float(seconds)

    async def _safe_send_telegram(self, text: str):
        """
        Lähettää viestin turvallisesti: cooldown-check, try/except, virheissä backoff.
        """
        if not getattr(self, "telegram", None):
            return
        if not self._can_send_telegram():
            return
        try:
            await self.telegram.send_message(text)
            # onnistui → palauta backoff minimiin
            self._telegram_backoff_sec = 1.0
        except Exception as e:
            # Jos 409/429 → backoff ja mute hetkeksi
            msg = str(e)
            if "409" in msg or "429" in msg or "Too Many" in msg or "Conflict" in msg:
                self._mute_telegram(min(30.0, max(1.0, self._telegram_backoff_sec)))
                self._telegram_backoff_sec = min(30.0, self._telegram_backoff_sec * 2.0)
            # Lokita mutta älä kaada sykliä
            import logging
            logging.getLogger(__name__).warning(f"Telegram send failed: {e}")
    
    async def send_shutdown_notice(self, reason: str):
        try:
            await self._safe_send_telegram(f"🛑 Bot sammutetaan siististi ({reason})…")
            await asyncio.sleep(0.3)  # anna verkolle hetki
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Shutdown telegram failed: {e}")
    
    async def _ensure_discovery_started(self):
        """Käynnistä DiscoveryEngine vain kerran per prosessi."""
        if self.offline_mode:
            if not self._de_started:
                self.discovery_engine = None
                self._de_started = True
                logger.info("🧪 Offline mode: DiscoveryEngine ohitetaan")
            return

        if self._de_started and self.discovery_engine is not None:
            return

        cfg = self._cfg or load_config()
        self._cfg = cfg

        # Rakenna lähteet configista
        sources = []
        try:
            if cfg.discovery.sources.raydium:
                from sources.raydium_newpools import RaydiumNewPoolsSource
                # Käytä mock WS clientia jos ei ole oikeaa
                sources.append(RaydiumNewPoolsSource(ws_client=None))
                logger.info("✅ Raydium source lisätty")
        except Exception as e:
            logger.warning(f"Raydium-newpools ohitetaan: {e}")

        try:
            if cfg.discovery.sources.pumpfun:
                # PumpPortal HTTP source
                try:
                    from sources.pumpportal_newtokens import PumpPortalNewTokensSource
                    pp = (cfg.io.get("pump_portal") if isinstance(cfg.io, dict) else getattr(cfg.io,"pump_portal",{})) or {}
                    base_url = pp.get("base_url") or "https://pumpportal.fun"
                    poll = float(pp.get("poll_interval_sec") or 2.0)
                    sources.append(PumpPortalNewTokensSource(base_url=base_url, poll_interval=poll))
                    logger.info("✅ PumpPortal HTTP source lisätty: %s", base_url)
                except Exception as e:
                    logger.warning("PumpPortal HTTP source ohitetaan: %s", e)

                # WS new-token source
                if cfg.discovery.sources.pumpportal_ws:
                    try:
                        from sources.pumpportal_ws_newtokens import PumpPortalWSNewTokensSource
                        sources.append(PumpPortalWSNewTokensSource(
                            on_new_token=self._on_new_token_from_ws,
                            on_trade=self._on_trade_from_ws,
                        ))
                        logger.info("✅ PumpPortal WS new-token source lisätty")
                    except Exception as e:
                        logger.warning("PumpPortal WS new-token source ohitetaan: %s", e)
        except Exception as e:
            logger.warning(f"PumpPortal-newtokens ohitetaan: {e}")

        # Birdeye WebSocket source for new listings
        if cfg.discovery.sources.birdeye_ws:
            try:
                from sources.birdeye_ws_newlistings import BirdeyeWSNewListingsSource
                birdeye = (cfg.io.get("birdeye") if isinstance(cfg.io, dict) else getattr(cfg.io,"birdeye",{})) or {}
                ws_url = birdeye.get("ws_url") or "wss://public-api.birdeye.so/socket"
                api_key = birdeye.get("api_key")
                sources.append(BirdeyeWSNewListingsSource(ws_url=ws_url, api_key=api_key))
                logger.info("✅ Birdeye WS new-listings source lisätty: %s", ws_url)
            except Exception as e:
                logger.warning("Birdeye WS new-listings source ohitetaan: %s", e)

        # Helius logs source for real-time token creation monitoring
        if cfg.discovery.sources.helius_logs:
            try:
                from sources.helius_logs_newtokens import HeliusLogsNewTokensSource
                rpc_cfg = (cfg.io.get("rpc") if isinstance(cfg.io, dict) else getattr(cfg.io,"rpc",{})) or {}
                ws_url = rpc_cfg.get("ws_url") or "wss://mainnet.helius-rpc.com/?api-key=your-key"
                programs = getattr(cfg.discovery, "helius_programs", ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"])
                sources.append(HeliusLogsNewTokensSource(ws_url=ws_url, programs=programs))
                logger.info("✅ Helius logs source lisätty: %s (programs: %d)", ws_url[:50] + "...", len(programs))
            except Exception as e:
                logger.warning("Helius logs source ohitetaan: %s", e)

        if not sources:
            logger.warning("DiscoveryEngine käynnistyy ilman lähteitä! (0 sourcea) -> ei uutuuksia.")

        # RPC pool
        endpoints = getattr(cfg.io, "rpc_endpoints", None) if hasattr(cfg.io, 'rpc_endpoints') else None
        if not endpoints:
            logger.warning("RPC endpoint -listaa ei löydy configista; käytetään oletusta.")
            endpoints = ["https://api.mainnet-beta.solana.com"]

        # Käytä yksinkertaista RPC clientia
        from rpc_interfaces import SolanaRPC
        rpc = SolanaRPC(endpoint=endpoints[0])

        # Alusta DiscoveryEngine
        from discovery_engine import DiscoveryEngine
        self.discovery_engine = DiscoveryEngine(
            rpc_endpoint=endpoints[0],
            market_sources=sources,
            min_liq_usd=cfg.discovery.min_liq_usd,
            rpc_client=rpc
        )
        await self.discovery_engine.start()
        self._de_started = True
        logger.info(f"✅ DiscoveryEngine käynnissä: {len(sources)} lähdettä")

    def _age_minutes(self, cand) -> Optional[float]:
        """Laske ikä minuuteissa on-chain ts:stä (first_pool_ts / first_trade_ts / first_seen_ts). Tukee TokenCandidatea ja dictiä."""
        try:
            extra = getattr(cand, "extra", None) or (cand.get("extra") if isinstance(cand, dict) else {}) or {}
            ts = (
                extra.get("first_pool_ts")
                or extra.get("first_trade_ts")
                or getattr(cand, "first_seen_ts", None)
                or (cand.get("first_seen_ts") if isinstance(cand, dict) else None)
            )
            if not ts:
                return None  # ⬅️ tärkein muutos: EI 0.0
            return max(0.0, (time.time() - float(ts)) / 60.0)
        except Exception as e:
            logger.warning(f"_age_minutes virhe: {e}; palautetaan None")
            return None

    def _is_source_healthy(self, source: str) -> bool:
        """Tarkista lähteen terveys (turvallinen oletus=True)"""
        try:
            from metrics import metrics
            # jos mittari löytyy, lue se (valinnainen):
            # return bool(metrics and metrics.hot_candidates_gauge._value.get() >= 0)  # placeholder
        except Exception:
            pass
        return self._last_source_ok.get(source, True)

    def _log_evt(self, evt: str, **kv):
        """Apu-loggeri koneystävällisiin eventteihin"""
        try:
            payload = {"evt": evt, **kv}
            logger.info(json.dumps(payload, ensure_ascii=False))
        except Exception:
            logger.info(f"{{\"evt\":\"{evt}\"}}")

    async def _check_api_health(self):
        """Tarkista API health status"""
        if self.offline_mode:
            logger.info("🧪 Offline mode: API health-check skipattu")
            return {"offline": True}
        cfg = self._cfg or load_config()
        io = getattr(cfg, "io", {}) if hasattr(cfg, 'io') else {}
        
        # Määritä health-URLit konfigista tai käytä turvallisia oletuksia
        urls = {
            "cmc": "https://pro-api.coinmarketcap.com/v1/key/info",
            "birdeye": "https://public-api.birdeye.so/defi/health",
            "pumpportal": "http://localhost:9999/metrics"  # oletus
        }
        
        # Yritä lukea konfigista
        if hasattr(io, 'pump_portal') and hasattr(io.pump_portal, 'base_url'):
            urls["pumpportal"] = io.pump_portal.base_url + "/metrics"
        
        statuses = {}
        timeout = getattr(io, "rpc_timeout_sec", 3.0) if hasattr(io, 'rpc_timeout_sec') else 3.0
        
        try:
            conn = aiohttp.TCPConnector(limit=10)
            async with aiohttp.ClientSession(connector=conn) as s:
                for name, url in urls.items():
                    if not url:
                        continue
                    try:
                        async with s.get(url, timeout=timeout) as r:
                            # luetaan vähän, ettei jätetä sokettia roikkumaan
                            await r.content.readany()
                            statuses[name] = r.status
                    except Exception:
                        statuses[name] = 599  # custom "network error"
        except Exception as e:
            logger.warning(f"API health-check epäonnistui: {e}")
            return

        # Lokitus
        if statuses:
            line = ", ".join(f"{k}={'✅' if 200<=v<300 else '❌'}({v})" for k,v in statuses.items())
            logger.info(f"🔑 API health: {line}")

    async def run_analysis_cycle(self) -> Dict[str, Any]:
        """Suorittaa yhden analyysi syklin"""
        logger.info("🔄 Aloitetaan hybrid analyysi sykli...")
        
        # Varmista että DiscoveryEngine on käynnissä
        await self._ensure_discovery_started()
        
        # Tarkista API health
        await self._check_api_health()
        
        start_time = time.time()
        
        try:
            # Skannaa tokeneita (tai generoi mock-dataa offline-tilassa)
            async with HybridTokenScanner(telegram=self.telegram_bot, offline_mode=self.offline_mode) as scanner:
                tokens = await scanner.scan_real_tokens()

            # Hae DiscoveryEngine hot candidates
            hot_candidates = []
            if self.discovery_engine:
                try:
                    hot_candidates = self.discovery_engine.best_candidates(k=5)  # Käytä configin arvoa
                    logger.info(f"🔥 DiscoveryEngine: Löydettiin {len(hot_candidates)} hot candidate:ja")
                except Exception as e:
                    logger.warning(f"DiscoveryEngine virhe: {e}")
            elif self.offline_mode and tokens:
                hot_candidates = self._select_offline_hot_candidates(tokens)
                logger.info("🧪 Offline mode: generoitu %d mock hot candidatea", len(hot_candidates))

            current_hot_mints = tuple(sorted(
                mint for mint in (
                    (c.get("mint") if isinstance(c, dict) else getattr(c, "mint", None))
                    for c in hot_candidates
                ) if mint
            ))
            if not current_hot_mints:
                self._last_hot_candidate_signature = None

            if not tokens and not hot_candidates:
                logger.warning("⚠️ Ei löytynyt tokeneita tällä skannauksella")
                return {
                    'tokens_found': 0, 
                    'signals_generated': 0, 
                    'trades_executed': 0,
                    'hot_candidates': []
                }
            
            # Analysoi tokenit
            analyzed_tokens = []
            for token in tokens:
                try:
                    analysis = self._analyze_token(token)
                    analyzed_tokens.append(analysis)
                except Exception as e:
                    logger.error(f"Virhe tokenin {token.symbol} analyysissä: {e}")
                    continue
            
            # Generoi trading signaalit
            signals = self._generate_trading_signals(analyzed_tokens)
            
            # Suorita kaupat
            trades_executed = await self._execute_trades(signals)
            
            # Päivitä performance metriikat
            await self._update_performance_metrics(scanner)
            
            # Laske riskinhallinta metriikat
            portfolio_heat = self._calculate_portfolio_heat()
            
            # Tallenna analyysi
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'tokens_scanned': len(tokens),
                'tokens_analyzed': len(analyzed_tokens),
                'signals_generated': len(signals),
                'trades_executed': trades_executed,
                'hot_candidates': [self._convert_token_candidate_to_dict(candidate) for candidate in hot_candidates],
                'accepted_candidates_count': len(hot_candidates),  # DE:n parhaat tälle sykille
                'portfolio_value': self.portfolio['total_value'],
                'portfolio_pnl': self.portfolio['total_pnl'],
                'active_positions': len(self.portfolio['positions']),
                'performance_metrics': self.performance_metrics.copy(),
                'risk_metrics': {
                    'portfolio_heat': portfolio_heat,
                    'max_portfolio_risk': self.max_portfolio_risk,
                    'correlation_threshold': self.correlation_threshold,
                    'dynamic_position_sizing': True
                },
                'tokens': [asdict(token) for token in analyzed_tokens],
                'positions': self.portfolio['positions'].copy(),  # Lisää position tiedot
                'signals': [{'type': s['type'], 'symbol': s['token'].symbol, 'reasoning': s['reasoning'], 'confidence': s['confidence']} for s in signals]
            }
            
            self._save_analysis_to_file(analysis_result)
            
            logger.info(f"✅ Hybrid analyysi sykli valmis: {len(tokens)} tokenia, {len(signals)} signaalia, {len(hot_candidates)} hot candidates")
            
            # TopScore-snapshot syklin loppuun
            try:
                # Hae DE:n nähdyt kandidaatit turvallisesti
                seen = list(getattr(self.discovery_engine, "processed_candidates", {}).values())
                top = sorted(seen, key=lambda x: getattr(x, "overall_score", 0.0), reverse=True)[:10]
                for c in top:
                    buys  = int(getattr(c, "buys_5m", 0) or 0)
                    sells = int(getattr(c, "sells_5m", 0) or 0)
                    total = max(1, buys + sells)
                    buy_ratio = buys / total
                    uniq  = int(getattr(c, "unique_buyers_5m", 0) or 0)
                    liq   = float(getattr(c, "liquidity_usd", 0.0) or 0.0)
                    top10 = getattr(c, "top10_holder_share", None)
                    age_min = None
                    extra = getattr(c, "extra", {}) or {}
                    ts = extra.get("first_pool_ts") or extra.get("first_trade_ts") or getattr(c, "first_seen_ts", None)
                    if ts: age_min = max(0.0, (time.time() - float(ts)) / 60.0)
                    logger.info(
                        "TopScore mint=%s score=%.2f liq=$%.0f buyers=%d buy_ratio=%.2f top10=%s fresh=%s age=%s src=%s",
                        (getattr(c,"mint",None)[:4]+"…"+getattr(c,"mint",None)[-4:]) if getattr(c,"mint",None) else "-",
                        float(getattr(c,"last_score",0.0) or 0.0),
                        liq, uniq, buy_ratio,
                        ("%.2f" % top10) if top10 is not None else "n/a",
                        str(self.discovery_engine._is_fresh(c)) if hasattr(self.discovery_engine, "_is_fresh") else "n/a",
                        (f"{age_min:.1f}m" if age_min is not None else "n/a"),
                        (extra.get("source") if isinstance(extra, dict) else None),
                    )
            except Exception as e:
                logger.warning(f"TopScore-snapshot epäonnistui: {e}")
            
            # Trading logic - signaali→kauppa polku
            try:
                cfg = self._cfg or load_config()
                hc = []
                if isinstance(analysis_result, dict):
                    hc = analysis_result.get("hot_candidates") or []
                if not hc:
                    pass  # ei hotteja, ohita
                else:
                    # Poimi top-1 (voi laajentaa myöhemmin)
                    c = hc[0]
                    mint = c.get("mint") if isinstance(c, dict) else getattr(c, "mint", None)
                    
                    # Turvallisesti nosta score ja base_min numerisiksi
                    import math
                    score_val = result_score = 0.0
                    if isinstance(c, dict):
                        score_val = float(c.get("score") or 0.0)
                    else:
                        score_val = float(getattr(c, "last_score", 0.0) or 0.0)
                    if math.isnan(score_val): score_val = 0.0

                    # baseline from config (discovery.score_threshold) tai trading.min_score_for_trade
                    base_min = None
                    try:
                        cfg = self._cfg or load_config()
                        base_min = getattr(getattr(cfg,"trading",None), "min_score_for_trade", None)
                        if base_min is None:
                            base_min = getattr(getattr(cfg,"discovery",None), "score_threshold", 0.55)
                        base_min = float(base_min or 0.55)
                    except Exception:
                        base_min = 0.55

                    # Ennen vertailua varmista että molemmat floatteja
                    if mint and float(score_val) >= float(base_min) and self._trade_allowed(mint):
                        if not cfg.trading.enabled:
                            # Trading kokonaan pois; logaa vain
                            logger.info(f"[TRADE_DISABLED] mint={mint} score={score_val:.2f}")
                        elif cfg.trading.paper_trade:
                            # PAPER TRADE: ei oikeaa osto-operaatiota
                            logger.info(f"[PAPER] BUY mint={mint} amount_sol={cfg.trading.default_amount_sol} score={score_val:.2f}")
                            try:
                                from metrics import metrics
                                if metrics: metrics.trades_sent.labels(mode="paper").inc()
                            except Exception:
                                pass
                            self._mark_traded(mint)
                        else:
                            # LIVE TRADE
                            await self._ensure_trading_client()
                            if not self._trade_client:
                                logger.warning("Trading enabled, mutta trade client puuttuu – ohitetaan.")
                            else:
                                sig = await self._trade_client.buy(
                                    mint=mint,
                                    amount_sol=cfg.trading.default_amount_sol,
                                    slippage=cfg.trading.slippage,
                                    priority_fee=cfg.trading.priority_fee,
                                    pool=cfg.trading.pool,
                                )
                                logger.info(f"BUY OK mint={mint} sig={sig}")
                                if getattr(self, "telegram", None):
                                    await self._safe_send_telegram(
                                        f"✅ BUY\n• mint: `{mint}`\n• amount: {cfg.trading.default_amount_sol} SOL\n• sig: `{sig}`"
                                    )
                                try:
                                    from metrics import metrics
                                    if metrics: metrics.trades_sent.labels(mode="live").inc()
                                except Exception:
                                    pass
                                self._mark_traded(mint)
                    else:
                        logger.info(f"Trade gates not met mint={mint} score={score_val:.2f} min={base_min}")
            except Exception as e:
                logger.error(f"Trade path error: {e}")
                try:
                    from metrics import metrics
                    if metrics: metrics.trades_failed.labels(stage="trade_path").inc()
                except Exception:
                    pass

            # Lähetä Telegram raportti
            tokens_count = (
                analysis_result.get("accepted_candidates_count")  # DE:n hyväksymät tälle sykille
                or len(analysis_result.get("hot_candidates", []) or [])
                or analysis_result.get("tokens_scanned", 0)       # fallback
            )
            
            message = (
                f"📊 *Hybrid Bot Raportti:*\n"
                f"🔍 Tokeneita: {tokens_count}\n"          # <-- tämä oli ennen 0, koska katsoi väärää listaa
                f"📡 Signaaleja: {len(signals)}\n"
                f"💼 Kauppoja: {trades_executed}\n"
                f"🔥 Hot Candidates: {len(hot_candidates)}\n"
                f"💰 Portfolio: ${self.portfolio['total_value']:.2f} (+${self.portfolio['total_pnl']:.2f})\n"
                f"📈 Positioita: {len(self.portfolio['positions'])}"
            )
            summary_signature = (
                tokens_count,
                len(signals),
                trades_executed,
                len(hot_candidates),
                current_hot_mints,
                round(self.portfolio['total_value'], 2),
                round(self.portfolio['total_pnl'], 2),
                len(self.portfolio['positions'])
            )
            if self._last_summary_signature == summary_signature:
                logger.info("📵 Telegram yhteenveto ohitetaan – ei muutoksia.")
            else:
                await self.telegram_bot.send_message(message)
                try:
                    from metrics import metrics
                    if metrics:
                        metrics.telegram_sent.inc()
                except Exception:
                    pass
                self._last_summary_signature = summary_signature

            # Päivitä hot candidates historiat turvallisesti
            try:
                for c in hot_candidates:
                    mint = getattr(c, "mint", None) or (c.get("mint") if isinstance(c, dict) else None)
                    score = getattr(c, "last_score", None) or (c.get("score") if isinstance(c, dict) else None)
                    self.hot_candidates_history.append((time.time(), mint, score))
                    if mint: self.recent_hot_candidates.append(mint)
            except Exception as e:
                logger.error(f"Virhe päivittäessä burn-in metriikoita: {e}")
            
            # Lähetä hot candidates Telegram viesti jos löytyi (jos ei hiljennetty)
            if hot_candidates and not self.is_telegram_muted():
                await self._send_hot_candidates_telegram(hot_candidates)
                
                # Kirjaa shadow trades
                try:
                    from shadow_trading_logger import shadow_logger
                    for candidate in hot_candidates:
                        shadow_logger.log_hot_candidate(candidate)
                except ImportError:
                    pass  # Shadow logger ei ole saatavilla
            
            # Metrics
            cycle_duration = time.time() - start_time
            try:
                from metrics import metrics
                if metrics:
                    metrics.cycle_duration.observe(cycle_duration)
                    metrics.hot_candidates_gauge.set(len(hot_candidates))
            except Exception:
                pass
            
            # Burn-in seuranta
            self._update_burn_in_metrics(cycle_duration, len(hot_candidates))
            
            # Live-kauppa gate tarkistus
            self._check_live_trading_gate()
            
            # Päivitä laatupaneeli
            self._update_quality_panel(len(hot_candidates))
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Virhe hybrid analyysi syklissä: {e}")
            return {'error': str(e)}
    
    async def stop(self):
        """Pysäytä bot siististi - sammuta DiscoveryEngine"""
        logger.info("🛑 Pysäytetään HybridTradingBot...")
        
        if hasattr(self, "discovery_engine") and self.discovery_engine:
            try:
                await self.discovery_engine.stop()
                await self.discovery_engine.wait_closed()
                logger.info("✅ DiscoveryEngine pysäytetty siististi")
            except Exception as e:
                logger.warning(f"⚠️ Virhe pysäytettäessä DiscoveryEngine: {e}")
        
        logger.info("✅ HybridTradingBot pysäytetty")
    
    def _convert_token_candidate_to_dict(self, candidate: TokenCandidate) -> Dict[str, Any]:
        """Muunna TokenCandidate dictiksi"""
        return {
            'mint': candidate.mint,
            'symbol': candidate.symbol,
            'name': candidate.name,
            'decimals': candidate.decimals,
            'liquidity_usd': candidate.liquidity_usd,
            'top10_holder_share': candidate.top10_holder_share,
            'lp_locked': candidate.lp_locked,
            'lp_burned': candidate.lp_burned,
            'mint_authority_renounced': candidate.mint_authority_renounced,
            'freeze_authority_renounced': candidate.freeze_authority_renounced,
            'age_minutes': candidate.age_minutes,
            'unique_buyers_5m': candidate.unique_buyers_5m,
            'buy_sell_ratio': candidate.buy_sell_ratio,
            'novelty_score': candidate.novelty_score,
            'liquidity_score': candidate.liquidity_score,
            'distribution_score': candidate.distribution_score,
            'rug_risk_score': candidate.rug_risk_score,
            'overall_score': candidate.overall_score,
            'score': getattr(candidate, 'last_score', None) if getattr(candidate, 'last_score', None) is not None else candidate.overall_score,
            'source': candidate.source,
            'first_seen': candidate.first_seen.isoformat() if hasattr(candidate.first_seen, 'isoformat') else str(candidate.first_seen),
            'last_updated': candidate.last_updated.isoformat() if hasattr(candidate.last_updated, 'isoformat') else str(candidate.last_updated)
        }

    def _select_offline_hot_candidates(self, tokens: List[HybridToken]) -> List[Any]:
        """Muodosta DiscoveryEngine-tyyliset ehdokkaat mock-tokeneista"""
        try:
            from discovery_engine import TokenCandidate
        except Exception:
            logger.warning("Offline mode: TokenCandidate ei saatavilla, hot candidates skipataan")
            return []

        top = sorted(tokens, key=lambda t: (t.momentum_score + t.technical_score) - t.risk_score, reverse=True)[:3]
        hot: List[TokenCandidate] = []
        now_ts = time.time()
        for token in top:
            first_trade_ts = max(0.0, now_ts - float(token.age_minutes or 0) * 60.0)
            liquidity_norm = float(token.liquidity) if token.liquidity else 0.0
            overall_score = max(0.0, min(1.0, (token.momentum_score + token.technical_score + (1.0 - token.risk_score)) / 3.0))
            candidate = TokenCandidate(
                mint=token.address or token.pair_address,
                symbol=token.symbol,
                name=token.name,
                liquidity_usd=liquidity_norm,
                top10_holder_share=min(0.95, 0.25 + token.risk_score * 0.5),
                lp_locked=True,
                lp_burned=False,
                mint_authority_renounced=True,
                freeze_authority_renounced=True,
                age_minutes=float(token.age_minutes),
                unique_buyers_5m=max(3, int(token.momentum_score * 15)),
                buys_5m=max(5, int(token.momentum_score * 20)),
                sells_5m=max(1, int((1.0 - token.momentum_score) * 10)),
                buy_sell_ratio=max(0.1, 0.8 + token.momentum_score),
                price_usd=float(token.real_price),
                market_cap_usd=float(token.market_cap),
                volume_24h_usd=float(token.volume_24h),
                novelty_score=float(min(1.0, token.momentum_score)),
                liquidity_score=float(min(1.0, liquidity_norm / max(liquidity_norm, 1.0 + 50_000.0))),
                distribution_score=float(max(0.0, 1.0 - token.risk_score)),
                rug_risk_score=float(min(1.0, token.risk_score)),
                overall_score=overall_score,
                last_score=float(max(0.0, min(1.0, (token.momentum_score + token.technical_score) / 2.0))),
                source="offline_mock",
                extra={
                    "source": "offline_mock",
                    "first_trade_ts": first_trade_ts,
                    "trade_unique_buyers_30s": int(max(1, token.momentum_score * 10)),
                }
            )
            hot.append(candidate)
        return hot
    
    async def _send_hot_candidates_telegram(self, hot_candidates: List[TokenCandidate]) -> None:
        """Lähetä hot candidates Telegram viesti score breakdown:lla + per-mint cooldown + dedupe"""
        try:
            current_time = time.time()
            
            # Dedupe: poista saman syklin duplikaatit
            seen_mints = set()
            unique_candidates = []
            for candidate in hot_candidates:
                mint = getattr(candidate, 'mint', 'unknown')
                if mint not in seen_mints:
                    unique_candidates.append(candidate)
                    seen_mints.add(mint)
            
            # Cooldown: suodata mintit jotka ovat cooldown:issa
            filtered_candidates = []
            for candidate in unique_candidates:
                mint = getattr(candidate, 'mint', 'unknown')
                source_name = getattr(candidate, 'source', None) or ((getattr(candidate, 'extra', {}) or {}).get('source') if getattr(candidate, 'extra', None) else None)
                if source_name == 'pumpportal_ws':
                    metrics = self._ws_trade_metrics.get(mint)
                    if metrics:
                        self._apply_trade_metrics(candidate, metrics)
                    if not self._is_viable_ws_candidate(candidate):
                        continue
                if mint not in self._mint_cooldown or (current_time - self._mint_cooldown[mint]) >= self._mint_cooldown_sec:
                    filtered_candidates.append(candidate)
                    self._mint_cooldown[mint] = current_time
                else:
                    remaining = self._mint_cooldown_sec - (current_time - self._mint_cooldown[mint])
                    logger.info(f"Cooldown skip mint={mint[:8]}... remaining={remaining:.0f}s")
            
            if not filtered_candidates:
                logger.info("📱 Kaikki hot candidates cooldown:issa tai duplikaatteja, ei lähetetä Telegram viestiä")
                return

            signature = tuple(sorted(
                mint for mint in (
                    (c.get('mint') if isinstance(c, dict) else getattr(c, 'mint', None))
                    for c in filtered_candidates
                ) if mint
            ))
            if signature == self._last_hot_candidate_signature:
                logger.info("📵 Hot candidates Telegram viesti ohitetaan – ei uusia minttejä")
                return

            # Jos > 5 kandidattia, lähetä yhteenveto
            if len(filtered_candidates) > 5:
                message = f"🌱 *Uudet kuumat tokenit* ({len(filtered_candidates)} kpl)\n\n"
                message += "📊 *Yhteenveto:*\n"
                for i, candidate in enumerate(filtered_candidates[:5], 1):
                    final_score = getattr(candidate, 'overall_score', 0.0)
                    message += f"{i}) {candidate.symbol} — {final_score:.2f}\n"
                message += f"\n📋 Täydellinen lista: {len(filtered_candidates)} kandidattia\n"
                message += "🔗 Katso lokitiedostot yksityiskohtien saamiseksi"
            else:
                message = "🌱 *Uudet kuumat tokenit*\n\n"
                for i, candidate in enumerate(filtered_candidates, 1):
                    # Laske ikä minuutteina
                    age_min = self._age_minutes(candidate) if hasattr(self, '_age_minutes') else candidate.age_minutes
                    
                    # Score breakdown
                    novelty = getattr(candidate, 'novelty_score', 0.0)
                    buyers_5m = getattr(candidate, 'unique_buyers_5m', 0)
                    buy_ratio = getattr(candidate, 'buy_sell_ratio', 1.0)
                    liq_score = getattr(candidate, 'liquidity_score', 0.0)
                    dist_score = getattr(candidate, 'distribution_score', 0.0)
                    rug_risk = getattr(candidate, 'rug_risk_score', 0.0)
                    final_score = getattr(candidate, 'overall_score', 0.0)
                    
                    # Mint address (lyhennetty)
                    mint = getattr(candidate, 'mint', 'unknown')
                    mint_short = f"{mint[:4]}…{mint[-4:]}" if len(mint) > 8 else mint
                    
                    message += f"{i}) *{candidate.symbol}* — {final_score:.2f}\n"
                    message += f"   • age {age_min:.1f}m • buyers {buyers_5m} • buy-ratio {buy_ratio:.2f}\n"
                    message += f"   • liq ${candidate.liquidity_usd:.0f} • dist {dist_score:.2f} • rug_risk {rug_risk:.2f}\n"
                    message += f"   • mint: {mint_short}\n"
                    message += f"   • address: `{mint}`\n\n"

            await self.telegram_bot.send_message(message)
            try:
                from metrics import metrics
                if metrics:
                    metrics.telegram_sent.inc()
            except Exception:
                pass
            logger.info(f"✅ Hot candidates Telegram viesti lähetetty: {len(filtered_candidates)} tokenia (cooldown: {len(hot_candidates) - len(filtered_candidates)} skipattu)")
            self._last_hot_candidate_signature = signature

        except Exception as e:
            logger.error(f"Virhe lähettäessä hot candidates Telegram viestiä: {e}")
    
    async def handle_stats_command(self) -> None:
        """Käsittele /stats-komento"""
        try:
            # Kerää stats data
            stats_data = {
                'min_score_effective': 0.0,
                'source_health': {},
                'hot_candidates': []
            }
            
            # Min score effective
            if self.discovery_engine and hasattr(self.discovery_engine, '_calculate_dynamic_score_threshold'):
                stats_data['min_score_effective'] = self.discovery_engine._calculate_dynamic_score_threshold()
            
            # Source health
            stats_data['source_health'] = {
                'pumpportal': self._is_source_healthy('pumpportal'),
                'pumpfun': self._is_source_healthy('pumpfun')
            }
            
            # Recent hot candidates
            for candidate in self.recent_hot_candidates:
                sources = []
                if hasattr(candidate, 'extra') and candidate.extra:
                    sources = candidate.extra.get('seen_from', [])
                
                stats_data['hot_candidates'].append({
                    'symbol': getattr(candidate, 'symbol', 'unknown'),
                    'score': getattr(candidate, 'overall_score', 0.0),
                    'age_min': self._age_minutes(candidate) if hasattr(self, '_age_minutes') else 0.0,
                    'buyers_5m': getattr(candidate, 'unique_buyers_5m', 0),
                    'sources': sources
                })
            
            # Live trading status
            stats_data['live_trading_enabled'] = self.live_trading_enabled
            
            # Burn-in status
            current_time = time.time()
            if len(self.hot_candidate_count_history) > 0:
                total_hot = sum(count for _, count in self.hot_candidate_count_history)
                hours = max(1, (current_time - self.hot_candidate_count_history[0][0]) / 3600)
                hot_per_hour = total_hot / hours
            else:
                hot_per_hour = 0
            
            if len(self.cycle_durations) > 0:
                sorted_durations = sorted(self.cycle_durations)
                p95_index = int(0.95 * len(sorted_durations))
                p95_cycle = sorted_durations[p95_index] if p95_index < len(sorted_durations) else sorted_durations[-1]
            else:
                p95_cycle = 0
            
            spam_ratio = 0
            try:
                from metrics import metrics as global_metrics
                if global_metrics:
                    filtered_total = global_metrics.candidates_filtered._value._value
                    in_total = sum(global_metrics.candidates_in._metrics.values())
                    if in_total > 0:
                        spam_ratio = filtered_total / in_total
            except:
                pass
            
            stats_data['burn_in_status'] = {
                'hot_per_hour': hot_per_hour,
                'p95_cycle': p95_cycle,
                'spam_ratio': spam_ratio
            }
            
            # Lähetä stats viesti
            await self.telegram_bot.send_stats_message(stats_data)
            
        except Exception as e:
            logger.error(f"Virhe käsiteltäessä /stats-komentoa: {e}")
    
    def _update_burn_in_metrics(self, cycle_duration: float, hot_candidates_count: int):
        """Päivitä burn-in metriikat"""
        try:
            current_time = time.time()
            
            # Hot candidates per hour
            self.hot_candidate_count_history.append((current_time, hot_candidates_count))
            # Pidä vain viimeisen tunnin data
            self.hot_candidate_count_history = deque(
                [(ts, count) for ts, count in self.hot_candidate_count_history if current_time - ts <= 3600],
                maxlen=self.hot_candidate_count_history.maxlen,
            )
            
            # Cycle durations
            self.cycle_durations.append(cycle_duration)
            # Pidä vain viimeiset 100 sykliä
            if len(self.cycle_durations) > 100:
                self.cycle_durations = self.cycle_durations[-100:]
            
            # Laske metriikat
            try:
                from metrics import metrics
                if metrics:
                    # Hot candidates per hour
                    if len(self.hot_candidate_count_history) > 0:
                        total_hot = sum(count for _, count in self.hot_candidate_count_history)
                        hours = max(1, (current_time - self.hot_candidate_count_history[0][0]) / 3600)
                        hot_per_hour = total_hot / hours
                        metrics.hot_candidates_per_hour.set(hot_per_hour)
                    
                    # P95 cycle duration
                    if len(self.cycle_durations) > 0:
                        sorted_durations = sorted(self.cycle_durations)
                        p95_index = int(0.95 * len(sorted_durations))
                        p95_duration = sorted_durations[p95_index] if p95_index < len(sorted_durations) else sorted_durations[-1]
                        metrics.cycle_p95_duration.set(p95_duration)
                    
                    # Spam ratio (filtered/total)
                    try:
                        from metrics import metrics as global_metrics
                        if global_metrics:
                            filtered_total = global_metrics.candidates_filtered._value._value
                            in_total = sum(global_metrics.candidates_in._metrics.values())
                            if in_total > 0:
                                spam_ratio = filtered_total / in_total
                                metrics.spam_ratio.set(spam_ratio)
                    except:
                        pass
            except Exception:
                pass
            
            # Tarkista hyväksymiskriteerit
            self._check_burn_in_criteria()
            
        except Exception as e:
            logger.error(f"Virhe päivittäessä burn-in metriikoita: {e}")
    
    def _check_burn_in_criteria(self):
        """Tarkista burn-in hyväksymiskriteerit"""
        try:
            current_time = time.time()
            
            # Hot candidates per hour >= 2
            if len(self.hot_candidate_count_history) > 0:
                total_hot = sum(count for _, count in self.hot_candidate_count_history)
                hours = max(1, (current_time - self.hot_candidate_count_history[0][0]) / 3600)
                hot_per_hour = total_hot / hours
                
                if hot_per_hour < 2.0:
                    logger.warning(f"⚠️ Burn-in: Hot candidates/h = {hot_per_hour:.1f} < 2.0 (kriteeri ei täyty)")
                else:
                    logger.info(f"✅ Burn-in: Hot candidates/h = {hot_per_hour:.1f} >= 2.0 (kriteeri täyttyy)")
            
            # P95 cycle < 3s
            if len(self.cycle_durations) > 0:
                sorted_durations = sorted(self.cycle_durations)
                p95_index = int(0.95 * len(sorted_durations))
                p95_duration = sorted_durations[p95_index] if p95_index < len(sorted_durations) else sorted_durations[-1]
                
                if p95_duration > 3.0:
                    logger.warning(f"⚠️ Burn-in: P95 cycle = {p95_duration:.2f}s > 3.0s (kriteeri ei täyty)")
                else:
                    logger.info(f"✅ Burn-in: P95 cycle = {p95_duration:.2f}s <= 3.0s (kriteeri täyttyy)")
            
            # Spam ratio < 80%
            try:
                from metrics import metrics as global_metrics
                if global_metrics:
                    filtered_total = global_metrics.candidates_filtered._value._value
                    in_total = sum(global_metrics.candidates_in._metrics.values())
                    if in_total > 0:
                        spam_ratio = filtered_total / in_total
                        if spam_ratio > 0.8:
                            logger.warning(f"⚠️ Burn-in: Spam ratio = {spam_ratio:.1%} > 80% (kriteeri ei täyty)")
                        else:
                            logger.info(f"✅ Burn-in: Spam ratio = {spam_ratio:.1%} <= 80% (kriteeri täyttyy)")
            except:
                pass
                
        except Exception as e:
            logger.error(f"Virhe tarkistettaessa burn-in kriteereitä: {e}")
    
    def _check_live_trading_gate(self) -> bool:
        """Tarkista 'kahden miehen sääntö' live-kauppaan"""
        try:
            # Kriteerit live-kauppaan
            hot_candidates_ok = len(self.recent_hot_candidates) >= 2  # Vähintään 2 hot candidate
            
            # API health OK
            api_health_ok = all(self.api_health.values())
            
            # Source health OK
            source_health_ok = all(self._is_source_healthy(source) for source in ['pumpportal', 'pumpfun'])
            
            # Max drawdown today < limit (5%)
            drawdown_ok = self.max_drawdown_today < 0.05
            
            # Yhdistä kaikki kriteerit
            go_live = hot_candidates_ok and api_health_ok and source_health_ok and drawdown_ok
            
            if go_live and not self.live_trading_enabled:
                logger.info("🚀 Live-kauppa GATE: Kaikki kriteerit täyttyvät - live-kauppa ENABLED")
                self.live_trading_enabled = True
            elif not go_live and self.live_trading_enabled:
                logger.warning("⚠️ Live-kauppa GATE: Kriteerit eivät täyty - live-kauppa DISABLED")
                self.live_trading_enabled = False
            
            # Logita kriteerit
            logger.info(f"🔍 Live-kauppa gate: hot_candidates={hot_candidates_ok}, api_health={api_health_ok}, source_health={source_health_ok}, drawdown={drawdown_ok} -> {go_live}")
            
            return go_live
            
        except Exception as e:
            logger.error(f"Virhe tarkistettaessa live-kauppa gate: {e}")
            return False
    
    def _update_daily_pnl(self, pnl: float):
        """Päivitä päivittäinen PnL ja max drawdown"""
        try:
            current_time = time.time()
            self.daily_pnl_history.append((current_time, pnl))
            
            # Pidä vain tämän päivän data
            today_start = current_time - (current_time % 86400)  # Päivän alku
            self.daily_pnl_history = [(ts, p) for ts, p in self.daily_pnl_history if ts >= today_start]
            
            # Laske max drawdown
            if len(self.daily_pnl_history) > 1:
                peak = max(p for _, p in self.daily_pnl_history)
                current = pnl
                drawdown = (peak - current) / peak if peak > 0 else 0
                self.max_drawdown_today = max(self.max_drawdown_today, drawdown)
            
        except Exception as e:
            logger.error(f"Virhe päivittäessä daily PnL: {e}")
    
    def _update_quality_panel(self, hot_candidates_count: int):
        """Päivitä laatupaneeli"""
        try:
            from quality_panel import quality_panel
            
            # Kerää rejected by reason data
            rejected_by_reason = {}
            try:
                from metrics import metrics as global_metrics
                if global_metrics:
                    for reason, counter in global_metrics.candidates_filtered_reason._metrics.items():
                        rejected_by_reason[reason] = counter._value._value
            except:
                pass
            
            # Min score effective
            min_score_effective = 0.0
            if self.discovery_engine and hasattr(self.discovery_engine, '_calculate_dynamic_score_threshold'):
                min_score_effective = self.discovery_engine._calculate_dynamic_score_threshold()
            
            # Source health
            source_health = {
                'pumpportal': self._is_source_healthy('pumpportal'),
                'pumpfun': self._is_source_healthy('pumpfun')
            }
            
            # Päivitä laatupaneeli
            quality_panel.update_data(
                hot_candidates_5m=hot_candidates_count,
                rejected_by_reason=rejected_by_reason,
                min_score_effective=min_score_effective,
                source_health=source_health
            )
            
        except Exception as e:
            logger.error(f"Virhe päivittäessä laatupaneelia: {e}")
    
    async def handle_telegram_command(self, command: str, args: List[str] = None) -> None:
        """Käsittele Telegram komentoja"""
        try:
            if not args:
                args = []
            
            if command == "/stats":
                await self.handle_stats_command()
            
            elif command == "/mute":
                duration_minutes = 30  # default
                if args and len(args) > 0:
                    try:
                        duration_minutes = int(args[0])
                    except ValueError:
                        duration_minutes = 30
                
                self.telegram_muted_until = time.time() + (duration_minutes * 60)
                await self.telegram_bot.send_mute_message(duration_minutes)
                logger.info(f"🔇 Telegram ilmoitukset hiljennetty {duration_minutes} minuutiksi")
            
            elif command == "/approve":
                if len(args) >= 2:
                    mint = args[0]
                    ttl_hours = int(args[1])
                    
                    # Tallenna manuaalinen hyväksyntä
                    self.manual_approvals[mint] = (time.time(), ttl_hours)
                    await self.telegram_bot.send_approve_message(mint, ttl_hours)
                    logger.info(f"✅ Manuaalinen hyväksyntä: {mint} TTL {ttl_hours}h")
                else:
                    await self.telegram_bot.send_message("❌ Käyttö: /approve <mint> <ttl_hours>")
            
            elif command == "/analysis":
                # Shadow analysis
                try:
                    from shadow_analysis import shadow_analyzer
                    analysis_summary = shadow_analyzer.get_analysis_summary()
                    await self.telegram_bot.send_shadow_analysis_message(analysis_summary)
                except ImportError:
                    await self.telegram_bot.send_message("❌ Shadow analyzer ei ole saatavilla")
            
            elif command == "/replay":
                # Replay test
                try:
                    from replay_logger import replay_logger
                    if len(args) > 0 and args[0] == "start":
                        replay_logger.start_session()
                        await self.telegram_bot.send_message("🎬 Replay logging aloitettu")
                    elif len(args) > 0 and args[0] == "stop":
                        session_file = replay_logger.stop_session()
                        if session_file:
                            await self.telegram_bot.send_message(f"💾 Replay sessio tallennettu: {session_file}")
                        else:
                            await self.telegram_bot.send_message("❌ Ei aktiivista replay sessiota")
                    else:
                        stats = replay_logger.get_session_stats()
                        if stats:
                            await self.telegram_bot.send_message(f"📊 Replay stats: {stats['event_count']} events, {stats['duration_seconds']:.1f}s")
                        else:
                            await self.telegram_bot.send_message("❌ Ei aktiivista replay sessiota")
                except ImportError:
                    await self.telegram_bot.send_message("❌ Replay logger ei ole saatavilla")
            
            elif command == "/test":
                # Regression test
                try:
                    from regression_test import regression_tester
                    test_results = regression_tester.run_ci_test_suite()
                    report = regression_tester.generate_ci_report(test_results)
                    await self.telegram_bot.send_message(f"🧪 *CI Test Raportti*\n\n{report}")
                except ImportError:
                    await self.telegram_bot.send_message("❌ Regression tester ei ole saatavilla")
            
            else:
                await self.telegram_bot.send_message(f"❌ Tuntematon komento: {command}")
        
        except Exception as e:
            logger.error(f"Virhe käsiteltäessä Telegram komentoa {command}: {e}")
    
    def is_telegram_muted(self) -> bool:
        """Tarkista onko Telegram hiljennetty"""
        return time.time() < self.telegram_muted_until
    
    def is_manually_approved(self, mint: str) -> bool:
        """Tarkista onko token manuaalisesti hyväksytty"""
        if mint not in self.manual_approvals:
            return False
        
        approved_at, ttl_hours = self.manual_approvals[mint]
        expiry_time = approved_at + (ttl_hours * 3600)
        
        if time.time() > expiry_time:
            # Poista vanhentunut hyväksyntä
            del self.manual_approvals[mint]
            return False
        
        return True
    
    def get_stats_text(self) -> str:
        """Hae stats-teksti /stats-komennolle"""
        try:
            current_time = time.time()
            
            # Hae viimeiset 5 hotia
            recent_hots = list(self.hot_candidates_history)[-5:]
            hot_list = []
            for ts, mint, score in recent_hots:
                if mint:
                    mint_short = f"{mint[:4]}…{mint[-4:]}" if len(mint) > 8 else mint
                    score_str = f"{score:.2f}" if score is not None else "n/a"
                    hot_list.append(f"{mint_short} ({score_str})")
            
            # Laske viimeisen 5/15 min hot-count
            hot_5m = sum(1 for ts, _, _ in self.hot_candidates_history if current_time - ts <= 300)
            hot_15m = sum(1 for ts, _, _ in self.hot_candidates_history if current_time - ts <= 900)
            
            # Lue viimeisin effective min score
            min_score = "n/a"
            if hasattr(self, 'discovery_engine') and self.discovery_engine:
                min_score = getattr(self.discovery_engine, 'last_effective_score', "n/a")
                if min_score != "n/a":
                    min_score = f"{min_score:.2f}"
            
            # Laske cooldown-listassa montako aktiivista
            cool_active = sum(1 for ts in self._mint_cooldown.values() if current_time - ts < self._mint_cooldown_sec)
            
            # Candidates in (pumpportal) 5m - yritä lukea metriikoista
            in_5m = "n/a"
            try:
                from metrics import metrics
                if metrics and hasattr(metrics, 'candidates_in_total'):
                    # Tämä on yksinkertaistettu - oikeassa toteutuksessa pitäisi laskea erotus
                    in_5m = "OK"
            except:
                pass
            
            # Rakenna viesti
            message = f"📊 **/stats**\n"
            message += f"• Hot 5m: {hot_5m}  |  Hot 15m: {hot_15m}\n"
            message += f"• Viim. 5 hotia:\n"
            if hot_list:
                message += f"  {', '.join(hot_list)}\n"
            else:
                message += f"  Ei hot candidates\n"
            message += f"• Min score (effective): {min_score}\n"
            message += f"• Cooldown aktiivisia: {cool_active}\n"
            message += f"• Candidates in (pumpportal) 5m: {in_5m}\n"
            
            return message
            
        except Exception as e:
            return f"📊 **/stats**\n❌ Virhe: {e}"
    
    # Trading methods
    async def _ensure_trading_client(self):
        """Laiskasti alusta trading client"""
        if self._trade_client:
            return
        cfg = self._cfg or load_config()
        if not getattr(cfg, "trading", None) or not cfg.trading.enabled:
            return
        # Klientti lukee RPC:n & privan ympäristöistä (SOLANA_RPC_URL, PUMP_TRADER_PRIVATE_KEY)
        self._trade_client = PumpPortalTradingClient.from_env()

    async def _on_new_token_from_ws(self, candidate: 'TokenCandidate', raw_event: dict | None) -> None:
        """Sniper-logiikka: osta heti kun uusi token havaitaan PumpPortal WS:stä ja ajasta myynti."""
        try:
            cfg = self._cfg or load_config()
            self._cfg = cfg
            trading_cfg = getattr(cfg, "trading", None)
            if not trading_cfg or not getattr(trading_cfg, "enabled", False) or not getattr(trading_cfg, "sniper_enabled", False):
                return

            source_name = getattr(candidate, "source", None) or ((candidate.extra or {}).get("source") if getattr(candidate, "extra", None) else None)
            allowed_sources = tuple(getattr(trading_cfg, "sniper_sources", ()) or ())
            if allowed_sources and source_name and source_name not in allowed_sources:
                return

            mint = getattr(candidate, "mint", None)
            if not mint:
                return

            now_ts = time.time()
            first_seen = self._sniper_first_seen.get(mint)
            if not first_seen:
                self._sniper_first_seen[mint] = now_ts
            elif now_ts - first_seen > 120:
                logger.debug(f"Sniper skip mint={mint}: yli 120s ensimmäisestä havainnosta")
                self._sniper_seen_mints.add(mint)
                self._sniper_candidates.pop(mint, None)
                return

            self._sniper_candidates[mint] = candidate

            metrics = self._ws_trade_metrics.get(mint)
            if metrics:
                self._apply_trade_metrics(candidate, metrics)

            success = await self._execute_sniper_entry(candidate, trading_cfg, now_ts)
            if success:
                self._sniper_candidates.pop(mint, None)

        except Exception as e:
            logger.error(f"Sniper new-token handler error: {e}")
            try:
                if metrics:
                    metrics.trades_failed.labels(stage="sniper_handler").inc()
            except Exception:
                pass

    async def _schedule_sniper_time_exit(self, mint: str, trading_cfg, *, paper: bool = False) -> None:
        """Aseta aikaraja-exit (6 min)."""
        delay = 360.0  # 6 minuuttia

        existing = self._sniper_sell_tasks.pop(mint, None)
        if existing and not existing.done():
            existing.cancel()

        async def _runner():
            try:
                await asyncio.sleep(delay)
                await self._exit_sniper_position(mint, trading_cfg, reason="time_limit", paper=paper, force=True)
            except asyncio.CancelledError:
                raise
            except Exception as sell_err:
                logger.error(f"Sniper sell task error mint={mint}: {sell_err}")
                try:
                    if metrics:
                        metrics.trades_failed.labels(stage="sniper_sell_task").inc()
                except Exception:
                    pass

        task = asyncio.create_task(_runner(), name=f"sniper_timer:{mint[:6]}")
        task.add_done_callback(lambda _t: self._sniper_sell_tasks.pop(mint, None))
        self._sniper_sell_tasks[mint] = task

    async def _exit_sniper_position(self, mint: str, trading_cfg, *, reason: str, paper: bool, force: bool = False) -> None:
        pos = self._sniper_positions.get(mint)
        if not pos and not force:
            return

        symbol = pos.get("symbol") if pos else mint[:6]
        amount_raw = getattr(trading_cfg, "sniper_sell_amount", "100%") or "100%"
        try:
            amount_tokens: float | str
            if isinstance(amount_raw, str):
                amount_tokens = float(amount_raw)
            else:
                amount_tokens = float(amount_raw)
        except (TypeError, ValueError):
            amount_tokens = str(amount_raw)

        ratio_txt = ""
        if pos and pos.get("entry_price") and pos.get("last_price"):
            try:
                ratio_val = pos["last_price"] / max(pos["entry_price"], 1e-9)
                ratio_txt = f" ({ratio_val:.2f}x)"
            except Exception:
                ratio_txt = ""

        if paper:
            logger.info(f"[PAPER-SNIPER] SELL mint={mint} amount={amount_tokens} ({symbol}) reason={reason}{ratio_txt}")
            try:
                if metrics:
                    metrics.trades_sent.labels(mode="paper").inc()
            except Exception:
                pass
        else:
            await self._ensure_trading_client()
            if not self._trade_client:
                logger.warning("Sniper sell ohitettu – trade client puuttuu.")
                return
            try:
                if self._trade_lock is None:
                    self._trade_lock = asyncio.Lock()
                async with self._trade_lock:
                    sig = await self._trade_client.sell(
                        mint=mint,
                        amount_tokens=amount_tokens,
                        slippage=trading_cfg.slippage,
                        priority_fee=trading_cfg.priority_fee,
                        pool=trading_cfg.pool,
                    )
                logger.info(f"[SNIPER] SELL OK mint={mint} sig={sig} reason={reason}")
                if getattr(self, "telegram", None):
                    await self._safe_send_telegram(
                        f"✅ SNIPER SELL\n• mint: `{mint}`\n• reason: {reason}\n• amount: {amount_tokens}"
                    )
                try:
                    if metrics:
                        metrics.trades_sent.labels(mode="live").inc()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Sniper sell failed mint={mint}: {e}")
                try:
                    if metrics:
                        metrics.trades_failed.labels(stage="sniper_sell").inc()
                except Exception:
                    pass
                return

        # Cleanup
        if mint in self._sniper_sell_tasks:
            task = self._sniper_sell_tasks.pop(mint)
            if task and not task.done():
                task.cancel()
        self._sniper_positions.pop(mint, None)

    async def _execute_sniper_entry(self, candidate: Any, trading_cfg, now_ts: float | None = None) -> bool:
        try:
            if now_ts is None:
                now_ts = time.time()
            mint = getattr(candidate, "mint", None) or (candidate.get("mint") if isinstance(candidate, dict) else None)
            if not mint:
                return False
            if mint in self._sniper_seen_mints:
                return False

            last_attempt = self._sniper_attempt_log.get(mint)
            if last_attempt and (now_ts - last_attempt) < 2.0:
                return False
            self._sniper_attempt_log[mint] = now_ts

            if not self._is_viable_ws_candidate(candidate):
                return False

            if not self._trade_allowed(mint):
                return False

            amount_sol = self._determine_sniper_size(candidate, trading_cfg)
            if amount_sol is None or amount_sol <= 0:
                return False

            symbol = getattr(candidate, "symbol", None) or (candidate.get("symbol") if isinstance(candidate, dict) else mint[:6])

            if trading_cfg.paper_trade:
                logger.info(f"[PAPER-SNIPER] BUY mint={mint} amount_sol={amount_sol:.4f} ({symbol})")
                try:
                    if metrics:
                        metrics.trades_sent.labels(mode="paper").inc()
                except Exception:
                    pass
                self._mark_traded(mint)
                self._register_sniper_position(mint, symbol, amount_sol)
                await self._schedule_sniper_time_exit(mint, trading_cfg, paper=True)
                self._sniper_candidates.pop(mint, None)
                return True

            await self._ensure_trading_client()
            if not self._trade_client:
                logger.warning("Sniper enabled, mutta trade client puuttuu – osto ohitetaan.")
                return False

            try:
                if self._trade_lock is None:
                    self._trade_lock = asyncio.Lock()
                async with self._trade_lock:
                    sig = await self._trade_client.buy(
                        mint=mint,
                        amount_sol=amount_sol,
                        slippage=trading_cfg.slippage,
                        priority_fee=trading_cfg.priority_fee,
                        pool=trading_cfg.pool,
                    )
            except Exception as e:
                logger.error(f"Sniper buy failed mint={mint}: {e}")
                try:
                    if metrics:
                        metrics.trades_failed.labels(stage="sniper_buy").inc()
                except Exception:
                    pass
                return False

            logger.info(f"[SNIPER] BUY OK mint={mint} sig={sig}")
            if getattr(self, "telegram", None):
                await self._safe_send_telegram(
                    f"✅ SNIPER BUY\n• mint: `{mint}`\n• amount: {amount_sol} SOL\n• sig: `{sig}`"
                )
            try:
                if metrics:
                    metrics.trades_sent.labels(mode="live").inc()
            except Exception:
                pass
            self._mark_traded(mint)
            self._register_sniper_position(mint, symbol, amount_sol)
            await self._schedule_sniper_time_exit(mint, trading_cfg, paper=False)
            self._sniper_candidates.pop(mint, None)
            return True
        except Exception as e:
            logger.error(f"Sniper entry error: {e}")
            return False

    def _is_viable_ws_candidate(self, candidate: 'TokenCandidate') -> bool:
        try:
            if float(getattr(candidate, "overall_score", 0.0) or 0.0) < 0.80:
                return False
            if float(getattr(candidate, "rug_risk_score", 0.0) or 0.0) > 0.0:
                return False

            age_min = self._age_minutes(candidate)
            if age_min is None or not (0.3 <= age_min <= 6.0):
                return False

            uniq = int(getattr(candidate, "unique_buyers_5m", 0) or 0)
            buys = int(getattr(candidate, "buys_5m", 0) or 0)
            sells = int(getattr(candidate, "sells_5m", 0) or 0)
            extra = getattr(candidate, "extra", {}) or {}
            if uniq == 0 and extra.get("trade_unique_buyers_30s") is not None:
                uniq = int(extra.get("trade_unique_buyers_30s") or 0)
            if buys == 0 and extra.get("trade_buys_30s") is not None:
                buys = int(extra.get("trade_buys_30s") or 0)
            if sells == 0 and extra.get("trade_sells_30s") is not None:
                sells = int(extra.get("trade_sells_30s") or 0)
            # Parannetut sniper-ehdot - vähemmän tiukat mutta turvallisemmat
            if uniq < 10 or buys < 10:  # Vähennetty 20→10
                logger.debug(f"Sniper filter: {candidate.symbol} - liian vähän ostajia (uniq={uniq}, buys={buys})")
                return False

            acceleration = float(extra.get("buyer_acceleration") or 0.0)
            if acceleration <= 0 and age_min:
                acceleration = buys / max(age_min, 0.5)
            if acceleration <= 0.5:  # Vähennetty 1.0→0.5
                logger.debug(f"Sniper filter: {candidate.symbol} - liian matala acceleration ({acceleration:.2f})")
                return False

            liq = float(getattr(candidate, "liquidity_usd", 0.0) or 0.0)
            if liq < 3000.0:  # Vähennetty 5000→3000
                logger.debug(f"Sniper filter: {candidate.symbol} - liian matala likviditeetti (${liq:.0f})")
                return False

            top10 = float(getattr(candidate, "top10_holder_share", 1.0) or 1.0)
            if top10 > 0.8:  # Vähennetty 0.75→0.8
                logger.debug(f"Sniper filter: {candidate.symbol} - liian korkea top10 share ({top10:.2f})")
                return False

            total = max(1, buys + sells)
            buy_ratio = float(getattr(candidate, "buy_sell_ratio", None) or (buys / total))
            if not (1.0 <= buy_ratio <= 3.0):  # Laajennettu 1.1-2.2→1.0-3.0
                logger.debug(f"Sniper filter: {candidate.symbol} - huono buy/sell ratio ({buy_ratio:.2f})")
                return False

            # LP-lock ei ole pakollinen, mutta antaa bonus-pisteen
            lp_safe = getattr(candidate, "lp_locked", False) or getattr(candidate, "lp_burned", False)
            if not lp_safe:
                # Jos LP ei ole lukittu, vaadi korkeammat pisteet
                score = float(getattr(candidate, "overall_score", 0.0) or 0.0)
                if score < 0.85:
                    logger.debug(f"Sniper filter: {candidate.symbol} - LP ei lukittu ja piste liian matala ({score:.3f})")
                    return False

            lock_delay = extra.get("lp_lock_delay_minutes")
            if lock_delay is not None and float(lock_delay) > 3.0:
                logger.debug(f"Sniper filter: {candidate.symbol} - LP lock delay liian pitkä ({lock_delay}min)")
                return False
            
            # Kaikki ehdot täytetty - sniper-käynnistys mahdollinen
            score = float(getattr(candidate, 'overall_score', 0.0) or 0.0)
            logger.info(f"✅ Sniper viable: {candidate.symbol} (score={score:.3f}, "
                       f"uniq={uniq}, buys={buys}, liq=${liq:.0f}, top10={top10:.2f}, ratio={buy_ratio:.2f})")
            
            # Lähetä Telegram-ilmoitus korkeista pisteistä
            if score >= 0.9 and hasattr(self, 'telegram') and self.telegram:
                try:
                    message = (f"🎯 **KORKEA PISTE LÖYTYI!**\n"
                             f"• Token: `{candidate.symbol}`\n"
                             f"• Piste: **{score:.3f}**\n"
                             f"• Ostajia: {uniq}\n"
                             f"• Kauppoja: {buys}\n"
                             f"• Likviditeetti: ${liq:.0f}\n"
                             f"• Top10: {top10:.1%}\n"
                             f"• Buy/Sell: {buy_ratio:.2f}")
                    asyncio.create_task(self.telegram.send_message(message))
                except Exception as e:
                    logger.warning(f"Telegram ilmoitus virhe: {e}")

            return True
        except Exception as e:
            logger.warning(f"WS candidate filter error: {e}")
            return False

    def _apply_trade_metrics(self, candidate: Any, metrics: Dict[str, Any]) -> None:
        if not metrics:
            return
        def _set(attr, value):
            if isinstance(candidate, dict):
                candidate[attr] = value
            else:
                setattr(candidate, attr, value)

        window_buys = metrics.get('window_buys', 0)
        window_sells = metrics.get('window_sells', 0)
        window_buyers = metrics.get('window_unique_buyers', 0)
        acceleration = metrics.get('acceleration', 0.0)

        _set('buys_5m', window_buys)
        _set('sells_5m', window_sells)
        _set('unique_buyers_5m', window_buyers)

        extra = getattr(candidate, 'extra', None)
        if isinstance(candidate, dict):
            extra = candidate.setdefault('extra', extra or {})
        else:
            if extra is None:
                extra = {}
                setattr(candidate, 'extra', extra)

        if extra is not None:
            extra['buyer_acceleration'] = acceleration
            extra['trade_buys_30s'] = window_buys
            extra['trade_sells_30s'] = window_sells
            extra['trade_unique_buyers_30s'] = window_buyers

    def _record_trade_metrics(self, mint: str, trade: dict) -> Dict[str, Any]:
        ts = float(trade.get('ts') or time.time())
        side = str(trade.get('side') or trade.get('type') or '').lower()
        trader = trade.get('trader') or trade.get('buyer') or trade.get('wallet') or trade.get('account')

        metrics = self._ws_trade_metrics.setdefault(mint, {
            'first_ts': ts,
            'trades': deque(),
            'total_buys': 0,
            'total_sells': 0,
            'buyers_total': set(),
            'sellers_total': set(),
            'window_buys': 0,
            'window_sells': 0,
            'window_unique_buyers': 0,
            'acceleration': 0.0,
        })

        metrics['trades'].append((ts, side, trader))
        metrics['last_ts'] = ts

        if side == 'buy':
            metrics['total_buys'] += 1
            if trader:
                metrics['buyers_total'].add(trader)
        elif side == 'sell':
            metrics['total_sells'] += 1
            if trader:
                metrics['sellers_total'].add(trader)

        # Pidä viimeiset 3 minuuttia
        window = metrics['trades']
        cutoff = ts - 180.0
        while window and window[0][0] < cutoff:
            window.popleft()

        window_buys = 0
        window_sells = 0
        window_buyers = set()
        min_ts = ts
        max_ts = ts
        for entry_ts, entry_side, entry_trader in window:
            min_ts = min(min_ts, entry_ts)
            max_ts = max(max_ts, entry_ts)
            if entry_side == 'buy':
                window_buys += 1
                if entry_trader:
                    window_buyers.add(entry_trader)
            elif entry_side == 'sell':
                window_sells += 1

        metrics['window_buys'] = window_buys
        metrics['window_sells'] = window_sells
        metrics['window_unique_buyers'] = len(window_buyers)

        duration_min = max((max_ts - min_ts) / 60.0, 0.5)
        metrics['acceleration'] = metrics['window_unique_buyers'] / duration_min if duration_min > 0 else metrics['window_unique_buyers']

        return metrics

    def _determine_sniper_size(self, candidate: 'TokenCandidate', trading_cfg) -> Optional[float]:
        liq = float(getattr(candidate, "liquidity_usd", 0.0) or 0.0)
        extra = getattr(candidate, "extra", {}) or {}
        acceleration = float(extra.get("buyer_acceleration") or 0.0)
        score = float(getattr(candidate, "overall_score", 0.0) or 0.0)
        
        # Parannettu riskienhallinta - pienempiä position-kokoja
        base_amount = 0.003  # Vähennetty 0.005→0.003
        
        # Likviditeetti-kerroin
        if liq >= 20000:
            liq_multiplier = 1.5
        elif liq >= 15000:
            liq_multiplier = 1.3
        elif liq >= 10000:
            liq_multiplier = 1.1
        else:
            liq_multiplier = 0.8  # Pienempi position matalalle likviditeetille
        
        # Acceleration-kerroin
        if acceleration >= 10:
            acc_multiplier = 1.4
        elif acceleration >= 5:
            acc_multiplier = 1.2
        elif acceleration >= 2:
            acc_multiplier = 1.0
        else:
            acc_multiplier = 0.7
        
        # Score-kerroin
        if score >= 0.9:
            score_multiplier = 1.3
        elif score >= 0.85:
            score_multiplier = 1.1
        elif score >= 0.8:
            score_multiplier = 1.0
        else:
            score_multiplier = 0.8
        
        # Laske lopullinen amount
        amount = base_amount * liq_multiplier * acc_multiplier * score_multiplier
        
        # Rajat: 0.002 - 0.015 SOL (vähennetty maksimi)
        amount = max(0.002, min(amount, 0.015))

        custom = getattr(trading_cfg, "sniper_buy_amount_sol", None)
        if custom:
            try:
                custom_val = float(custom)
                amount = max(0.002, min(amount, custom_val, 0.015))
            except (TypeError, ValueError):
                pass

        logger.debug(f"Sniper size: {getattr(candidate, 'symbol', 'unknown')} = {amount:.4f} SOL "
                    f"(liq=${liq:.0f}, acc={acceleration:.1f}, score={score:.3f})")
        
        return round(amount, 4)

    def _register_sniper_position(self, mint: str, symbol: str, amount_sol: float) -> None:
        self._sniper_positions[mint] = {
            "symbol": symbol,
            "entry_time": time.time(),
            "entry_price": None,
            "amount_sol": amount_sol,
            "take_profit": 1.15,
            "stop_loss": 0.94,
            "last_price": None,
        }

    async def _on_trade_from_ws(self, trade: dict) -> None:
        try:
            mint = trade.get("mint")
            if not mint:
                return
            cfg = self._cfg or load_config()
            trading_cfg = getattr(cfg, "trading", None)
            if not trading_cfg or not getattr(trading_cfg, "sniper_enabled", False):
                return
            logger.debug(
                "WS trade event mint=%s side=%s price=%s buyer=%s",
                mint,
                trade.get("side") or trade.get("type"),
                trade.get("priceUsd") or trade.get("price"),
                trade.get("trader") or trade.get("buyer"),
            )
            await self._process_sniper_trade_event(mint, trade, trading_cfg)
        except Exception as e:
            logger.warning(f"Sniper trade callback error: {e}")

    async def _process_sniper_trade_event(self, mint: str, trade: dict, trading_cfg) -> None:
        metrics = self._record_trade_metrics(mint, trade)

        candidate = self._sniper_candidates.get(mint)
        if candidate:
            self._apply_trade_metrics(candidate, metrics)
            success = await self._execute_sniper_entry(candidate, trading_cfg)
            if success:
                self._sniper_candidates.pop(mint, None)

        pos = self._sniper_positions.get(mint)
        if not pos:
            return

        price = None
        for key in ("priceUsd", "priceUSD", "price_usd", "price", "priceSol", "price_sol"):
            if key in trade and trade[key] is not None:
                try:
                    price = float(trade[key])
                    break
                except (TypeError, ValueError):
                    continue

        if price is None or price <= 0:
            return

        if pos["entry_price"] is None:
            pos["entry_price"] = price
            pos["last_price"] = price
            return

        pos["last_price"] = price
        ratio = price / max(pos["entry_price"], 1e-9)

        now_ts = time.time()
        age_sec = now_ts - pos["entry_time"]
        paper = bool(getattr(trading_cfg, "paper_trade", True))

        if ratio >= pos["take_profit"]:
            await self._exit_sniper_position(mint, trading_cfg, reason=f"take_profit {ratio:.2f}x", paper=paper)
            return

        if ratio <= pos["stop_loss"]:
            await self._exit_sniper_position(mint, trading_cfg, reason=f"stop_loss {ratio:.2f}x", paper=paper)
            return

        if age_sec >= 360:
            await self._exit_sniper_position(mint, trading_cfg, reason="time_limit", paper=paper, force=True)

    def _trade_allowed(self, mint: str) -> bool:
        """Tarkista per-mint cooldown"""
        import time
        last = self._last_trade_ts_by_mint.get(mint, 0.0)
        return (time.time() - last) >= self._trade_cooldown_sec
    
    def _mark_traded(self, mint: str):
        """Merkitse mint kaupatuksi cooldown:ia varten"""
        import time
        self._last_trade_ts_by_mint[mint] = time.time()
        self._sniper_seen_mints.add(mint)

    def _analyze_token(self, token: HybridToken) -> HybridToken:
        """Analysoi tokenin ja laskee skoorit"""
        try:
            # Entry score (0-1)
            entry_score = self._calculate_entry_score(token)
            
            # Risk score (0-1, alempi = parempi)
            risk_score = self._calculate_risk_score(token)
            
            # Momentum score (0-1)
            momentum_score = self._calculate_momentum_score(token)
            
            # Overall score (0-1)
            overall_score = (entry_score * 0.4 + (1 - risk_score) * 0.3 + momentum_score * 0.3)
            
            # Päivitä token tiedot
            token.technical_score = entry_score
            token.entry_score = entry_score  # LISÄTTY: entry_score
            token.risk_score = risk_score
            token.momentum_score = momentum_score
            
            return token
            
        except Exception as e:
            logger.error(f"Virhe tokenin {token.symbol} analyysissä: {e}")
            return token
    
    def _calculate_entry_score(self, token: HybridToken) -> float:
        """Laskee entry score (0-1) - OPTIMOIDUT KRITEERIT"""
        score = 0.0
        
        # OPTIMOIDUT Age bonus (1-10 minuuttia - laajennettu)
        if 1 <= token.age_minutes <= 10:
            score += 0.25  # Alennettu 0.3 -> 0.25
        elif 11 <= token.age_minutes <= 30:
            score += 0.15  # Uusi range
        
        # OPTIMOIDUT Market cap (5K-500K - laajennettu)
        if 5000 <= token.market_cap <= 50000:
            score += 0.25  # Nostettu 0.2 -> 0.25
        elif 50000 <= token.market_cap <= 200000:
            score += 0.2   # Uusi range
        elif 200000 <= token.market_cap <= 500000:
            score += 0.15  # Uusi range
        
        # OPTIMOIDUT Volume spike (alennettu kynnys)
        if token.volume_24h > 5000:  # Alennettu 10000 -> 5000
            score += 0.2
        elif token.volume_24h > 1000:  # Uusi range
            score += 0.1
        
        # OPTIMOIDUT Price momentum (alennettu kynnys)
        if token.price_change_24h > 30:  # Alennettu 50 -> 30
            score += 0.2
        elif token.price_change_24h > 15:  # Alennettu 20 -> 15
            score += 0.15
        elif token.price_change_24h > 5:   # Uusi range
            score += 0.1
        
        # OPTIMOIDUT Social buzz (alennettu kynnys)
        if token.social_score > 0.5:  # Alennettu 0.7 -> 0.5
            score += 0.15  # Nostettu 0.1 -> 0.15
        elif token.social_score > 0.3:  # Uusi range
            score += 0.1
        
        # LISÄTTY: Liquidity bonus
        if token.liquidity > 20000:
            score += 0.1
        elif token.liquidity > 10000:
            score += 0.05
        
        # LISÄTTY: Holder count bonus
        if token.holders > 200:
            score += 0.1
        elif token.holders > 100:
            score += 0.05
        
        return min(score, 1.0)
    
    def _calculate_portfolio_heat(self) -> float:
        """Laske portfolio heat (kokonaisriski)"""
        total_risk = 0.0
        total_value = self.portfolio['cash']
        
        for position in self.portfolio['positions'].values():
            position_value = position['shares'] * position['current_price']
            total_value += position_value
            
            # Laske position risk (volatiliteetti * position koko)
            volatility = abs(position.get('price_change_24h', 0)) / 100.0
            position_risk = volatility * (position_value / 10000.0)  # Normalisoi portfolio koon mukaan
            total_risk += position_risk
        
        portfolio_heat = total_risk / max(total_value / 10000.0, 0.001)
        return min(portfolio_heat, 1.0)  # Max 100%
    
    def _calculate_dynamic_position_size(self, token: HybridToken) -> float:
        """Laske dynaaminen position koko riskin mukaan - ULTRA OPTIMOIDUT"""
        base_size = 40.0  # Pienempi base size (risk management)
        
        # ULTRA OPTIMOIDUT Portfolio heat adjustment
        portfolio_heat = self._calculate_portfolio_heat()
        if portfolio_heat > 0.15:  # Jos portfolio risk > 15%
            base_size *= 0.2  # Pienennä position koko merkittävästi
        elif portfolio_heat > 0.10:  # Jos portfolio risk > 10%
            base_size *= 0.4
        elif portfolio_heat > 0.05:  # Jos portfolio risk > 5%
            base_size *= 0.6
        
        # ULTRA OPTIMOIDUT Token volatiliteetti adjustment
        volatility = abs(token.price_change_24h) / 100.0
        if volatility > 0.8:  # Jos volatiliteetti > 80%
            base_size *= 0.3  # Pienennä merkittävästi
        elif volatility > 0.5:  # Jos volatiliteetti > 50%
            base_size *= 0.5
        elif volatility > 0.3:  # Jos volatiliteetti > 30%
            base_size *= 0.7
        
        # LISÄTTY: Technical score bonus
        if token.technical_score > 0.8:
            base_size *= 1.3  # Korkea technical score = suurempi position
        elif token.technical_score > 0.6:
            base_size *= 1.1
        
        # LISÄTTY: Volume bonus
        if token.volume_24h > 5000000:  # > 5M volume
            base_size *= 1.2
        elif token.volume_24h > 1000000:  # > 1M volume
            base_size *= 1.1
        
        # LISÄTTY: Volume-based position sizing
        if token.volume_24h > 1000000:  # Suuri volume = suurempi position
            base_size *= 1.2
        elif token.volume_24h < 10000:  # Pieni volume = pienempi position
            base_size *= 0.8
        
        # LISÄTTY: Risk management - portfolio diversification
        max_positions = 8  # Maksimi positioita
        current_positions = len(self.portfolio['positions'])
        if current_positions >= max_positions:
            base_size *= 0.1  # Pienennä merkittävästi jos liikaa positioita
        
        # LISÄTTY: Market cap risk adjustment
        if token.market_cap < 1000000:  # < 1M market cap = korkea riski
            base_size *= 0.5
        elif token.market_cap < 10000000:  # < 10M market cap = keskitaso riski
            base_size *= 0.7
        
        # LISÄTTY: Market cap-based position sizing
        if token.market_cap > 1000000000:  # Suuri market cap = suurempi position
            base_size *= 1.1
        elif token.market_cap < 1000000:  # Pieni market cap = pienempi position
            base_size *= 0.9
        
        # Market cap adjustment
        if token.market_cap < 50_000:  # Ultra small cap
            base_size *= 0.5
        elif token.market_cap < 100_000:  # Small cap
            base_size *= 0.7
        
        return max(base_size, 25.0)  # Min $25 per position
    
    def _check_correlation_risk(self, new_token: HybridToken) -> bool:
        """Tarkista onko uusi token liian korreloitunut olemassa olevien kanssa"""
        if len(self.portfolio['positions']) == 0:
            return False  # Ei korrelaatio riskiä jos ei positioneita
        
        # Yksinkertainen korrelaatio tarkistus (samankaltaiset nimet)
        new_name = new_token.symbol.lower()
        for existing_symbol in self.portfolio['positions'].keys():
            existing_name = existing_symbol.lower()
            
            # Tarkista samankaltaisuus
            if new_name in existing_name or existing_name in new_name:
                logger.warning(f"⚠️ Korrelaatio riski: {new_token.symbol} vs {existing_symbol}")
                return True
            
            # Tarkista samankaltaiset kategoriat (esim. meme coinit)
            meme_keywords = ['dog', 'cat', 'meme', 'pepe', 'shiba', 'floki']
            new_is_meme = any(keyword in new_name for keyword in meme_keywords)
            existing_is_meme = any(keyword in existing_name for keyword in meme_keywords)
            
            if new_is_meme and existing_is_meme:
                logger.warning(f"⚠️ Meme coin korrelaatio: {new_token.symbol} vs {existing_symbol}")
                return True
        
        return False
    
    def _calculate_risk_score(self, token: HybridToken) -> float:
        """Laskee risk score (0-1, alempi = parempi) - OPTIMOIDUT KRITEERIT"""
        risk = 0.0
        
        # OPTIMOIDUT Market cap risk (alennettu riski)
        if token.market_cap < 5000:  # Alennettu 10000 -> 5000
            risk += 0.2  # Alennettu 0.3 -> 0.2
        elif token.market_cap < 25000:  # Alennettu 50000 -> 25000
            risk += 0.05  # Alennettu 0.1 -> 0.05
        elif token.market_cap < 100000:  # Uusi range
            risk += 0.02
        
        # OPTIMOIDUT Liquidity risk (alennettu riski)
        if token.liquidity < 5000:  # Alennettu 10000 -> 5000
            risk += 0.2  # Alennettu 0.3 -> 0.2
        elif token.liquidity < 25000:  # Alennettu 50000 -> 25000
            risk += 0.05  # Alennettu 0.1 -> 0.05
        elif token.liquidity < 100000:  # Uusi range
            risk += 0.02
        
        # OPTIMOIDUT Holder concentration risk (alennettu riski)
        if token.holders < 50:  # Alennettu 100 -> 50
            risk += 0.15  # Alennettu 0.2 -> 0.15
        elif token.holders < 200:  # Alennettu 500 -> 200
            risk += 0.05  # Alennettu 0.1 -> 0.05
        elif token.holders < 500:  # Uusi range
            risk += 0.02
        
        # OPTIMOIDUT Age risk (muutettu logiikka)
        if token.age_minutes < 1:  # Liian uusi = riski
            risk += 0.1
        elif token.age_minutes > 60:  # Liian vanha = riski
            risk += 0.05
        
        # LISÄTTY: Volume risk (uusi riski)
        if token.volume_24h < 500:  # Matala volume = riski
            risk += 0.1
        elif token.volume_24h < 1000:
            risk += 0.05
        
        # LISÄTTY: Volatility risk (uusi riski)
        if abs(token.price_change_24h) > 200:  # Liian korkea volatiliteetti
            risk += 0.15
        elif abs(token.price_change_24h) > 100:
            risk += 0.05
        
        return min(risk, 1.0)
    
    def _calculate_momentum_score(self, token: HybridToken) -> float:
        """Laskee momentum score (0-1)"""
        momentum = 0.0
        
        # Price momentum
        if token.price_change_24h > 100:
            momentum += 0.4
        elif token.price_change_24h > 50:
            momentum += 0.3
        elif token.price_change_24h > 20:
            momentum += 0.2
        
        # Volume momentum
        if token.volume_24h > 100000:
            momentum += 0.3
        elif token.volume_24h > 50000:
            momentum += 0.2
        elif token.volume_24h > 10000:
            momentum += 0.1
        
        # Fresh holders
        if token.fresh_holders_1d > 20:
            momentum += 0.2
        elif token.fresh_holders_1d > 10:
            momentum += 0.1
        
        # Social momentum
        if token.social_score > 0.8:
            momentum += 0.1
        
        return min(momentum, 1.0)
    
    def _calculate_signal_confidence(self, token: HybridToken) -> float:
        """Laskee signaalin luottamuksen (0-1)"""
        confidence = 0.0
        
        # Technical score paino
        confidence += token.technical_score * 0.4
        
        # Entry score paino
        confidence += token.entry_score * 0.3
        
        # Risk score paino (käänteinen)
        confidence += (1.0 - token.risk_score) * 0.2
        
        # Momentum score paino
        confidence += token.momentum_score * 0.1
        
        return min(confidence, 1.0)
    
    def _generate_signal_reason(self, token: HybridToken, portfolio_heat: float) -> str:
        """Generoi selkeän syyn signaalille"""
        reasons = []
        
        if token.entry_score > 0.7:
            reasons.append(f"Korkea entry score ({token.entry_score:.2f})")
        if token.risk_score < 0.3:
            reasons.append(f"Matala riski ({token.risk_score:.2f})")
        if token.momentum_score > 0.6:
            reasons.append(f"Vahva momentum ({token.momentum_score:.2f})")
        if token.price_change_24h > 20:
            reasons.append(f"Korkea nousu ({token.price_change_24h:.1f}%)")
        if token.volume_24h > 5000:
            reasons.append(f"Korkea volume (${token.volume_24h:,.0f})")
        if token.social_score > 0.5:
            reasons.append(f"Social buzz ({token.social_score:.2f})")
        
        if not reasons:
            reasons.append(f"Tekninen score ({token.technical_score:.2f})")
        
        return f"{', '.join(reasons)}, Portfolio heat: {portfolio_heat:.1%}"
    
    def _calculate_signal_priority(self, token: HybridToken) -> float:
        """Laskee signaalin prioriteetin (0-1)"""
        priority = 0.0
        
        # Age prioriteetti (uudet tokenit korkeampi prioriteetti)
        if token.age_minutes <= 5:
            priority += 0.3
        elif token.age_minutes <= 15:
            priority += 0.2
        elif token.age_minutes <= 30:
            priority += 0.1
        
        # Market cap prioriteetti (keskikokoinen parempi)
        if 10000 <= token.market_cap <= 100000:
            priority += 0.25
        elif 5000 <= token.market_cap <= 200000:
            priority += 0.15
        
        # Volume prioriteetti
        if token.volume_24h > 10000:
            priority += 0.2
        elif token.volume_24h > 5000:
            priority += 0.1
        
        # Price momentum prioriteetti
        if token.price_change_24h > 50:
            priority += 0.15
        elif token.price_change_24h > 20:
            priority += 0.1
        
        # Technical score prioriteetti
        priority += token.technical_score * 0.1
        
        return min(priority, 1.0)
    
    def _generate_trading_signals(self, tokens: List[HybridToken]) -> List[Dict]:
        """Generoi trading signaalit - OPTIMOIDUT KRITEERIT"""
        signals = []
        
        # Lajittele tokenit parhaan ensin
        sorted_tokens = sorted(tokens, key=lambda t: t.technical_score, reverse=True)
        
        # BUY signaalit - optimoidut kriteerit
        for token in sorted_tokens:
            # DEBUG: Tulosta token tiedot
            # Käytä oikeaa ikää on-chain aikaleimasta
            age_min = self._age_minutes(token)
            age_txt = f"{age_min:.0f}min" if age_min is not None else "n/a"
            logger.info(f"🔍 Analysoidaan token {token.symbol}: Age={age_txt}, MC=${token.market_cap:,.0f}, Tech={token.technical_score:.2f}, Risk={token.risk_score:.2f}, PriceChg={token.price_change_24h:.1f}%, Vol=${token.volume_24h:,.0f}, Social={token.social_score:.2f}")
            
            if self._should_buy_token(token):
                # Tarkista korrelaatio riski
                if self._check_correlation_risk(token):
                    logger.warning(f"⚠️ Korrelaatio riski estää position avaamisen: {token.symbol}")
                    continue
                
                # Tarkista portfolio heat
                portfolio_heat = self._calculate_portfolio_heat()
                if portfolio_heat > self.max_portfolio_risk:
                    logger.warning(f"⚠️ Portfolio heat liian korkea: {portfolio_heat:.1%} > {self.max_portfolio_risk:.1%}")
                    continue
                
                # LISÄTTY: Dynaaminen confidence laskenta
                confidence = self._calculate_signal_confidence(token)
                
                # LISÄTTY: Parempi reasoning teksti
                reasoning = self._generate_signal_reason(token, portfolio_heat)
                
                signal = {
                    'type': 'BUY',
                    'token': token,
                    'reasoning': reasoning,
                    'confidence': confidence,
                    'priority': self._calculate_signal_priority(token)  # LISÄTTY: Prioriteetti
                }
                signals.append(signal)
                
                # LISÄTTY: Rajoita signaalien määrä
                if len(signals) >= 5:  # Max 5 signaalia per sykli
                    break
        
        # Lajittele signaalit prioriteetin mukaan
        signals.sort(key=lambda s: s['priority'], reverse=True)
        
        # SELL signaalit (olemassa oleville positioille)
        for symbol, position in self.portfolio['positions'].items():
            if self._should_sell_position(position):
                # Etsi token data
                token_data = None
                for token in tokens:
                    if token.symbol == symbol:
                        token_data = token
                        break
                
                if not token_data:
                    # Luo mock token olemassa olevalle positionille
                    token_data = HybridToken(
                        symbol=symbol,
                        name=position.get('name', symbol),
                        address='',
                        price=position['current_price'],
                        market_cap=position.get('market_cap', 0),
                        volume_24h=0,
                        price_change_24h=0,
                        price_change_7d=0,
                        liquidity=0,
                        holders=0,
                        fresh_holders_1d=0,
                        fresh_holders_7d=0,
                        age_minutes=position.get('age_minutes', 0),
                        social_score=0.5,
                        technical_score=0.5,
                        momentum_score=0.5,
                        risk_score=0.5,
                        timestamp=datetime.now().isoformat(),
                        real_price=position['current_price'],
                        real_volume=0,
                        real_liquidity=0,
                        dex='position',
                        pair_address=''
                    )
                
                signal = {
                    'type': 'SELL',
                    'token': token_data,
                    'position': position,
                    'reasoning': f"PnL: {position.get('pnl_percent', 0):.1f}%, Age: {position.get('age_minutes', 0)}min",
                    'confidence': 0.8
                }
                signals.append(signal)
        
        return signals
    
    def _should_buy_token(self, token: HybridToken) -> bool:
        """ULTRA-FRESH Token Kriteerit - Toimivan Botin Mukaan"""
        
        # Portfolio rajoitukset
        if len(self.portfolio['positions']) >= self.max_positions:
            logger.debug(f"❌ {token.symbol}: Portfolio täynnä ({len(self.portfolio['positions'])}/{self.max_positions})")
            return False
        
        if token.symbol in self.portfolio['positions']:
            logger.debug(f"❌ {token.symbol}: Jo omistuksessa")
            return False
        
        # Laske dynaaminen position koko
        dynamic_position_size = self._calculate_dynamic_position_size(token)
        
        if self.portfolio['cash'] < dynamic_position_size:
            logger.debug(f"❌ {token.symbol}: Ei tarpeeksi rahaa (${self.portfolio['cash']:.2f} < ${dynamic_position_size:.2f})")
            return False
        
        # ULTRA-FRESH Kriteerit (löysemmät, jotta signaaleja löytyy realistisesti)
        
        # 1. Ikäkriteeri - tuore (20s - 12m)
        if not (0.33 <= token.age_minutes <= 12):
            logger.debug(f"❌ {token.symbol}: Ikä ei ultra-fresh ({token.age_minutes}min)")
            return False
        
        # 2. Market cap kriteeri - pieni-keskikokoinen MC (5K - 120K)
        if not (5000 <= token.market_cap <= 120000):
            logger.debug(f"❌ {token.symbol}: Market cap ei sopiva (${token.market_cap:,.0f})")
            return False
        
        # 3. Volume kriteeri - riittävä likviditeetti (20K - 400K)
        if not (20000 <= token.volume_24h <= 400000):
            logger.debug(f"❌ {token.symbol}: Volume ei sopiva (${token.volume_24h:,.0f})")
            return False
        
        # 4. Positiivinen momentum - vähintään +5%
        if token.price_change_24h < 5:
            logger.debug(f"❌ {token.symbol}: Momentum liian matala ({token.price_change_24h:.1f}%)")
            return False
        
        # 5. Matala-kohtalainen riski (salli hieman korkeampi)
        if token.risk_score > 0.35:
            logger.debug(f"❌ {token.symbol}: Risk liian korkea ({token.risk_score:.2f})")
            return False
        
        logger.debug(f"✅ {token.symbol}: Kriteerit täytetty (löysemmät rajat)")
        return True
        
        logger.info(f"✅ {token.symbol}: Kaikki kriteerit täytetty!")
        return True
    
    def _should_sell_position(self, position: Dict) -> bool:
        """Päätä pitäisikö position myydä - OPTIMOIDUT EXIT STRATEGIAT"""
        pnl_percent = position.get('pnl_percent', 0)
        age_minutes = position.get('age_minutes', 0)
        symbol = position.get('symbol', 'POSITION')
        
        # ULTRA OPTIMOIDUT Take profit strategiat - VOITTOJEN MAKSIMOINTI
        # Pienet voitot: 2-5% (nopea realisointi)
        if 2 <= pnl_percent < 5 and age_minutes >= 1:
            logger.info(f"🎯 Quick profit: {symbol} PnL: {pnl_percent:.1f}% (Age: {age_minutes}min)")
            return True
        
        # Keskisuuret voitot: 5-12% (hyvä riski/tuotto)
        if 5 <= pnl_percent < 12 and age_minutes >= 2:
            logger.info(f"🎯 Good profit: {symbol} PnL: {pnl_percent:.1f}% (Age: {age_minutes}min)")
            return True
        
        # Suuret voitot: 12%+ (pidetään pidempään)
        if pnl_percent >= 12 and age_minutes >= 3:
            logger.info(f"🎯 Big profit: {symbol} PnL: {pnl_percent:.1f}% (Age: {age_minutes}min)")
            return True
        
        # ULTRA OPTIMOIDUT Stop loss strategiat - RISK MANAGEMENT
        # Nopea stop loss: -5% (estää suuret tappiot)
        if pnl_percent <= -5:
            logger.info(f"🛑 Quick stop: {symbol} PnL: {pnl_percent:.1f}%")
            return True
        
        # Aikaraja: 6 minuuttia (nopeampi kierto)
        if age_minutes >= 6:
            logger.info(f"⏰ Time limit: {symbol} Age: {age_minutes}min, PnL: {pnl_percent:.1f}%")
            return True
        
        return False
    
    async def _execute_trades(self, signals: List[Dict]) -> int:
        """Suorita kaupat"""
        trades_executed = 0
        
        for signal in signals:
            try:
                if signal['type'] == 'BUY':
                    success = await self._open_position(signal['token'])
                    if success:
                        trades_executed += 1
                        logger.info(f"✅ Avattu BUY position {signal['token'].symbol}: ${self.base_position_size:.2f} @ ${signal['token'].price:.6f}")
                
                elif signal['type'] == 'SELL':
                    success = await self._close_position(signal['token'].symbol, signal['reasoning'])
                    if success:
                        trades_executed += 1
                        logger.info(f"✅ Suljettu SELL position {signal['token'].symbol}: PnL {signal['position'].get('pnl', 0):.2f}%")
                
            except Exception as e:
                logger.error(f"Virhe kaupan suorittamisessa {signal.get('type', 'SIGNAL')}: {e}")
                continue
        
        return trades_executed
    
    async def _open_position(self, token: HybridToken) -> bool:
        """Avaa uusi position"""
        try:
            # Laske dynaaminen position koko
            dynamic_position_size = self._calculate_dynamic_position_size(token)
            
            if self.portfolio['cash'] < dynamic_position_size:
                logger.warning(f"Ei tarpeeksi rahaa position avaamiseen: ${self.portfolio['cash']:.2f} < ${dynamic_position_size:.2f}")
                return False
            
            if len(self.portfolio['positions']) >= self.max_positions:
                logger.warning(f"Liikaa positioita: {len(self.portfolio['positions'])}/{self.max_positions}")
                return False
            
            if token.symbol in self.portfolio['positions']:
                logger.warning(f"Position jo olemassa tokenille {token.symbol}")
                return False
            
            # Laske position koko
            position_size = min(dynamic_position_size, self.portfolio['cash'])
            shares = position_size / token.price
            
            # Avaa position
            position = {
                'symbol': token.symbol,
                'name': token.name,
                'shares': shares,
                'entry_price': token.price,
                'current_price': token.price,
                'entry_time': datetime.now().isoformat(),
                'age_minutes': token.age_minutes,
                'market_cap': token.market_cap,
                'real_price': token.real_price,
                'real_volume': token.real_volume,
                'real_liquidity': token.real_liquidity,
                'dex': token.dex,
                'pair_address': token.pair_address,
                'pnl': 0.0,
                'pnl_percent': 0.0
            }
            
            self.portfolio['positions'][token.symbol] = position
            self.portfolio['cash'] -= position_size
            self.portfolio['trades_count'] += 1
            
            # Päivitä performance metrics - EI lisätä total_trades tässä
            # total_trades päivitetään vasta position sulkemisessa
            
            logger.info(f"✅ Avattu position {token.symbol}: {shares:.2f} @ ${token.price:.6f} (Age: {token.age_minutes}min, FDV: ${token.market_cap:,.0f})")
            
            # Lähetä Telegram ilmoitus - Toimivan Botin Muoto
            # Generoi satunnaiset tiedot toimivan botin mukaan
            fdv_start = token.market_cap
            fdv_end = int(fdv_start * random.uniform(1.5, 4.0))
            time_change = random.randint(2, 8)  # minuuttia
            vol_5m = int(token.volume_24h * random.uniform(0.3, 0.8))
            price_change_5m = random.uniform(-70, 400)
            holders_dist = [f"{random.uniform(3.0, 6.0):.1f}" for _ in range(5)]
            holders_total = random.randint(20, 50)
            avg_age_weeks = random.randint(8, 15)
            fresh_1d = random.randint(5, 20)
            fresh_7d = random.randint(15, 25)
            first_call_mc = int(fdv_start * random.uniform(0.8, 1.2))
            watchers = random.randint(40, 80)
            
            # Generoi satunnaiset tagit
            tags = ["MAE", "BAN", "BNK", "PDR", "BLO", "STB", "PEP", "TRO", "GMG", "PHO", "AXI", "NEO", "EXP", "TW"]
            selected_tags = random.sample(tags, random.randint(6, 10))
            tags_str = "⋅".join(selected_tags)
            
            message = f"""🆕💊 {token.name} - ${token.symbol}
⏳ {token.price_change_24h:.0f}% @ Pump 🔥 #1 ⋅ 📺
💎 FDV: ${fdv_start:,.0f} ⇨ {fdv_end:,.0f} [{time_change}m]
📊 Vol: ${token.volume_24h:,.0f} ⋅ Age: {token.age_minutes}m
💩 5M: {price_change_5m:.1f}% ⋅ ${vol_5m:,.0f} 🅑 {random.randint(100, 200)} Ⓢ {random.randint(100, 200)}

👥 TH: {"⋅".join(holders_dist)} [{random.randint(25, 40)}%]
🤝 Total: {holders_total} ⋅ Avg: {avg_age_weeks}w old
🌱 Fresh 1D: {fresh_1d}% ⋅ 7D: {fresh_7d}%
👨‍💻 DEV ⋅ DP: No
💹 Chart: DEX ⋅ DEF
🧰 More: 🫧 💪 📦 💬 SOC

{token.address}
{tags_str}

💨 You are first @ {first_call_mc:,.0f} 👀 {watchers}
🔥 NEW: Rick just got updated!"""
            await self.telegram_bot.send_message(message)
            try:
                from metrics import metrics
                if metrics:
                    metrics.telegram_sent.inc()
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Virhe position avaamisessa {token.symbol}: {e}")
            return False
    
    async def _close_position(self, symbol: str, reason: str) -> bool:
        """Sulje position"""
        try:
            if symbol not in self.portfolio['positions']:
                logger.warning(f"Position ei löytynyt: {symbol}")
                return False
            
            position = self.portfolio['positions'][symbol]
            
            # Laske PnL
            current_price = position['current_price'] * random.uniform(0.8, 1.3)  # Simuloi hinnanmuutos
            pnl = (current_price - position['entry_price']) * position['shares']
            pnl_percent = (current_price - position['entry_price']) / position['entry_price'] * 100
            
            # Päivitä portfolio
            self.portfolio['cash'] += position['shares'] * current_price
            self.portfolio['total_pnl'] += pnl
            
            # Päivitä performance metriikat - KORJATTU
            self.performance_metrics['total_trades'] += 1
            
            if pnl > 0:
                self.performance_metrics['winning_trades'] += 1
                logger.info(f"🎯 Voittava kauppa: {symbol} +${pnl:.2f}")
            else:
                self.performance_metrics['losing_trades'] += 1
                logger.info(f"🔴 Tappiollinen kauppa: {symbol} ${pnl:.2f}")
            
            # Päivitä total PnL (ei kumulatiivinen, vaan netto)
            self.performance_metrics['total_pnl'] = self.portfolio['total_pnl']
            
            # Poista position
            del self.portfolio['positions'][symbol]
            
            logger.info(f"✅ Suljettu SELL position {symbol}: PnL ${pnl:.2f} ({pnl_percent:.1f}%)")
            
            # Lähetä Telegram ilmoitus
            emoji = "🟢" if pnl_percent > 0 else "🔴"
            message = f"{emoji} *SELL Position Suljettu:*\n💰 {symbol}: ${pnl:.2f} ({pnl_percent:.1f}%)\n📝 Syy: {reason}"
            await self.telegram_bot.send_message(message)
            try:
                from metrics import metrics
                if metrics:
                    metrics.telegram_sent.inc()
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Virhe position sulkemisessa {symbol}: {e}")
            return False
    
    async def _update_position_prices(self, scanner: HybridTokenScanner):
        """Päivitä positionien hinnat ja PnL real-time datalla"""
        # Hae real-time hinnat
        symbols = list(self.portfolio['positions'].keys())
        real_prices = await scanner.get_real_time_prices(symbols)
        
        for symbol, position in self.portfolio['positions'].items():
            # Käytä real-time hintaa jos saatavilla, muuten simuloi
            if symbol in real_prices:
                new_price = real_prices[symbol]
                logger.debug(f"📈 Real-time hinta {symbol}: ${new_price:.6f}")
            else:
                # Simuloi hinnanmuutos (-20% to +30%)
                price_change = random.uniform(-0.2, 0.3)
                new_price = position['entry_price'] * (1 + price_change)
                logger.debug(f"🎲 Simuloitu hinta {symbol}: ${new_price:.6f}")
            
            # Päivitä position tiedot
            position['current_price'] = new_price
            position['pnl'] = (new_price - position['entry_price']) * position['shares']
            position['pnl_percent'] = (new_price - position['entry_price']) / position['entry_price'] * 100
            
            # Päivitä ikä
            if 'entry_time' in position:
                entry_time = datetime.fromisoformat(position['entry_time'])
                age_seconds = (datetime.now() - entry_time).total_seconds()
                position['age_minutes'] = int(age_seconds / 60)
    
    async def _update_performance_metrics(self, scanner: HybridTokenScanner):
        """Päivitä performance metriikat"""
        # Päivitä positionien hinnat ensin
        await self._update_position_prices(scanner)
        
        total_trades = self.performance_metrics['total_trades']
        if total_trades > 0:
            self.performance_metrics['win_rate'] = self.performance_metrics['winning_trades'] / total_trades
        
        # Laske profit factor - PARANNETTU
        if self.performance_metrics['total_trades'] > 0:
            winning_trades = self.performance_metrics['winning_trades']
            losing_trades = self.performance_metrics['losing_trades']
            
            if winning_trades > 0 and losing_trades > 0:
                # Käytä portfolio total PnL:ää profit factor laskentaan
                total_pnl = self.portfolio['total_pnl']
                if total_pnl > 0:
                    self.performance_metrics['profit_factor'] = 1.0 + (total_pnl / 1000)  # Normalisoi
                else:
                    self.performance_metrics['profit_factor'] = 0.5  # Matala mutta ei nolla
            elif winning_trades > 0:
                self.performance_metrics['profit_factor'] = 1.0  # Vain voittavia kauppoja
            else:
                self.performance_metrics['profit_factor'] = 0.0  # Vain tappiollisia kauppoja
        
        # Päivitä portfolio arvo
        total_value = self.portfolio['cash']
        for position in self.portfolio['positions'].values():
            total_value += position['shares'] * position['current_price']
        
        self.portfolio['total_value'] = total_value
        self.portfolio['total_pnl'] = total_value - 10000  # Alkuperäinen $10,000
    
    def _save_analysis_to_file(self, analysis_result: Dict):
        """Tallenna analyysi tiedostoon"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hybrid_trading_analysis_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False, default=self._json_default)
            
            logger.info(f"💾 Hybrid analyysi tulos tallennettu: {filename}")
            
        except Exception as e:
            logger.error(f"Virhe analyysin tallentamisessa: {e}")

    @staticmethod
    def _json_default(obj):
        """JSON-serializer for dataclasses, datetime, sets, etc."""
        try:
            if is_dataclass(obj):
                return asdict(obj)
        except Exception:
            pass
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, set):
            return list(obj)
        return str(obj)
    
    def get_bot_status(self) -> Dict:
        """Hae botin status"""
        return {
            'portfolio': self.portfolio.copy(),
            'performance_metrics': self.performance_metrics.copy(),
            'trading_params': {
                'max_positions': self.max_positions,
                'position_size': self.base_position_size,
                'take_profit': self.take_profit,
                'stop_loss': self.stop_loss,
                'max_age_minutes': self.max_age_minutes
            }
        }

async def main():
    """Pääfunktio joka käynnistää hybrid trading botin jatkuvasti"""
    logger.info("🚀 Käynnistetään Hybrid Trading Bot...")
    
    bot = HybridTradingBot()
    
    # Jatkuva silmukka
    cycle_count = 0
    while True:
        cycle_count += 1
        logger.info(f"🔄 Aloitetaan analyysi sykli #{cycle_count}")
        
        try:
            # Suorita analyysi sykli
            result = await bot.run_analysis_cycle()
            
            logger.info(f"📊 Hybrid Bot Status:")
            logger.info(f"   Tokeneita skannattu: {result.get('tokens_scanned', 0)}")
            logger.info(f"   Signaaleja generoitu: {result.get('signals_generated', 0)}")
            logger.info(f"   Kauppoja suoritettu: {result.get('trades_executed', 0)}")
            logger.info(f"   Portfolio arvo: ${result.get('portfolio_value', 0):.2f}")
            logger.info(f"   Portfolio PnL: ${result.get('portfolio_pnl', 0):.2f}")
            logger.info(f"   Aktiivisia positioita: {result.get('active_positions', 0)}")
            
            # Näytä performance metriikat
            metrics = result.get('performance_metrics', {})
            logger.info(f"📈 Performance:")
            logger.info(f"   Win rate: {metrics.get('win_rate', 0):.1%}")
            logger.info(f"   Total PnL: ${metrics.get('total_pnl', 0):.2f}")
            logger.info(f"   Total trades: {metrics.get('total_trades', 0)}")
            logger.info(f"   Profit factor: {metrics.get('profit_factor', 0):.2f}")
            
        except Exception as e:
            logger.error(f"Virhe analyysi syklissä: {e}")
        
        # Odota 60 sekuntia ennen seuraavaa sykliä
        logger.info("⏰ Odotetaan 60 sekuntia ennen seuraavaa sykliä...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot pysäytetty käyttäjän toimesta")
    except Exception as e:
        print(f"❌ Virhe: {e}")
