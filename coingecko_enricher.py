"""
CoinGecko Enricher - Tehokas CoinGecko integraatio
Toteuttaa symbolin varmistuksen, metadata-rikastuksen ja scoring-bonukset
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any, Tuple
import aiohttp
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

@dataclass
class CoinGeckoTokenData:
    """CoinGecko token data structure"""
    # Basic info
    cg_id: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    logo_url: Optional[str] = None
    
    # Market data
    current_price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    ath_usd: Optional[float] = None
    ath_change_percentage: Optional[float] = None
    
    # Social & links
    homepage_url: Optional[str] = None
    twitter_url: Optional[str] = None
    discord_url: Optional[str] = None
    
    # Trading data
    dex_tickers_count: int = 0
    dex_volume_24h_usd: float = 0.0
    
    # Status flags
    is_trending: bool = False
    is_recently_added: bool = False
    is_bluechip: bool = False
    
    # Metadata
    categories: List[str] = field(default_factory=list)
    description: Optional[str] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(ZoneInfo("Europe/Helsinki")))

@dataclass
class CoinGeckoScore:
    """CoinGecko scoring results"""
    symbol_resolution_bonus: int = 0  # +10 if CG confirms symbol, -10 if impersonation
    confluence_bonus: int = 0  # +5 if found in both CG and other sources
    trending_bonus: int = 0  # +5 if trending
    recently_added_bonus: int = 0  # +5 if recently added
    tradability_bonus: int = 0  # +5-10 based on DEX tickers
    social_bonus: int = 0  # +2-5 for official links
    market_health_bonus: int = 0  # +0-10 based on ecosystem volume
    total_score: int = 0
    
    # Confidence indicators
    has_official_symbol: bool = False
    has_social_links: bool = False
    has_dex_trading: bool = False
    is_verified_project: bool = False

class CoinGeckoEnricher:
    """CoinGecko enrichment engine"""
    
    def __init__(self, api_key: str, cache_ttl_minutes: int = 120):
        self.api_key = api_key
        self.base_url = "https://pro-api.coingecko.com/api/v3"
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        
        # Caches
        self._contract_cache: Dict[str, Tuple[CoinGeckoTokenData, datetime]] = {}
        self._trending_cache: Tuple[List[str], datetime] = ([], datetime.min)
        self._recently_added_cache: Tuple[List[str], datetime] = ([], datetime.min)
        self._bluechip_cache: Set[str] = set()
        self._platform_mapping_cache: Dict[str, str] = {}
        
        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests
        
        # Session
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10.0),
            headers={
                "accept": "application/json",
                "x-cg-pro-api-key": self.api_key
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    async def _get_json(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make rate-limited API request"""
        await self._rate_limit()
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("CoinGecko rate limit hit, waiting...")
                    await asyncio.sleep(1.0)
                    return await self._get_json(url, params)
                
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"CoinGecko API error for {url}: {e}")
            return {}
    
    async def enrich_token(self, mint: str, existing_data: Optional[Dict] = None) -> Tuple[CoinGeckoTokenData, CoinGeckoScore]:
        """
        Main enrichment method - resolves symbol and enriches metadata
        """
        # Check cache first
        if mint in self._contract_cache:
            data, timestamp = self._contract_cache[mint]
            if datetime.now() - timestamp < self.cache_ttl:
                score = await self._calculate_score(data, existing_data)
                return data, score
        
        # Fetch from CoinGecko
        token_data = await self._fetch_contract_data(mint)
        if token_data:
            self._contract_cache[mint] = (token_data, datetime.now())
        
        # Calculate scoring
        score = await self._calculate_score(token_data, existing_data)
        
        return token_data, score
    
    async def _fetch_contract_data(self, mint: str) -> Optional[CoinGeckoTokenData]:
        """Fetch token data from CoinGecko contract endpoint"""
        url = f"{self.base_url}/coins/solana/contract/{mint}"
        
        try:
            data = await self._get_json(url)
            if not data or data.get("error"):
                return None
            
            token_data = CoinGeckoTokenData()
            
            # Basic info
            token_data.cg_id = data.get("id")
            token_data.name = data.get("name")
            token_data.symbol = data.get("symbol", "").upper()
            token_data.logo_url = data.get("image", {}).get("small")
            
            # Market data
            market_data = data.get("market_data", {})
            token_data.current_price_usd = market_data.get("current_price", {}).get("usd")
            token_data.market_cap_usd = market_data.get("market_cap", {}).get("usd")
            token_data.volume_24h_usd = market_data.get("total_volume", {}).get("usd")
            token_data.ath_usd = market_data.get("ath", {}).get("usd")
            token_data.ath_change_percentage = market_data.get("ath_change_percentage", {}).get("usd")
            
            # Social links
            links = data.get("links", {})
            token_data.homepage_url = links.get("homepage", [None])[0] if links.get("homepage") else None
            token_data.twitter_url = links.get("twitter_screen_name")
            if token_data.twitter_url:
                token_data.twitter_url = f"https://twitter.com/{token_data.twitter_url}"
            token_data.discord_url = links.get("chat_url", [None])[0] if links.get("chat_url") else None
            
            # Categories
            token_data.categories = data.get("categories", [])
            
            # Description
            token_data.description = data.get("description", {}).get("en", "")
            
            # Check if trending/recently added
            await self._update_status_flags(token_data)
            
            # Fetch tickers for tradability analysis
            if token_data.cg_id:
                await self._fetch_tickers_data(token_data)
            
            return token_data
            
        except Exception as e:
            logger.error(f"Error fetching CoinGecko contract data for {mint}: {e}")
            return None
    
    async def _update_status_flags(self, token_data: CoinGeckoTokenData):
        """Update trending, recently added, and bluechip flags"""
        if not token_data.cg_id:
            return
        
        # Update caches if needed
        await self._update_trending_cache()
        await self._update_recently_added_cache()
        await self._update_bluechip_cache()
        
        # Check flags
        token_data.is_trending = token_data.cg_id in self._trending_cache[0]
        token_data.is_recently_added = token_data.cg_id in self._recently_added_cache[0]
        token_data.is_bluechip = token_data.cg_id in self._bluechip_cache
    
    async def _fetch_tickers_data(self, token_data: CoinGeckoTokenData):
        """Fetch tickers data for tradability analysis"""
        if not token_data.cg_id:
            return
        
        url = f"{self.base_url}/coins/{token_data.cg_id}/tickers"
        
        try:
            data = await self._get_json(url)
            if not data or "tickers" not in data:
                return
            
            tickers = data["tickers"]
            dex_tickers = [t for t in tickers if t.get("market", {}).get("type") == "dex"]
            
            token_data.dex_tickers_count = len(dex_tickers)
            token_data.dex_volume_24h_usd = sum(
                float(t.get("volume", 0)) for t in dex_tickers
            )
            
        except Exception as e:
            logger.error(f"Error fetching tickers for {token_data.cg_id}: {e}")
    
    async def _update_trending_cache(self):
        """Update trending coins cache"""
        if datetime.now() - self._trending_cache[1] < timedelta(minutes=30):
            return
        
        try:
            url = f"{self.base_url}/search/trending"
            data = await self._get_json(url)
            
            if data and "coins" in data:
                trending_ids = [coin["item"]["id"] for coin in data["coins"]]
                self._trending_cache = (trending_ids, datetime.now())
                logger.info(f"Updated trending cache: {len(trending_ids)} coins")
        except Exception as e:
            logger.error(f"Error updating trending cache: {e}")
    
    async def _update_recently_added_cache(self):
        """Update recently added coins cache"""
        if datetime.now() - self._recently_added_cache[1] < timedelta(hours=1):
            return
        
        try:
            url = f"{self.base_url}/coins/list/new"
            data = await self._get_json(url)
            
            if data:
                # Filter for Solana platform coins
                solana_coins = []
                for coin in data:
                    platforms = coin.get("platforms", {})
                    if "solana" in platforms:
                        solana_coins.append(coin["id"])
                
                self._recently_added_cache = (solana_coins, datetime.now())
                logger.info(f"Updated recently added cache: {len(solana_coins)} Solana coins")
        except Exception as e:
            logger.error(f"Error updating recently added cache: {e}")
    
    async def _update_bluechip_cache(self):
        """Update bluechip coins cache"""
        if self._bluechip_cache:
            return  # Only update once per session
        
        try:
            # Known bluechip Solana tokens
            bluechip_mints = {
                "So11111111111111111111111111111111111111112",  # SOL
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
                "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # ETH
            }
            
            # Map mints to CG IDs
            for mint in bluechip_mints:
                url = f"{self.base_url}/coins/solana/contract/{mint}"
                data = await self._get_json(url)
                if data and "id" in data:
                    self._bluechip_cache.add(data["id"])
            
            logger.info(f"Updated bluechip cache: {len(self._bluechip_cache)} coins")
        except Exception as e:
            logger.error(f"Error updating bluechip cache: {e}")
    
    async def _calculate_score(self, token_data: Optional[CoinGeckoTokenData], existing_data: Optional[Dict]) -> CoinGeckoScore:
        """Calculate CoinGecko scoring bonuses"""
        score = CoinGeckoScore()
        
        if not token_data:
            return score
        
        # 1. Symbol resolution bonus
        if token_data.symbol and token_data.name:
            score.symbol_resolution_bonus = 10
            score.has_official_symbol = True
            score.is_verified_project = True
        
        # 2. Confluence bonus (if found in other sources too)
        if existing_data and existing_data.get("dex_status") == "ok":
            score.confluence_bonus = 5
        
        # 3. Trending bonus
        if token_data.is_trending:
            score.trending_bonus = 5
        
        # 4. Recently added bonus
        if token_data.is_recently_added:
            score.recently_added_bonus = 5
        
        # 5. Tradability bonus
        if token_data.dex_tickers_count > 0:
            score.tradability_bonus = 5
            score.has_dex_trading = True
            
            if token_data.dex_volume_24h_usd >= 10000:
                score.tradability_bonus = 10
        
        # 6. Social bonus
        social_links = sum([
            bool(token_data.homepage_url),
            bool(token_data.twitter_url),
            bool(token_data.discord_url)
        ])
        
        if social_links >= 2:
            score.social_bonus = 5
            score.has_social_links = True
        elif social_links == 1:
            score.social_bonus = 2
        
        # Calculate total
        score.total_score = (
            score.symbol_resolution_bonus +
            score.confluence_bonus +
            score.trending_bonus +
            score.recently_added_bonus +
            score.tradability_bonus +
            score.social_bonus +
            score.market_health_bonus
        )
        
        return score
    
    async def get_recently_added_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently added Solana coins for lookback sweep"""
        await self._update_recently_added_cache()
        
        recently_added = []
        for cg_id in self._recently_added_cache[0][:limit]:
            # Try to get mint address from platform data
            try:
                url = f"{self.base_url}/coins/{cg_id}"
                data = await self._get_json(url)
                
                if data and "platforms" in data:
                    platforms = data["platforms"]
                    if "solana" in platforms:
                        mint = platforms["solana"]
                        recently_added.append({
                            "mint": mint,
                            "cg_id": cg_id,
                            "name": data.get("name"),
                            "symbol": data.get("symbol", "").upper(),
                            "source": "coingecko_recently_added"
                        })
            except Exception as e:
                logger.error(f"Error getting mint for {cg_id}: {e}")
                continue
        
        return recently_added

# Global instance
_coingecko_enricher: Optional[CoinGeckoEnricher] = None

async def get_coingecko_enricher() -> CoinGeckoEnricher:
    """Get global CoinGecko enricher instance"""
    global _coingecko_enricher
    
    if _coingecko_enricher is None:
        api_key = os.getenv("COINGECKO_API_KEY")
        if not api_key:
            raise ValueError("COINGECKO_API_KEY not found in environment")
        
        _coingecko_enricher = CoinGeckoEnricher(api_key)
        await _coingecko_enricher.__aenter__()
    
    return _coingecko_enricher

async def enrich_token_with_coingecko(mint: str, existing_data: Optional[Dict] = None) -> Tuple[Optional[CoinGeckoTokenData], CoinGeckoScore]:
    """Convenience function for token enrichment"""
    try:
        enricher = await get_coingecko_enricher()
        return await enricher.enrich_token(mint, existing_data)
    except Exception as e:
        logger.error(f"Error enriching token {mint} with CoinGecko: {e}")
        return None, CoinGeckoScore()
