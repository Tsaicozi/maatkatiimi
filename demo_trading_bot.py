"""
Demo Trading Bot - Esittely versio NextGen Trading Bot:ista
Käyttää mock dataa API ongelmien välttämiseksi
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Mock data luokat
@dataclass
class MockTokenData:
    symbol: str
    name: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_1h: float
    price_change_24h: float
    price_change_7d: float
    liquidity: float
    age_minutes: int
    holders: int
    fresh_holders_1d: float
    fresh_holders_7d: float
    top_10_percent: float
    dev_tokens_percent: float
    social_score: float
    technical_score: float
    momentum_score: float
    risk_score: float
    overall_score: float
    timestamp: datetime

class DemoTokenScanner:
    """Demo token skanneri mock datalla"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def scan_new_tokens(self) -> List[MockTokenData]:
        """Skannaa mock tokeneita - dynaamisesti generoituja"""
        self.logger.info("🔍 Skannataan ultra-fresh Solana tokeneita (1-5min)...")
        
        # Solana-pohjaiset token nimet ja symbolit
        token_names = [
            ("BONK", "Bonk"), ("WIF", "Dogwifhat"), ("POPCAT", "Popcat"), ("MYRO", "Myro"),
            ("BOME", "Book of Meme"), ("SLERF", "Slerf"), ("MEW", "Cat in a Dogs World"), ("PNUT", "Peanut the Squirrel"),
            ("GOAT", "Goatseus Maximus"), ("ACT", "Achaint"), ("FARTCOIN", "Fartcoin"), ("BILLY", "Billy"),
            ("CHILLGUY", "Chill Guy"), ("NEIRO", "Neiro"), ("SMOG", "Smog"), ("PNUT", "Peanut"),
            ("SLOTH", "Slothana"), ("RAY", "Raydium"), ("JUP", "Jupiter"), ("ORCA", "Orca"),
            ("SRM", "Serum"), ("STEP", "Step Finance"), ("COPE", "Cope"), ("ROPE", "Rope"),
            ("FIDA", "Bonfida"), ("KIN", "Kin"), ("MAPS", "Maps"), ("OXY", "Oxygen"),
            ("PORT", "Port Finance"), ("SLIM", "Solanium"), ("TULIP", "Tulip Protocol"), ("ATLAS", "Star Atlas"),
            ("POLIS", "Star Atlas DAO"), ("SAMO", "Samoyedcoin"), ("SUNNY", "Sunny Aggregator"), ("TULIP", "Tulip")
        ]
        
        # Generoi 8-15 satunnaista tokenia jokaisella skannauksella
        num_tokens = np.random.randint(8, 16)
        selected_tokens = np.random.choice(len(token_names), num_tokens, replace=False)
        
        mock_tokens = []
        for i in selected_tokens:
            symbol, name = token_names[i]
            
            # Generoi toisen botin mukaisten kriteerien arvot
            price = np.random.uniform(0.000001, 0.0001)  # Pienet hinnat
            market_cap = np.random.uniform(20_000, 100_000)  # Pieni FDV (20K-100K)
            volume_24h = market_cap * np.random.uniform(0.8, 3.0)  # Korkea volume
            price_change_1h = np.random.uniform(7, 700)  # 1H muutos +7% to +700%
            price_change_24h = np.random.uniform(10, 800)  # 24H muutos
            price_change_7d = np.random.uniform(15, 1000)  # 7D muutos
            liquidity = market_cap * np.random.uniform(0.2, 0.5)  # LP 20-50% market capista
            age_minutes = np.random.randint(1, 5)  # 1-5 minuuttia ultra-fresh (1-480h)
            holders = np.random.randint(50, 1000)  # Pieni holder määrä
            fresh_holders_1d = np.random.uniform(3, 12)  # Fresh holders 1D: 3-12%
            fresh_holders_7d = np.random.uniform(15, 30)  # Fresh holders 7D: 15-30%
            top_10_percent = np.random.uniform(20, 35)  # Top 10 holders: 20-35%
            dev_tokens_percent = np.random.uniform(0, 1)  # Dev tokens: 0-1%
            
            # Skoorit
            social_score = np.random.uniform(3, 10)
            technical_score = np.random.uniform(3, 10)
            momentum_score = np.random.uniform(3, 10)
            risk_score = np.random.uniform(1, 10)
            overall_score = (social_score + technical_score + momentum_score) / 3
            
            token = MockTokenData(
                symbol=symbol,
                name=name,
                price=price,
                market_cap=market_cap,
                volume_24h=volume_24h,
                price_change_1h=price_change_1h,
                price_change_24h=price_change_24h,
                price_change_7d=price_change_7d,
                liquidity=liquidity,
                age_minutes=age_minutes,
                holders=holders,
                fresh_holders_1d=fresh_holders_1d,
                fresh_holders_7d=fresh_holders_7d,
                top_10_percent=top_10_percent,
                dev_tokens_percent=dev_tokens_percent,
                social_score=social_score,
                technical_score=technical_score,
                momentum_score=momentum_score,
                risk_score=risk_score,
                overall_score=overall_score,
                timestamp=datetime.now()
            )
            mock_tokens.append(token)
        
        # Lajittele parhaan skoorin mukaan
        mock_tokens.sort(key=lambda x: x.overall_score, reverse=True)
        
        self.logger.info(f"✅ Löydettiin {len(mock_tokens)} ultra-fresh Solana tokenia")
        return mock_tokens

class DemoTechnicalEngine:
    """Demo tekninen analyysi moottori"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_token(self, token: MockTokenData) -> Dict:
        """Analysoi token mock datalla"""
        try:
            # Simuloi teknistä analyysiä
            analysis = {
                "rsi": float(np.random.uniform(20, 80)),
                "macd": float(np.random.uniform(-0.01, 0.01)),
                "macd_signal": float(np.random.uniform(-0.01, 0.01)),
                "sma_20": float(token.price * np.random.uniform(0.95, 1.05)),
                "sma_50": float(token.price * np.random.uniform(0.90, 1.10)),
                "bollinger_upper": float(token.price * 1.1),
                "bollinger_lower": float(token.price * 0.9),
                "volume_sma": float(token.volume_24h * np.random.uniform(0.8, 1.2)),
                "atr": float(token.price * 0.05),
                "trend_direction": str(np.random.choice(["BULLISH", "BEARISH", "SIDEWAYS"])),
                "trend_strength": float(np.random.uniform(30, 90)),
                "momentum_score": float(np.random.uniform(40, 90)),
                "breakout_probability": float(np.random.uniform(0.2, 0.8)),
                "patterns": ["ASCENDING_TRIANGLE"] if np.random.random() > 0.7 else []
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Virhe tokenin analyysissä: {e}")
            return {}

class DemoRiskEngine:
    """Demo riskienhallinta moottori"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.closed_positions = []
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, token: MockTokenData, risk_score: float, confidence: float) -> float:
        """Laske position koko"""
        base_size = self.initial_capital * 0.05  # 5% per position
        
        # Säätö riskin mukaan
        risk_adjustment = 1.0 - (risk_score / 10.0)
        risk_adjustment = max(risk_adjustment, 0.1)
        
        # Säätö luottamuksen mukaan
        confidence_adjustment = confidence
        
        # Säätö market cap mukaan
        if token.market_cap < 1_000_000:
            market_cap_adjustment = 0.3
        elif token.market_cap < 10_000_000:
            market_cap_adjustment = 0.6
        else:
            market_cap_adjustment = 0.8
        
        final_size = base_size * risk_adjustment * confidence_adjustment * market_cap_adjustment
        return min(final_size, self.current_capital * 0.1)
    
    def can_open_position(self, token_symbol: str, position_size: float) -> tuple[bool, str]:
        """Tarkista voiko avata position"""
        if token_symbol in self.positions:
            return False, f"Position jo olemassa tokenille {token_symbol}"
        
        if position_size > self.current_capital * 0.1:
            return False, f"Liian suuri position: {position_size:.2f}"
        
        return True, "OK"
    
    def open_position(self, token: MockTokenData, entry_price: float, position_size: float) -> bool:
        """Avaa position"""
        try:
            token_symbol = token.symbol
            
            can_open, reason = self.can_open_position(token_symbol, position_size)
            if not can_open:
                self.logger.warning(f"Ei voi avata position {token_symbol}: {reason}")
                return False
            
            quantity = position_size / entry_price
            
            position = {
                "token_symbol": token_symbol,
                "token_name": token.name,
                "entry_price": entry_price,
                "current_price": entry_price,
                "quantity": quantity,
                "position_value": position_size,
                "unrealized_pnl": 0.0,
                "entry_time": datetime.now(),
                "risk_score": token.risk_score,
                "age_minutes": token.age_minutes,
                "market_cap": token.market_cap,
                "price_change_1h": token.price_change_1h,
                "fresh_holders_1d": token.fresh_holders_1d,
                "top_10_percent": token.top_10_percent,
                "dev_tokens_percent": token.dev_tokens_percent
            }
            
            self.positions[token_symbol] = position
            self.current_capital -= position_size
            
            self.logger.info(f"✅ Avattu position {token_symbol}: {quantity:.6f} @ ${entry_price:.6f} (Age: {token.age_minutes}min, FDV: ${token.market_cap:,.0f})")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe position avaamisessa: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict:
        """Hae portfolio yhteenveto"""
        total_value = self.current_capital + sum(pos["position_value"] for pos in self.positions.values())
        
        return {
            "portfolio_value": total_value,
            "current_capital": self.current_capital,
            "total_exposure": sum(pos["position_value"] for pos in self.positions.values()),
            "open_positions": len(self.positions),
            "closed_positions": len(self.closed_positions),
            "positions": self.positions
        }

class DemoNextGenTradingBot:
    """Demo NextGen Trading Bot"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.logger = self.setup_logging()
        
        # Alusta komponentit
        self.token_scanner = DemoTokenScanner()
        self.technical_engine = DemoTechnicalEngine()
        self.risk_engine = DemoRiskEngine(initial_capital)
        
        # Tilastot
        self.total_scans = 0
        self.total_signals = 0
        self.total_trades = 0
        self.successful_trades = 0
        
        self.logger.info("🚀 Demo NextGen Trading Bot alustettu")
    
    def setup_logging(self):
        """Aseta logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('demo_trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def run_full_analysis_cycle(self) -> Dict:
        """Suorita täydellinen analyysi sykli"""
        try:
            self.logger.info("🔄 Aloitetaan demo analyysi sykli...")
            
            # 1. Skannaa mock tokeneita
            tokens = await self.token_scanner.scan_new_tokens()
            self.total_scans += 1
            
            if not tokens:
                return {"status": "no_tokens", "tokens": []}
            
            # 2. Analysoi jokainen token
            analyzed_tokens = []
            for token in tokens:
                try:
                    # Analysoi token
                    technical_analysis = self.technical_engine.analyze_token(token)
                    
                    if technical_analysis:  # Tarkista että analyysi onnistui
                        # Päivitä token skoorit
                        token.technical_score = technical_analysis.get("momentum_score", 5.0)
                        token.overall_score = (token.social_score + token.technical_score + token.momentum_score) / 3
                        
                        analyzed_tokens.append({
                            "token": token,
                            "technical_analysis": technical_analysis
                        })
                    else:
                        # Käytä oletusarvoja jos analyysi epäonnistui
                        token.technical_score = 5.0
                        token.overall_score = (token.social_score + token.technical_score + token.momentum_score) / 3
                        
                        analyzed_tokens.append({
                            "token": token,
                            "technical_analysis": {"trend_direction": "SIDEWAYS", "momentum_score": 5.0}
                        })
                    
                except Exception as e:
                    self.logger.error(f"Virhe tokenin {token.symbol} analyysissä: {e}")
                    # Lisää token ilman teknistä analyysiä
                    token.technical_score = 5.0
                    token.overall_score = (token.social_score + token.technical_score + token.momentum_score) / 3
                    
                    analyzed_tokens.append({
                        "token": token,
                        "technical_analysis": {"trend_direction": "SIDEWAYS", "momentum_score": 5.0}
                    })
                    continue
            
            # 3. Generoi trading signaalit
            trading_signals = self.generate_trading_signals(analyzed_tokens)
            self.total_signals += len(trading_signals)
            
            # 4. Suorita trading toimenpiteet
            trading_results = await self.execute_trading_signals(trading_signals)
            
            # 5. Päivitä tilastot
            self.update_statistics(trading_results)
            
            # 6. Tallenna tulos
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "tokens_analyzed": len(analyzed_tokens),
                "signals_generated": len(trading_signals),
                "trades_executed": len(trading_results),
                "portfolio_summary": self.risk_engine.get_portfolio_summary()
            }
            
            await self.save_analysis_result(result)
            
            self.logger.info(f"✅ Demo analyysi sykli valmis: {len(analyzed_tokens)} tokenia, {len(trading_signals)} signaalia")
            return result
            
        except Exception as e:
            self.logger.error(f"Virhe demo analyysi syklissä: {e}")
            return {"status": "error", "error": str(e)}
    
    def generate_trading_signals(self, analyzed_tokens: List[Dict]) -> List[Dict]:
        """Generoi trading signaalit"""
        signals = []
        
        try:
            for analysis in analyzed_tokens:
                token = analysis["token"]
                technical = analysis["technical_analysis"]
                
                # Ultra-fresh token signaali kriteerit (1-5 minuuttia)
                # BUY signaalit - Ultra-fresh tokenit, korkea momentum
                if (token.market_cap >= 20_000 and token.market_cap <= 100_000 and  # FDV 20K-100K
                    token.age_minutes <= 5 and  # Max 5 minuuttia ultra-fresh
                    token.price_change_1h >= 7 and  # Min +7% 1H
                    token.fresh_holders_1d >= 3 and token.fresh_holders_1d <= 12 and  # Fresh holders 3-12%
                    token.top_10_percent <= 35 and  # Top 10% max 35%
                    token.dev_tokens_percent <= 1 and  # Dev tokens max 1%
                    token.volume_24h >= token.market_cap * 0.8):  # Volume min 80% market capista
                    
                    # Laske Solana-spesifinen tuotto potentiaali
                    momentum_multiplier = min(token.price_change_24h / 30, 5.0)  # Max 5x Solana tokenille
                    target_price = token.price * (1.5 + momentum_multiplier * 0.5)  # Korkeammat tavoitteet
                    
                    signal = {
                        "token": token,
                        "signal_type": "BUY",
                        "confidence": min(token.overall_score / 10 + token.price_change_24h / 200, 0.95),
                        "entry_price": token.price,
                        "target_price": target_price,
                        "stop_loss": token.price * 0.85,
                        "reasoning": f"ULTRA-FRESH BUY: {token.symbol} FDV: ${token.market_cap:,.0f}, +{token.price_change_1h:.0f}% 1H, Age: {token.age_minutes}min, Fresh: {token.fresh_holders_1d:.1f}%, Top10: {token.top_10_percent:.1f}%, Dev: {token.dev_tokens_percent:.1f}%"
                    }
                    signals.append(signal)
                
                # SELL signaalit (vain jos on position)
                elif (token.overall_score <= 4.0 and 
                      token.price_change_24h < -20):
                    
                    signal = {
                        "token": token,
                        "signal_type": "SELL",
                        "confidence": min((10 - token.overall_score) / 10 + abs(token.price_change_24h) / 200, 0.95),
                        "entry_price": token.price,
                        "target_price": token.price * 0.8,
                        "stop_loss": token.price * 1.15,
                        "reasoning": f"SELL: Skoori {token.overall_score:.1f}/10, {token.price_change_24h:.1f}% 24h"
                    }
                    signals.append(signal)
                
                # HOLD signaalit (hyvät tokenit joilla on position)
                elif (token.overall_score >= 7.5 and 
                      token.price_change_24h > -5 and
                      token.price_change_24h < 30):
                    
                    signal = {
                        "token": token,
                        "signal_type": "HOLD",
                        "confidence": token.overall_score / 10,
                        "entry_price": token.price,
                        "target_price": token.price * 1.3,
                        "stop_loss": token.price * 0.9,
                        "reasoning": f"HOLD: Vakaa skoori {token.overall_score:.1f}/10, {token.price_change_24h:.1f}% 24h"
                    }
                    signals.append(signal)
            
            # Järjestä luottamuksen mukaan
            signals.sort(key=lambda x: x["confidence"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Virhe trading signaalien generoinnissa: {e}")
        
        return signals
    
    async def execute_trading_signals(self, signals: List[Dict]) -> List[Dict]:
        """Suorita trading signaalit"""
        results = []
        
        try:
            for signal in signals:
                token = signal["token"]
                
                if signal["signal_type"] == "BUY":
                    # Laske position koko
                    position_size = self.risk_engine.calculate_position_size(
                        token, 
                        token.risk_score, 
                        signal["confidence"]
                    )
                    
                    # Avaa position
                    success = self.risk_engine.open_position(
                        token,
                        entry_price=signal["entry_price"],
                        position_size=position_size
                    )
                    
                    if success:
                        self.total_trades += 1
                        results.append({
                            "action": "BUY",
                            "token": token.symbol,
                            "position_size": position_size,
                            "entry_price": signal["entry_price"],
                            "success": True,
                            "reasoning": signal["reasoning"]
                        })
                        
                        self.logger.info(f"✅ Avattu BUY position {token.symbol}: ${position_size:.2f} @ ${signal['entry_price']:.6f}")
                    else:
                        results.append({
                            "action": "BUY",
                            "token": token.symbol,
                            "success": False,
                            "reason": "Position avaaminen epäonnistui"
                        })
            
        except Exception as e:
            self.logger.error(f"Virhe trading signaalien suorittamisessa: {e}")
        
        return results
    
    def update_statistics(self, trading_results: List[Dict]):
        """Päivitä tilastot"""
        try:
            successful_trades = [r for r in trading_results if r.get("success", False)]
            self.successful_trades += len(successful_trades)
            
            if self.total_trades > 0:
                success_rate = (self.successful_trades / self.total_trades) * 100
                self.logger.info(f"📊 Tilastot: {self.total_trades} kauppaa, {success_rate:.1f}% onnistunut")
            
        except Exception as e:
            self.logger.error(f"Virhe tilastojen päivityksessä: {e}")
    
    async def save_analysis_result(self, result: Dict):
        """Tallenna analyysi tulos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"demo_trading_analysis_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            self.logger.info(f"💾 Demo analyysi tulos tallennettu: {filename}")
            
        except Exception as e:
            self.logger.error(f"Virhe demo analyysi tuloksen tallentamisessa: {e}")
    
    def get_bot_status(self) -> Dict:
        """Hae bot tila"""
        return {
            "total_scans": self.total_scans,
            "total_signals": self.total_signals,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "success_rate": (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "portfolio_summary": self.risk_engine.get_portfolio_summary()
        }

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Pääfunktio"""
    print("🚀 Demo NextGen Trading Bot käynnistyy...")
    print("=" * 80)
    
    # Luo demo trading bot
    bot = DemoNextGenTradingBot(initial_capital=10000.0)
    
    # Suorita yksi analyysi sykli
    print("🔄 Suoritetaan demo analyysi sykli...")
    result = await bot.run_full_analysis_cycle()
    
    if result["status"] == "success":
        print(f"✅ Demo analyysi onnistui!")
        print(f"   Tokenia analysoitu: {result['tokens_analyzed']}")
        print(f"   Signaalia generoitu: {result['signals_generated']}")
        print(f"   Kauppaa suoritettu: {result['trades_executed']}")
        
        # Näytä portfolio yhteenveto
        portfolio = result["portfolio_summary"]
        print(f"\n📊 PORTFOLIO YHTEENVETO:")
        print(f"   Portfolio arvo: ${portfolio['portfolio_value']:.2f}")
        print(f"   Nykyinen pääoma: ${portfolio['current_capital']:.2f}")
        print(f"   Kokonais exposure: ${portfolio['total_exposure']:.2f}")
        print(f"   Avoimia positioneita: {portfolio['open_positions']}")
        
        # Näytä avoimet positionit
        if portfolio['positions']:
            print(f"\n📈 AVOIMET POSITIONIT:")
            for token, pos in portfolio['positions'].items():
                print(f"   {token}: {pos['quantity']:.6f} @ ${pos['entry_price']:.6f}")
                print(f"      Position arvo: ${pos['position_value']:.2f}")
                print(f"      Risk skoori: {pos['risk_score']:.1f}/10")
        
    else:
        print(f"❌ Demo analyysi epäonnistui: {result.get('error', 'Tuntematon virhe')}")
    
    # Näytä bot tila
    status = bot.get_bot_status()
    print(f"\n🤖 BOT TILA:")
    print(f"   Skannauksia: {status['total_scans']}")
    print(f"   Signaaleja: {status['total_signals']}")
    print(f"   Kauppoja: {status['total_trades']}")
    print(f"   Onnistumisprosentti: {status['success_rate']:.1f}%")
    
    print("=" * 80)
    print("✅ Demo NextGen Trading Bot valmis!")
    print("\n🎯 TÄMÄ ON DEMO VERSIO!")
    print("   - Käyttää mock dataa")
    print("   - Ei tee oikeita kauppoja")
    print("   - Näyttää järjestelmän toiminnan")

if __name__ == "__main__":
    asyncio.run(main())
