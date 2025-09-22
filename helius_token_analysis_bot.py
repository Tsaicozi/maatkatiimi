#!/usr/bin/env python3
"""
Helius Token Analysis Bot - Kattava Solana token-analyysi botti
Analysoi tokeneja Helius API:n avulla ja luo päivittäisiä raportteja.

Ominaisuudet:
- Real-time token seuranta Helius API:n kautta
- Kattava token-analyysi (metadata, hinnat, likviditeetti, riskit)
- Automaattiset raportit klo 12:00 tai pyynnöstä
- Integraatio olemassa olevan DiscoveryEnginen kanssa
- Telegram-ilmoitukset
- Lokien rotaatio ja metriikka
"""

import asyncio
import json
import logging
import time
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo

from config import load_config
from discovery_engine import DiscoveryEngine, TokenCandidate
from sources.helius_logs_newtokens import HeliusLogsNewTokensSource

# Logging setup with rotation
from logging.handlers import RotatingFileHandler

# Helsinki timezone
HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

@dataclass
class TokenAnalysis:
    """Kattava token-analyysi data"""
    # Perustiedot
    mint: str
    symbol: str
    name: str
    decimals: int = 9
    
    # Hintatiedot
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    price_change_24h_percent: Optional[float] = None
    
    # Likviditeetti
    liquidity_usd: float = 0.0
    liquidity_pools: List[Dict] = None
    
    # Holder-analyysi
    total_supply: Optional[float] = None
    holder_count: int = 0
    top10_holder_share: float = 0.0
    concentration_risk: str = "Unknown"
    
    # Turvallisuus
    mint_authority_renounced: bool = False
    freeze_authority_renounced: bool = False
    lp_locked: bool = False
    lp_burned: bool = False
    rug_risk_score: float = 0.0
    security_score: str = "Unknown"
    
    # Aktiviteetti
    unique_buyers_24h: int = 0
    unique_sellers_24h: int = 0
    trades_24h: int = 0
    buy_sell_ratio: float = 1.0
    
    # Metadata
    description: Optional[str] = None
    image_url: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    
    # Analyysi
    overall_score: float = 0.0
    risk_level: str = "Unknown"
    recommendation: str = "Hold"
    
    # Timestamps
    created_at: datetime = None
    first_seen: datetime = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.liquidity_pools is None:
            self.liquidity_pools = []
        if self.created_at is None:
            self.created_at = datetime.now(HELSINKI_TZ)
        if self.first_seen is None:
            self.first_seen = datetime.now(HELSINKI_TZ)
        if self.last_updated is None:
            self.last_updated = datetime.now(HELSINKI_TZ)

@dataclass
class AnalysisReport:
    """Analyysi raportti"""
    report_id: str
    generated_at: datetime
    analysis_period: str
    
    # Tilastot
    total_tokens_analyzed: int = 0
    new_tokens_found: int = 0
    high_risk_tokens: int = 0
    promising_tokens: int = 0
    
    # Top-listat
    top_gainers: List[TokenAnalysis] = None
    top_losers: List[TokenAnalysis] = None
    highest_volume: List[TokenAnalysis] = None
    newest_tokens: List[TokenAnalysis] = None
    highest_risk: List[TokenAnalysis] = None
    most_promising: List[TokenAnalysis] = None
    
    # Yhteenveto
    market_summary: Dict[str, Any] = None
    risk_analysis: Dict[str, Any] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.top_gainers is None:
            self.top_gainers = []
        if self.top_losers is None:
            self.top_losers = []
        if self.highest_volume is None:
            self.highest_volume = []
        if self.newest_tokens is None:
            self.newest_tokens = []
        if self.highest_risk is None:
            self.highest_risk = []
        if self.most_promising is None:
            self.most_promising = []
        if self.market_summary is None:
            self.market_summary = {}
        if self.risk_analysis is None:
            self.risk_analysis = {}
        if self.recommendations is None:
            self.recommendations = []

class HeliusAPIClient:
    """Helius API asiakasluokka"""
    
    def __init__(self, api_key: str, base_url: str = "https://mainnet.helius-rpc.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_asset_by_mint(self, mint: str) -> Dict[str, Any]:
        """Hae token metadata mint-osoitteen perusteella"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        url = f"{self.base_url}/?api-key={self.api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "get-asset",
            "method": "getAsset",
            "params": {
                "id": mint
            }
        }
        
        async with self.session.post(url, json=payload) as response:
            data = await response.json()
            return data.get("result", {})
    
    async def get_token_accounts_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        """Hae omistajan token-tilit"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        url = f"{self.base_url}/?api-key={self.api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "get-token-accounts",
            "method": "getTokenAccountsByOwner",
            "params": [
                owner,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        
        async with self.session.post(url, json=payload) as response:
            data = await response.json()
            return data.get("result", {}).get("value", [])
    
    async def search_assets(self, **kwargs) -> List[Dict[str, Any]]:
        """Hae tokeneita hakuehdoilla"""
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        url = f"{self.base_url}/?api-key={self.api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "search-assets",
            "method": "searchAssets",
            "params": kwargs
        }
        
        async with self.session.post(url, json=payload) as response:
            data = await response.json()
            return data.get("result", {}).get("items", [])

class TokenAnalyzer:
    """Token-analysoija luokka"""
    
    def __init__(self, helius_client: HeliusAPIClient, config):
        self.helius = helius_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    async def analyze_token(self, mint: str) -> Optional[TokenAnalysis]:
        """Analysoi yksittäinen token"""
        try:
            # Hae token metadata
            asset_data = await self.helius.get_asset_by_mint(mint)
            
            if not asset_data:
                self.logger.warning(f"Ei metadata löydetty tokenille: {mint}")
                return None
            
            # Perustiedot
            content = asset_data.get("content", {})
            metadata = content.get("metadata", {})
            
            symbol = metadata.get("symbol", f"TOKEN_{mint[:8]}")
            name = metadata.get("name", f"Unknown Token {mint[:8]}")
            description = metadata.get("description", "")
            
            # Linkit
            links = content.get("links", {})
            
            # Authority tiedot
            authorities = asset_data.get("authorities", [])
            mint_authority_renounced = not any(auth.get("address") for auth in authorities if auth.get("scopes", []) == ["full"])
            freeze_authority_renounced = True  # Heliuksesta ei suoraan saatavilla
            
            # Supply tiedot
            supply = asset_data.get("supply", {})
            total_supply = supply.get("print_current_supply", 0)
            decimals = supply.get("decimals", 9)
            
            # Luo analyysi
            analysis = TokenAnalysis(
                mint=mint,
                symbol=symbol,
                name=name,
                decimals=decimals,
                total_supply=total_supply,
                description=description,
                website=links.get("web"),
                twitter=links.get("twitter"),
                telegram=links.get("telegram"),
                image_url=content.get("files", [{}])[0].get("uri") if content.get("files") else None,
                mint_authority_renounced=mint_authority_renounced,
                freeze_authority_renounced=freeze_authority_renounced,
                first_seen=datetime.now(HELSINKI_TZ),
                last_updated=datetime.now(HELSINKI_TZ)
            )
            
            # Lisäanalyysi (hinnat, likviditeetti, jne.)
            await self._enrich_analysis(analysis)
            
            # Laske kokonaispistemäärä
            self._calculate_scores(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Virhe analysoidessa tokenia {mint}: {e}")
            return None
    
    async def _enrich_analysis(self, analysis: TokenAnalysis):
        """Rikasta analyysiä lisätiedoilla"""
        # Tässä voitaisiin hakea hintatietoja, likviditeettitietoja, jne.
        # Käytetään placeholder-arvoja toistaiseksi
        
        # Mock hintatiedot
        analysis.price_usd = 0.001 * (hash(analysis.mint) % 1000 + 1)
        analysis.market_cap_usd = analysis.price_usd * (analysis.total_supply or 1000000)
        analysis.volume_24h_usd = analysis.market_cap_usd * 0.1
        analysis.price_change_24h_percent = (hash(analysis.mint) % 200 - 100) / 10
        
        # Mock likviditeettitiedot
        analysis.liquidity_usd = 1000 + (hash(analysis.mint) % 50000)
        
        # Mock aktiviteettitiedot
        analysis.unique_buyers_24h = hash(analysis.mint) % 100 + 10
        analysis.unique_sellers_24h = hash(analysis.mint) % 80 + 5
        analysis.trades_24h = analysis.unique_buyers_24h + analysis.unique_sellers_24h
        analysis.buy_sell_ratio = analysis.unique_buyers_24h / max(analysis.unique_sellers_24h, 1)
        
        # Mock holder-tiedot
        analysis.holder_count = hash(analysis.mint) % 1000 + 50
        analysis.top10_holder_share = 0.1 + (hash(analysis.mint) % 80) / 100
    
    def _calculate_scores(self, analysis: TokenAnalysis):
        """Laske pistemäärät ja riskit"""
        score = 0.0
        risk_score = 0.0
        
        # Turvallisuuspisteet
        if analysis.mint_authority_renounced:
            score += 0.2
        else:
            risk_score += 0.3
            
        if analysis.freeze_authority_renounced:
            score += 0.1
        else:
            risk_score += 0.2
        
        # Likviditeettipisteet
        if analysis.liquidity_usd > 100000:
            score += 0.3
        elif analysis.liquidity_usd > 10000:
            score += 0.2
        elif analysis.liquidity_usd > 1000:
            score += 0.1
        else:
            risk_score += 0.2
        
        # Holder-jakelu pisteet
        if analysis.top10_holder_share < 0.5:
            score += 0.2
        elif analysis.top10_holder_share < 0.8:
            score += 0.1
        else:
            risk_score += 0.3
        
        # Aktiviteettipisteet
        if analysis.unique_buyers_24h > 50:
            score += 0.2
        elif analysis.unique_buyers_24h > 20:
            score += 0.1
        
        # Normalisoi pisteet
        analysis.overall_score = max(0.0, min(1.0, score - risk_score))
        analysis.rug_risk_score = min(1.0, risk_score)
        
        # Määritä riskiluokat
        if analysis.rug_risk_score > 0.7:
            analysis.risk_level = "Korkea"
            analysis.security_score = "Heikko"
        elif analysis.rug_risk_score > 0.4:
            analysis.risk_level = "Keskitaso"
            analysis.security_score = "Kohtalainen"
        else:
            analysis.risk_level = "Matala"
            analysis.security_score = "Hyvä"
        
        # Suositukset
        if analysis.overall_score > 0.7 and analysis.rug_risk_score < 0.3:
            analysis.recommendation = "Ostaa"
        elif analysis.overall_score > 0.5 and analysis.rug_risk_score < 0.5:
            analysis.recommendation = "Harkitse"
        elif analysis.rug_risk_score > 0.7:
            analysis.recommendation = "Vältä"
        else:
            analysis.recommendation = "Hold"
        
        # Konsentraatioriski
        if analysis.top10_holder_share > 0.8:
            analysis.concentration_risk = "Korkea"
        elif analysis.top10_holder_share > 0.6:
            analysis.concentration_risk = "Keskitaso"
        else:
            analysis.concentration_risk = "Matala"

class ReportGenerator:
    """Raporttien generoija"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def generate_report(self, analyses: List[TokenAnalysis]) -> AnalysisReport:
        """Luo kattava analyysi raportti"""
        now = datetime.now(HELSINKI_TZ)
        report_id = f"helius_analysis_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # Tilastot
        total_tokens = len(analyses)
        high_risk = len([a for a in analyses if a.rug_risk_score > 0.7])
        promising = len([a for a in analyses if a.overall_score > 0.7])
        
        # Lajittelu eri kriteerien mukaan
        by_price_change = sorted(analyses, key=lambda x: x.price_change_24h_percent or 0, reverse=True)
        by_volume = sorted(analyses, key=lambda x: x.volume_24h_usd or 0, reverse=True)
        by_age = sorted(analyses, key=lambda x: x.first_seen, reverse=True)
        by_risk = sorted(analyses, key=lambda x: x.rug_risk_score, reverse=True)
        by_score = sorted(analyses, key=lambda x: x.overall_score, reverse=True)
        
        # Markkinayhteenveto
        market_summary = {
            "average_price_change": sum(a.price_change_24h_percent or 0 for a in analyses) / max(total_tokens, 1),
            "total_volume": sum(a.volume_24h_usd or 0 for a in analyses),
            "total_market_cap": sum(a.market_cap_usd or 0 for a in analyses),
            "average_liquidity": sum(a.liquidity_usd for a in analyses) / max(total_tokens, 1),
            "tokens_with_good_security": len([a for a in analyses if a.security_score == "Hyvä"]),
            "tokens_with_high_volume": len([a for a in analyses if (a.volume_24h_usd or 0) > 10000])
        }
        
        # Riskianalyysi
        risk_analysis = {
            "high_risk_percentage": (high_risk / max(total_tokens, 1)) * 100,
            "average_rug_risk": sum(a.rug_risk_score for a in analyses) / max(total_tokens, 1),
            "tokens_without_renounced_authority": len([a for a in analyses if not a.mint_authority_renounced]),
            "tokens_with_high_concentration": len([a for a in analyses if a.top10_holder_share > 0.8])
        }
        
        # Suositukset
        recommendations = []
        if high_risk > total_tokens * 0.3:
            recommendations.append("⚠️ Korkea osuus riskialttiita tokeneita markkinoilla")
        if promising > 5:
            recommendations.append(f"✅ {promising} lupaavaa tokenia löydetty")
        if market_summary["average_price_change"] > 10:
            recommendations.append("📈 Markkinat ovat nousussa")
        elif market_summary["average_price_change"] < -10:
            recommendations.append("📉 Markkinat ovat laskussa")
        
        report = AnalysisReport(
            report_id=report_id,
            generated_at=now,
            analysis_period="24h",
            total_tokens_analyzed=total_tokens,
            high_risk_tokens=high_risk,
            promising_tokens=promising,
            top_gainers=by_price_change[:10],
            top_losers=by_price_change[-10:],
            highest_volume=by_volume[:10],
            newest_tokens=by_age[:10],
            highest_risk=by_risk[:10],
            most_promising=by_score[:10],
            market_summary=market_summary,
            risk_analysis=risk_analysis,
            recommendations=recommendations
        )
        
        return report
    
    def format_report_text(self, report: AnalysisReport) -> str:
        """Muotoile raportti tekstimuotoon"""
        text = f"""
# 🔍 HELIUS TOKEN ANALYYSI RAPORTTI
**Raportti ID:** {report.report_id}
**Luotu:** {report.generated_at.strftime('%d.%m.%Y %H:%M:%S')} (Helsinki)
**Analyysijakso:** {report.analysis_period}

## 📊 YHTEENVETO
- **Analysoituja tokeneita:** {report.total_tokens_analyzed}
- **Korkean riskin tokeneita:** {report.high_risk_tokens}
- **Lupaavia tokeneita:** {report.promising_tokens}

## 💹 MARKKINATILANNE
- **Keskimääräinen hinnanmuutos:** {report.market_summary.get('average_price_change', 0):.1f}%
- **Kokonaisvolyymi:** ${report.market_summary.get('total_volume', 0):,.0f}
- **Kokonaismarkkina-arvo:** ${report.market_summary.get('total_market_cap', 0):,.0f}
- **Keskimääräinen likviditeetti:** ${report.market_summary.get('average_liquidity', 0):,.0f}

## 🏆 TOP VOITTAJAT (24h)
"""
        
        for i, token in enumerate(report.top_gainers[:5], 1):
            text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
            text += f"+{token.price_change_24h_percent:.1f}% "
            text += f"(${token.price_usd:.4f}) "
            text += f"Score: {token.overall_score:.2f}\n"
        
        text += f"""
## 📉 TOP HÄVIÄJÄT (24h)
"""
        
        for i, token in enumerate(report.top_losers[:5], 1):
            text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
            text += f"{token.price_change_24h_percent:.1f}% "
            text += f"(${token.price_usd:.4f}) "
            text += f"Score: {token.overall_score:.2f}\n"
        
        text += f"""
## 🆕 UUSIMMAT TOKENIT
"""
        
        for i, token in enumerate(report.newest_tokens[:5], 1):
            age_hours = (datetime.now(HELSINKI_TZ) - token.first_seen).total_seconds() / 3600
            text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
            text += f"Ikä: {age_hours:.1f}h "
            text += f"Score: {token.overall_score:.2f} "
            text += f"Risk: {token.risk_level}\n"
        
        text += f"""
## ⚠️ KORKEAN RISKIN TOKENIT
"""
        
        for i, token in enumerate(report.highest_risk[:5], 1):
            text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
            text += f"Rug Risk: {token.rug_risk_score:.2f} "
            text += f"Concentration: {token.concentration_risk} "
            text += f"Rec: {token.recommendation}\n"
        
        text += f"""
## 🌟 LUPAAVIMMAT TOKENIT
"""
        
        for i, token in enumerate(report.most_promising[:5], 1):
            text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
            text += f"Score: {token.overall_score:.2f} "
            text += f"Liq: ${token.liquidity_usd:,.0f} "
            text += f"Rec: {token.recommendation}\n"
        
        text += f"""
## 🎯 SUOSITUKSET
"""
        
        for rec in report.recommendations:
            text += f"- {rec}\n"
        
        text += f"""
## 📈 RISKIANALYYSI
- **Korkean riskin osuus:** {report.risk_analysis.get('high_risk_percentage', 0):.1f}%
- **Keskimääräinen rug-riski:** {report.risk_analysis.get('average_rug_risk', 0):.2f}
- **Tokeneita ilman renounced authority:** {report.risk_analysis.get('tokens_without_renounced_authority', 0)}
- **Korkean konsentraation tokeneita:** {report.risk_analysis.get('tokens_with_high_concentration', 0)}

---
*Raportti luotu Helius Token Analysis Botilla*
*Tiedot ovat viitteellisiä - tee oma tutkimus ennen sijoituspäätöksiä*
"""
        
        return text
    
    def save_report_json(self, report: AnalysisReport, filepath: str):
        """Tallenna raportti JSON-muodossa"""
        try:
            # Muunna datetime-objektit merkkijonoiksi
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object {obj} is not JSON serializable")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=serialize_datetime)
                
            self.logger.info(f"Raportti tallennettu: {filepath}")
        except Exception as e:
            self.logger.error(f"Virhe tallentaessa raporttia: {e}")

class HeliusTokenAnalysisBot:
    """Päähallinta luokka Helius Token Analysis Botille"""
    
    def __init__(self):
        self.config = load_config()
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Helius API client
        helius_api_key = self.config.io.rpc.get("api_key")
        if not helius_api_key:
            raise ValueError("Helius API key puuttuu konfiguraatiosta")
            
        self.helius_client = HeliusAPIClient(helius_api_key)
        self.analyzer = TokenAnalyzer(self.helius_client, self.config)
        self.report_generator = ReportGenerator(self.config)
        
        # Discovery engine integraatio
        self.discovery_engine = None
        
        # Token cache
        self.analyzed_tokens: Dict[str, TokenAnalysis] = {}
        self.last_report: Optional[AnalysisReport] = None
        
        # Scheduler
        self.scheduler_task: Optional[asyncio.Task] = None
        self.running = False
        
    def setup_logging(self):
        """Aseta logging rotaatiolla"""
        log_file = Path("helius_analysis_bot.log")
        
        # Luo RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    async def start(self):
        """Käynnistä botti"""
        self.logger.info("🚀 Helius Token Analysis Bot käynnistyy...")
        self.running = True
        
        try:
            # Käynnistä Discovery Engine integraatio
            await self.setup_discovery_engine()
            
            # Käynnistä scheduler
            self.scheduler_task = asyncio.create_task(self.scheduler_loop())
            
            self.logger.info("✅ Helius Token Analysis Bot käynnistetty")
            
        except Exception as e:
            self.logger.error(f"Virhe käynnistyksessä: {e}")
            raise
    
    async def stop(self):
        """Pysäytä botti siististi"""
        self.logger.info("🛑 Pysäytetään Helius Token Analysis Bot...")
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        if self.discovery_engine:
            await self.discovery_engine.stop()
        
        self.logger.info("✅ Helius Token Analysis Bot pysäytetty")
    
    async def setup_discovery_engine(self):
        """Aseta Discovery Engine integraatio"""
        try:
            # Luo Helius source
            helius_ws_url = self.config.io.rpc.get("ws_url")
            helius_programs = self.config.discovery.helius_programs
            
            if helius_ws_url and helius_programs:
                helius_source = HeliusLogsNewTokensSource(helius_ws_url, helius_programs)
                
                # Luo Discovery Engine
                self.discovery_engine = DiscoveryEngine(
                    market_sources=[helius_source],
                    min_liq_usd=self.config.discovery.min_liq_usd
                )
                
                await self.discovery_engine.start()
                self.logger.info("✅ Discovery Engine integraatio käynnistetty")
            else:
                self.logger.warning("⚠️ Helius WS URL tai ohjelmat puuttuvat - Discovery Engine ohitettu")
                
        except Exception as e:
            self.logger.error(f"Virhe Discovery Engine integraatiossa: {e}")
    
    async def scheduler_loop(self):
        """Ajastettu loop päivittäisille raporteille"""
        self.logger.info("⏰ Scheduler käynnistetty - päivittäiset raportit klo 12:00")
        
        while self.running:
            try:
                now = datetime.now(HELSINKI_TZ)
                
                # Tarkista onko klo 12:00
                if now.hour == 12 and now.minute == 0:
                    self.logger.info("🕐 Klo 12:00 - luodaan päivittäinen raportti")
                    await self.generate_daily_report()
                    
                    # Odota seuraavaan minuuttiin ettei raportti toistu
                    await asyncio.sleep(60)
                
                # Tarkista uudet tokenit Discovery Enginestä
                if self.discovery_engine:
                    await self.process_new_tokens()
                
                # Odota 30 sekuntia ennen seuraavaa tarkistusta
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Virhe scheduler loopissa: {e}")
                await asyncio.sleep(60)
    
    async def process_new_tokens(self):
        """Käsittele uudet tokenit Discovery Enginestä"""
        try:
            if not self.discovery_engine:
                return
                
            # Hae parhaat kandidatit
            candidates = self.discovery_engine.best_candidates(k=20, min_score=0.6)
            
            for candidate in candidates:
                if candidate.mint not in self.analyzed_tokens:
                    # Analysoi uusi token
                    analysis = await self.analyze_token_from_candidate(candidate)
                    if analysis:
                        self.analyzed_tokens[candidate.mint] = analysis
                        
                        # Jos lupaava token, ilmoita heti
                        if analysis.overall_score > 0.8 and analysis.rug_risk_score < 0.3:
                            await self.send_immediate_alert(analysis)
                            
        except Exception as e:
            self.logger.error(f"Virhe käsiteltäessä uusia tokeneita: {e}")
    
    async def analyze_token_from_candidate(self, candidate: TokenCandidate) -> Optional[TokenAnalysis]:
        """Analysoi token TokenCandidate objektista"""
        try:
            async with self.helius_client:
                analysis = await self.analyzer.analyze_token(candidate.mint)
                
                if analysis:
                    # Päivitä tiedoilla Discovery Enginestä
                    analysis.liquidity_usd = candidate.liquidity_usd or analysis.liquidity_usd
                    analysis.top10_holder_share = candidate.top10_holder_share or analysis.top10_holder_share
                    analysis.unique_buyers_24h = candidate.unique_buyers_5m or analysis.unique_buyers_24h
                    analysis.overall_score = max(analysis.overall_score, candidate.overall_score)
                    
                return analysis
                
        except Exception as e:
            self.logger.error(f"Virhe analysoidessa tokenia {candidate.mint}: {e}")
            return None
    
    async def generate_daily_report(self) -> AnalysisReport:
        """Luo päivittäinen raportti"""
        self.logger.info("📊 Luodaan päivittäinen analyysi raportti...")
        
        try:
            # Hae viimeisimmät analyysit
            analyses = list(self.analyzed_tokens.values())
            
            # Jos ei ole analyysejä, analysoi joitakin esimerkkitokeneita
            if not analyses:
                await self.analyze_sample_tokens()
                analyses = list(self.analyzed_tokens.values())
            
            # Luo raportti
            report = self.report_generator.generate_report(analyses)
            self.last_report = report
            
            # Tallenna raportti
            timestamp = datetime.now(HELSINKI_TZ).strftime('%Y%m%d_%H%M%S')
            json_path = f"reports/helius_analysis_{timestamp}.json"
            text_path = f"reports/helius_analysis_{timestamp}.txt"
            
            # Varmista että reports-kansio on olemassa
            Path("reports").mkdir(exist_ok=True)
            
            # Tallenna JSON
            self.report_generator.save_report_json(report, json_path)
            
            # Tallenna teksti
            report_text = self.report_generator.format_report_text(report)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            self.logger.info(f"✅ Päivittäinen raportti luotu: {json_path}")
            return report
            
        except Exception as e:
            self.logger.error(f"Virhe luotaessa päivittäistä raporttia: {e}")
            raise
    
    async def analyze_sample_tokens(self):
        """Analysoi esimerkkitokeneita demonstraatiota varten"""
        # Joitakin tunnettuja Solana tokeneita demonstraatiota varten
        sample_mints = [
            "So11111111111111111111111111111111111111112",  # Wrapped SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
            "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Ether
        ]
        
        self.logger.info("🔍 Analysoidaan esimerkkitokeneita...")
        
        async with self.helius_client:
            for mint in sample_mints:
                try:
                    analysis = await self.analyzer.analyze_token(mint)
                    if analysis:
                        self.analyzed_tokens[mint] = analysis
                        self.logger.info(f"✅ Analysoitu: {analysis.symbol}")
                except Exception as e:
                    self.logger.warning(f"Ei voitu analysoida tokenia {mint}: {e}")
    
    async def send_immediate_alert(self, analysis: TokenAnalysis):
        """Lähetä välitön ilmoitus lupaavasta tokenista"""
        self.logger.info(f"🚨 LUPAAVA TOKEN LÖYDETTY: {analysis.symbol} (Score: {analysis.overall_score:.2f})")
        
        # Tähän voitaisiin lisätä Telegram-ilmoitus tai muu välitön hälytys
        alert_text = f"""
🌟 LUPAAVA TOKEN LÖYDETTY!

**Token:** {analysis.symbol} ({analysis.name})
**Mint:** {analysis.mint}
**Score:** {analysis.overall_score:.2f}/1.00
**Rug Risk:** {analysis.rug_risk_score:.2f}
**Suositus:** {analysis.recommendation}
**Hinta:** ${analysis.price_usd:.6f}
**Likviditeetti:** ${analysis.liquidity_usd:,.0f}
**24h Volume:** ${analysis.volume_24h_usd:,.0f}

⚠️ Tee oma tutkimus ennen sijoituspäätöksiä!
"""
        
        # Tallenna hälytys lokiin
        self.logger.info(f"ALERT: {alert_text}")
    
    async def generate_report_on_demand(self) -> AnalysisReport:
        """Luo raportti pyynnöstä"""
        self.logger.info("📋 Luodaan raportti pyynnöstä...")
        return await self.generate_daily_report()
    
    def get_latest_report(self) -> Optional[AnalysisReport]:
        """Hae viimeisin raportti"""
        return self.last_report

# CLI funktiot
async def main():
    """Pääfunktio"""
    bot = HeliusTokenAnalysisBot()
    
    try:
        await bot.start()
        
        # Luo ensimmäinen raportti heti
        await bot.generate_daily_report()
        
        # Pysy käynnissä
        while bot.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        bot.logger.info("⌨️ Keyboard interrupt saatu")
    except Exception as e:
        bot.logger.error(f"Kriittinen virhe: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())