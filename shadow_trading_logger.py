"""
Shadow Trading Logger - Dataset keruu
Kerää dataa hot-kandidateista ja niiden toteutuneista tuotoista
"""

import asyncio
import csv
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ShadowTradeRecord:
    """Shadow trade -tietue"""
    timestamp: float
    mint: str
    symbol: str
    score: float
    novelty: float
    buyers_5m: int
    buy_ratio: float
    liq_usd: float
    top10_share: float
    rug_risk: float
    price_at_signal: Optional[float] = None
    price_5m: Optional[float] = None
    price_15m: Optional[float] = None
    price_60m: Optional[float] = None
    return_5m: Optional[float] = None
    return_15m: Optional[float] = None
    return_60m: Optional[float] = None

class ShadowTradingLogger:
    """Shadow trading -loggeri dataset keruulle"""
    
    def __init__(self, db_path: str = "shadow_trades.db"):
        self.db_path = db_path
        self.csv_path = "shadow_trades.csv"
        self.pending_trades: Dict[str, ShadowTradeRecord] = {}
        self.price_cache: Dict[str, Dict[str, float]] = {}  # mint -> {timestamp: price}
        
        # Alusta tietokanta
        self._init_database()
        
        # Alusta CSV
        self._init_csv()
        
        logger.info(f"✅ Shadow trading logger alustettu: {db_path}")
    
    def _init_database(self):
        """Alusta SQLite tietokanta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shadow_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                mint TEXT,
                symbol TEXT,
                score REAL,
                novelty REAL,
                buyers_5m INTEGER,
                buy_ratio REAL,
                liq_usd REAL,
                top10_share REAL,
                rug_risk REAL,
                price_at_signal REAL,
                price_5m REAL,
                price_15m REAL,
                price_60m REAL,
                return_5m REAL,
                return_15m REAL,
                return_60m REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indeksit
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mint ON shadow_trades(mint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON shadow_trades(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _init_csv(self):
        """Alusta CSV tiedosto"""
        if not Path(self.csv_path).exists():
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'mint', 'symbol', 'score', 'novelty', 'buyers_5m', 
                    'buy_ratio', 'liq_usd', 'top10_share', 'rug_risk',
                    'price_at_signal', 'price_5m', 'price_15m', 'price_60m',
                    'return_5m', 'return_15m', 'return_60m'
                ])
    
    def log_hot_candidate(self, candidate) -> None:
        """Kirjaa hot-kandidatin shadow trade -tietueeksi"""
        try:
            record = ShadowTradeRecord(
                timestamp=time.time(),
                mint=getattr(candidate, 'mint', 'unknown'),
                symbol=getattr(candidate, 'symbol', 'unknown'),
                score=getattr(candidate, 'overall_score', 0.0),
                novelty=getattr(candidate, 'novelty_score', 0.0),
                buyers_5m=getattr(candidate, 'unique_buyers_5m', 0),
                buy_ratio=getattr(candidate, 'buy_sell_ratio', 1.0),
                liq_usd=getattr(candidate, 'liquidity_usd', 0.0),
                top10_share=getattr(candidate, 'top10_holder_share', 0.0),
                rug_risk=getattr(candidate, 'rug_risk_score', 0.0)
            )
            
            self.pending_trades[record.mint] = record
            logger.info(f"📊 Shadow trade kirjattu: {record.symbol} (score: {record.score:.2f})")
            
        except Exception as e:
            logger.error(f"Virhe kirjattaessa shadow trade: {e}")
    
    async def _fetch_price(self, mint: str) -> Optional[float]:
        """Hae tokenin hinta Jupiter API:sta"""
        try:
            # Mock hinta - korvaa oikealla Jupiter API:lla
            import random
            return random.uniform(0.001, 10.0)
        except Exception as e:
            logger.debug(f"Virhe haettaessa hintaa {mint}: {e}")
            return None
    
    async def _update_pending_trades(self):
        """Päivitä odottavat shadow trades"""
        current_time = time.time()
        
        for mint, record in list(self.pending_trades.items()):
            try:
                # Tarkista onko aika päivittää hintoja
                time_since_signal = current_time - record.timestamp
                
                if time_since_signal >= 60 and record.price_5m is None:  # 1 min
                    price = await self._fetch_price(mint)
                    if price:
                        record.price_5m = price
                        if record.price_at_signal:
                            record.return_5m = (price - record.price_at_signal) / record.price_at_signal
                
                elif time_since_signal >= 900 and record.price_15m is None:  # 15 min
                    price = await self._fetch_price(mint)
                    if price:
                        record.price_15m = price
                        if record.price_at_signal:
                            record.return_15m = (price - record.price_at_signal) / record.price_at_signal
                
                elif time_since_signal >= 3600 and record.price_60m is None:  # 60 min
                    price = await self._fetch_price(mint)
                    if price:
                        record.price_60m = price
                        if record.price_at_signal:
                            record.return_60m = (price - record.price_at_signal) / record.price_at_signal
                        
                        # Valmis - tallenna ja poista
                        await self._save_record(record)
                        del self.pending_trades[mint]
                
            except Exception as e:
                logger.error(f"Virhe päivittäessä shadow trade {mint}: {e}")
    
    async def _save_record(self, record: ShadowTradeRecord):
        """Tallenna shadow trade -tietue"""
        try:
            # SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO shadow_trades 
                (timestamp, mint, symbol, score, novelty, buyers_5m, buy_ratio, 
                 liq_usd, top10_share, rug_risk, price_at_signal, price_5m, 
                 price_15m, price_60m, return_5m, return_15m, return_60m)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp, record.mint, record.symbol, record.score,
                record.novelty, record.buyers_5m, record.buy_ratio,
                record.liq_usd, record.top10_share, record.rug_risk,
                record.price_at_signal, record.price_5m, record.price_15m,
                record.price_60m, record.return_5m, record.return_15m, record.return_60m
            ))
            
            conn.commit()
            conn.close()
            
            # CSV
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    record.timestamp, record.mint, record.symbol, record.score,
                    record.novelty, record.buyers_5m, record.buy_ratio,
                    record.liq_usd, record.top10_share, record.rug_risk,
                    record.price_at_signal, record.price_5m, record.price_15m,
                    record.price_60m, record.return_5m, record.return_15m, record.return_60m
                ])
            
            logger.info(f"💾 Shadow trade tallennettu: {record.symbol}")
            
        except Exception as e:
            logger.error(f"Virhe tallentaessa shadow trade: {e}")
    
    async def start_background_task(self):
        """Käynnistä taustatehtävä"""
        while True:
            try:
                await self._update_pending_trades()
                await asyncio.sleep(30)  # Päivitä 30s välein
            except Exception as e:
                logger.error(f"Virhe shadow trading taustatehtävässä: {e}")
                await asyncio.sleep(60)

# Global instance
shadow_logger = ShadowTradingLogger()
