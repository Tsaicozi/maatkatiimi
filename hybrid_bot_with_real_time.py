#!/usr/bin/env python3
"""
Hybrid Trading Bot - With Real Time Integration
Integroitu real-time token skanneri pääbottiin
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from hybrid_bot_real_time import RealTimeTokenScanner, RealTimeToken

class HybridBotWithRealTime:
    """Hybrid trading bot real-time integraatiolla"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scanner = RealTimeTokenScanner()
        
        # Bot stats
        self.cycle_count = 0
        self.total_tokens_scanned = 0
        self.total_signals_generated = 0
        self.total_trades_executed = 0
        self.portfolio_value = 10000.0
        self.portfolio_pnl = 0.0

    async def run_real_time_cycle(self):
        """Suorita real-time analyysi sykli"""
        self.cycle_count += 1
        self.logger.info(f"🔄 Aloitetaan REAL-TIME analyysi sykli #{self.cycle_count}")
        
        try:
            # 1. Skannaa real-time tokeneita
            async with self.scanner as scanner:
                real_time_tokens = await scanner.scan_real_time_tokens()
                self.total_tokens_scanned += len(real_time_tokens)
            
            # 2. Generoi trading signaalit
            signals = self._generate_real_time_signals(real_time_tokens)
            self.total_signals_generated += len(signals)
            
            # 3. Simuloi kauppojen suorittaminen
            trades_executed = await self._simulate_real_time_trading(signals)
            self.total_trades_executed += trades_executed
            
            # 4. Tulosta raportti
            await self._print_real_time_report(real_time_tokens, signals, trades_executed)
            
            return {
                "cycle_number": self.cycle_count,
                "tokens_scanned": len(real_time_tokens),
                "signals_generated": len(signals),
                "trades_executed": trades_executed,
                "portfolio_value": self.portfolio_value,
                "portfolio_pnl": self.portfolio_pnl
            }
            
        except Exception as e:
            self.logger.error(f"❌ Virhe real-time syklissä: {e}")
            return {"error": str(e)}

    def _generate_real_time_signals(self, tokens: List[RealTimeToken]) -> List[Dict]:
        """Generoi trading signaalit real-time tokeneille"""
        signals = []
        
        for token in tokens:
            # Kriteerit real-time signaaleille
            if (token.age_minutes <= 5.0 and  # Max 5 minuuttia
                token.market_cap >= 10000 and token.market_cap <= 500000 and  # Sopiva MC
                token.volume_24h >= token.market_cap * 0.1 and  # Volume >= 10% MC
                token.overall_score >= 5.0):  # Minimum score
                
                # Luo BUY signaali
                signal = {
                    "type": "BUY",
                    "symbol": token.symbol,
                    "price": token.price,
                    "market_cap": token.market_cap,
                    "age_minutes": token.age_minutes,
                    "score": token.overall_score,
                    "source": token.source,
                    "reason": f"Real-time: {token.age_minutes:.1f}min old, MC: ${token.market_cap:,.0f}, Score: {token.overall_score:.1f}",
                    "timestamp": datetime.now().isoformat()
                }
                signals.append(signal)
                
                self.logger.info(f"🎯 REAL-TIME Signaali: BUY {token.symbol} - Age: {token.age_minutes:.1f}min, Source: {token.source}")
        
        return signals

    async def _simulate_real_time_trading(self, signals: List[Dict]) -> int:
        """Simuloi real-time kauppojen suorittaminen"""
        trades_executed = 0
        
        for signal in signals:
            try:
                # Simuloi kauppa
                trade_result = await self._execute_real_time_trade(signal)
                if trade_result:
                    trades_executed += 1
                    self.logger.info(f"💰 REAL-TIME Kauppa: {signal['symbol']} - {trade_result}")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Real-time kauppa epäonnistui {signal['symbol']}: {e}")
        
        return trades_executed

    async def _execute_real_time_trade(self, signal: Dict) -> Dict:
        """Suorita real-time simuloitu kauppa"""
        symbol = signal["symbol"]
        price = signal["price"]
        market_cap = signal["market_cap"]
        source = signal["source"]
        
        # Position size based on source reliability
        if "real_time" in source:
            position_size_percent = 0.03  # 3% for real-time data
        elif "trending" in source:
            position_size_percent = 0.02  # 2% for trending data
        else:
            position_size_percent = 0.01  # 1% for other sources
        
        position_value = self.portfolio_value * position_size_percent
        
        # Real-time price simulation (more conservative)
        if "real_time" in source:
            price_change_percent = -10 + (hash(symbol) % 40)  # -10% to +30%
        else:
            price_change_percent = -20 + (hash(symbol) % 50)  # -20% to +30%
        
        exit_price = price * (1 + price_change_percent / 100)
        
        # Laske PnL
        pnl = (exit_price - price) * (position_value / price)
        
        # Päivitä portfolio
        self.portfolio_value += pnl
        self.portfolio_pnl += pnl
        
        return {
            "symbol": symbol,
            "source": source,
            "entry_price": price,
            "exit_price": exit_price,
            "position_value": position_value,
            "pnl": pnl,
            "pnl_percent": (pnl / position_value) * 100
        }

    async def _print_real_time_report(self, tokens: List[RealTimeToken], signals: List[Dict], trades: int):
        """Tulosta real-time raportti"""
        self.logger.info("="*60)
        self.logger.info("📊 REAL-TIME HYBRID BOT RAPORTTI")
        self.logger.info("="*60)
        
        # Token analyysi
        self.logger.info(f"🔍 **REAL-TIME TOKEN ANALYYSI:**")
        self.logger.info(f"   Tokeneita skannattu: {len(tokens)}")
        
        if tokens:
            sources = {}
            for token in tokens:
                source = token.source
                sources[source] = sources.get(source, 0) + 1
            
            self.logger.info(f"   Data lähteet:")
            for source, count in sources.items():
                self.logger.info(f"     {source}: {count} tokenia")
            
            avg_age = sum(t.age_minutes for t in tokens) / len(tokens)
            self.logger.info(f"   Keskimääräinen ikä: {avg_age:.1f} min")
        
        # Signaalit
        self.logger.info(f"📈 **REAL-TIME SIGNAALIT:**")
        self.logger.info(f"   Signaaleja generoitu: {len(signals)}")
        if signals:
            self.logger.info(f"   Paras signaali: {max(signals, key=lambda x: x['score'])['symbol']} (Score: {max(signals, key=lambda x: x['score'])['score']:.1f})")
        
        # Kauppojen suorittaminen
        self.logger.info(f"💰 **REAL-TIME KAUPPOJEN SUORITTAMINEN:**")
        self.logger.info(f"   Kauppoja suoritettu: {trades}")
        self.logger.info(f"   Portfolio arvo: ${self.portfolio_value:.2f}")
        self.logger.info(f"   Portfolio PnL: ${self.portfolio_pnl:.2f}")
        
        self.logger.info("="*60)
        self.logger.info("✅ REAL-TIME HYBRID BOT SYKLI VALMIS!")

    async def run_continuous_real_time(self, cycles: int = 5):
        """Suorita jatkuva real-time optimointi"""
        self.logger.info(f"🚀 Käynnistetään jatkuva real-time optimointi ({cycles} sykliä)...")
        
        for i in range(cycles):
            try:
                self.logger.info(f"\n🔄 REAL-TIME SYKLI {i+1}/{cycles}")
                result = await self.run_real_time_cycle()
                
                if result.get('error'):
                    self.logger.error(f"❌ Real-time sykli {i+1} epäonnistui: {result['error']}")
                else:
                    self.logger.info(f"✅ Real-time sykli {i+1} valmis!")
                
                # Odota seuraavaan sykliin
                if i < cycles - 1:
                    self.logger.info("⏰ Odotetaan 30 sekuntia...")
                    await asyncio.sleep(30)
                    
            except Exception as e:
                self.logger.error(f"❌ Virhe real-time syklissä {i+1}: {e}")
        
        # Lopullinen raportti
        await self._print_final_real_time_report()

    async def _print_final_real_time_report(self):
        """Tulosta lopullinen real-time raportti"""
        self.logger.info("\n" + "="*80)
        self.logger.info("🏆 LOPULLINEN REAL-TIME RAPORTTI")
        self.logger.info("="*80)
        
        self.logger.info(f"📊 **KOKONAISTULOKSET:**")
        self.logger.info(f"   Syklejä suoritettu: {self.cycle_count}")
        self.logger.info(f"   Tokeneita skannattu: {self.total_tokens_scanned}")
        self.logger.info(f"   Signaaleja generoitu: {self.total_signals_generated}")
        self.logger.info(f"   Kauppoja suoritettu: {self.total_trades_executed}")
        
        self.logger.info(f"💰 **PORTFOLIO:**")
        self.logger.info(f"   Alkuperäinen arvo: $10,000.00")
        self.logger.info(f"   Nykyinen arvo: ${self.portfolio_value:.2f}")
        self.logger.info(f"   Kokonaistuotto: ${self.portfolio_pnl:.2f}")
        self.logger.info(f"   Tuotto-%: {(self.portfolio_pnl / 10000) * 100:.2f}%")
        
        self.logger.info(f"📈 **PERFORMANCE:**")
        if self.total_tokens_scanned > 0:
            self.logger.info(f"   Keskimäärin tokenia/sykli: {self.total_tokens_scanned / self.cycle_count:.1f}")
        if self.total_signals_generated > 0:
            self.logger.info(f"   Keskimäärin signaalia/sykli: {self.total_signals_generated / self.cycle_count:.1f}")
        
        self.logger.info("="*80)
        self.logger.info("🎯 REAL-TIME OPTIMOINTI VALMIS - BOT KÄYTTÄÄ NYT OIKEAA DATA! 🚀")

# Test function
async def test_real_time_bot():
    """Testaa real-time bottia"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    bot = HybridBotWithRealTime()
    await bot.run_continuous_real_time(3)

if __name__ == "__main__":
    asyncio.run(test_real_time_bot())
