"""
NextGen Trading Bot - Pääintegraatio
Yhdistää kaikki komponentit: token skanneri, tekninen analyysi, riskienhallinta
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Importoi komponentit
from nextgen_token_scanner_bot import NextGenTokenScanner, TokenData, TradingSignal
from technical_analysis_engine import TechnicalAnalysisEngine, TechnicalIndicators, TrendAnalysis, PatternRecognition
from risk_management_engine import RiskManagementEngine, Position, RiskLevel

class NextGenTradingBot:
    """Täydellinen trading bot uusille tokeneille"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.logger = self.setup_logging()
        
        # Alusta komponentit
        self.token_scanner = NextGenTokenScanner()
        self.technical_engine = TechnicalAnalysisEngine()
        self.risk_engine = RiskManagementEngine(initial_capital)
        
        # Bot tila
        self.is_running = False
        self.scan_interval = 300  # 5 minuuttia
        self.last_scan_time = None
        
        # Tilastot
        self.total_scans = 0
        self.total_signals = 0
        self.total_trades = 0
        self.successful_trades = 0
        
        self.logger.info("🚀 NextGen Trading Bot alustettu")
    
    def setup_logging(self):
        """Aseta logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nextgen_trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def run_full_analysis_cycle(self) -> Dict:
        """Suorita täydellinen analyysi sykli"""
        try:
            self.logger.info("🔄 Aloitetaan täydellinen analyysi sykli...")
            
            # 1. Skannaa uusia tokeneita
            new_tokens = await self.token_scanner.scan_new_tokens()
            self.total_scans += 1
            
            if not new_tokens:
                self.logger.info("❌ Ei löytynyt uusia tokeneita")
                return {"status": "no_tokens", "tokens": []}
            
            self.logger.info(f"✅ Löydettiin {len(new_tokens)} uutta tokenia")
            
            # 2. Analysoi jokainen token
            analyzed_tokens = []
            for token in new_tokens[:10]:  # Rajoita 10 tokeniin
                try:
                    # Hae OHLCV data (mock data tässä esimerkissä)
                    ohlcv_data = self.get_mock_ohlcv_data(token)
                    
                    # Laske tekniset indikaattorit
                    indicators = self.technical_engine.calculate_technical_indicators(ohlcv_data)
                    
                    # Analysoi trendi
                    trend_analysis = self.technical_engine.analyze_trend(ohlcv_data, indicators)
                    
                    # Tunnista kuvioita
                    patterns = self.technical_engine.recognize_patterns(ohlcv_data)
                    
                    # Laske riski skoori
                    risk_score = self.risk_engine.calculate_risk_score(token, indicators, trend_analysis)
                    
                    # Päivitä token skoorit
                    token.technical_score = self.calculate_technical_score(indicators, trend_analysis)
                    token.risk_score = risk_score
                    token.overall_score = self.calculate_overall_score(token, indicators, trend_analysis)
                    
                    analyzed_tokens.append({
                        "token": token,
                        "indicators": indicators,
                        "trend_analysis": trend_analysis,
                        "patterns": patterns,
                        "risk_score": risk_score
                    })
                    
                except Exception as e:
                    self.logger.error(f"Virhe tokenin {token.symbol} analyysissä: {e}")
                    continue
            
            # 3. Generoi trading signaalit
            trading_signals = self.generate_trading_signals(analyzed_tokens)
            self.total_signals += len(trading_signals)
            
            # 4. Suorita trading toimenpiteet
            trading_results = await self.execute_trading_signals(trading_signals)
            
            # 5. Päivitä riskienhallinta
            risk_actions = self.risk_engine.check_trading_rules()
            if risk_actions:
                self.risk_engine.execute_actions(risk_actions)
            
            # 6. Päivitä tilastot
            self.update_statistics(trading_results)
            
            # 7. Tallenna tulos
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "tokens_analyzed": len(analyzed_tokens),
                "signals_generated": len(trading_signals),
                "trades_executed": len(trading_results),
                "portfolio_summary": self.risk_engine.get_portfolio_summary()
            }
            
            await self.save_analysis_result(result)
            
            self.logger.info(f"✅ Analyysi sykli valmis: {len(analyzed_tokens)} tokenia, {len(trading_signals)} signaalia")
            return result
            
        except Exception as e:
            self.logger.error(f"Virhe analyysi syklissä: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_mock_ohlcv_data(self, token: TokenData) -> pd.DataFrame:
        """Hae mock OHLCV data (todellisessa toteutuksessa haettaisiin oikea data)"""
        try:
            # Luo 100 päivän mock data
            dates = pd.date_range(start=datetime.now() - timedelta(days=100), end=datetime.now(), freq='D')
            
            # Simuloi hinta dataa tokenin ominaisuuksien perusteella
            np.random.seed(hash(token.symbol) % 2**32)
            base_price = token.price
            volatility = abs(token.price_change_24h) / 100 if token.price_change_24h else 0.02
            
            returns = np.random.normal(0.001, volatility, len(dates))
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Luo OHLCV data
            ohlcv_data = pd.DataFrame({
                'date': dates,
                'open': [p * (1 + np.random.normal(0, volatility/2)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, volatility))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, volatility))) for p in prices],
                'close': prices,
                'volume': [np.random.randint(int(token.volume_24h/100), int(token.volume_24h*2)) for _ in range(len(dates))]
            })
            
            ohlcv_data.set_index('date', inplace=True)
            return ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Virhe mock OHLCV datan luonnissa: {e}")
            return pd.DataFrame()
    
    def calculate_technical_score(self, indicators: TechnicalIndicators, trend_analysis: TrendAnalysis) -> float:
        """Laske tekninen skoori"""
        try:
            score = 5.0  # Aloita keskimääräisellä
            
            # RSI skoori
            if 30 < indicators.rsi < 70:
                score += 1.0  # Terve RSI
            elif indicators.rsi > 70:
                score -= 0.5  # Ylimyynti
            elif indicators.rsi < 30:
                score -= 0.5  # Ylimyynti
            
            # MACD skoori
            if indicators.macd > indicators.macd_signal:
                score += 1.0  # Bullish MACD
            else:
                score -= 0.5  # Bearish MACD
            
            # Trendi skoori
            if trend_analysis.trend_direction == 'BULLISH':
                score += 1.5
            elif trend_analysis.trend_direction == 'BEARISH':
                score -= 1.0
            
            # Trendi voima
            if trend_analysis.trend_strength > 70:
                score += 1.0
            elif trend_analysis.trend_strength < 30:
                score -= 0.5
            
            # Momentum skoori
            if trend_analysis.momentum_score > 70:
                score += 1.0
            elif trend_analysis.momentum_score < 30:
                score -= 0.5
            
            return max(0, min(score, 10))
            
        except Exception as e:
            self.logger.error(f"Virhe teknisen skoorin laskennassa: {e}")
            return 5.0
    
    def calculate_overall_score(self, token: TokenData, indicators: TechnicalIndicators, trend_analysis: TrendAnalysis) -> float:
        """Laske kokonaisskoori"""
        try:
            weights = {
                'social': 0.15,
                'technical': 0.25,
                'momentum': 0.25,
                'risk': -0.15,  # Riskit vähentävät skooria
                'trend': 0.20
            }
            
            # Trendi skoori
            trend_score = 5.0
            if trend_analysis.trend_direction == 'BULLISH':
                trend_score = 8.0
            elif trend_analysis.trend_direction == 'BEARISH':
                trend_score = 2.0
            
            overall = (
                token.social_score * weights['social'] +
                token.technical_score * weights['technical'] +
                token.momentum_score * weights['momentum'] +
                (10 - token.risk_score) * weights['risk'] +
                trend_score * weights['trend']
            )
            
            return max(0, min(overall, 10))
            
        except Exception as e:
            self.logger.error(f"Virhe kokonaisskoorin laskennassa: {e}")
            return 5.0
    
    def generate_trading_signals(self, analyzed_tokens: List[Dict]) -> List[Dict]:
        """Generoi trading signaalit"""
        signals = []
        
        try:
            for analysis in analyzed_tokens:
                token = analysis["token"]
                indicators = analysis["indicators"]
                trend_analysis = analysis["trend_analysis"]
                patterns = analysis["patterns"]
                
                # Tarkista signaali kriteerit
                if token.overall_score >= 7.0:  # Korkea skoori
                    signal = {
                        "token": token,
                        "signal_type": "BUY",
                        "confidence": token.overall_score / 10,
                        "entry_price": token.price,
                        "target_price": token.price * 1.5,  # 50% tuotto
                        "stop_loss": token.price * 0.8,     # 20% tappio
                        "reasoning": f"Korkea skoori: {token.overall_score:.1f}/10, Trend: {trend_analysis.trend_direction}",
                        "indicators": indicators,
                        "trend_analysis": trend_analysis,
                        "patterns": patterns
                    }
                    signals.append(signal)
                
                elif token.overall_score <= 3.0:  # Matala skoori
                    signal = {
                        "token": token,
                        "signal_type": "SELL",
                        "confidence": (10 - token.overall_score) / 10,
                        "entry_price": token.price,
                        "target_price": token.price * 0.7,  # 30% tappio
                        "stop_loss": token.price * 1.2,     # 20% tappio
                        "reasoning": f"Matala skoori: {token.overall_score:.1f}/10, Trend: {trend_analysis.trend_direction}",
                        "indicators": indicators,
                        "trend_analysis": trend_analysis,
                        "patterns": patterns
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
                    
                    # Tarkista voiko avata position
                    can_open, reason = self.risk_engine.can_open_position(token.symbol, position_size)
                    
                    if can_open:
                        # Avaa position
                        success = self.risk_engine.open_position(
                            token,
                            entry_price=signal["entry_price"],
                            position_size=position_size,
                            stop_loss=signal["stop_loss"],
                            take_profit=signal["target_price"],
                            risk_score=token.risk_score
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
                    else:
                        results.append({
                            "action": "BUY",
                            "token": token.symbol,
                            "success": False,
                            "reason": reason
                        })
                
                elif signal["signal_type"] == "SELL":
                    # Tarkista onko position olemassa
                    if token.symbol in self.risk_engine.positions:
                        result = self.risk_engine.close_position(token.symbol, signal["reasoning"])
                        results.append(result)
                        
                        if result["success"]:
                            self.total_trades += 1
                            self.logger.info(f"✅ Suljettu SELL position {token.symbol}: P&L ${result['realized_pnl']:.2f}")
            
        except Exception as e:
            self.logger.error(f"Virhe trading signaalien suorittamisessa: {e}")
        
        return results
    
    def update_statistics(self, trading_results: List[Dict]):
        """Päivitä tilastot"""
        try:
            successful_trades = [r for r in trading_results if r.get("success", False)]
            self.successful_trades += len(successful_trades)
            
            # Laske onnistumisprosentti
            if self.total_trades > 0:
                success_rate = (self.successful_trades / self.total_trades) * 100
                self.logger.info(f"📊 Tilastot: {self.total_trades} kauppaa, {success_rate:.1f}% onnistunut")
            
        except Exception as e:
            self.logger.error(f"Virhe tilastojen päivityksessä: {e}")
    
    async def save_analysis_result(self, result: Dict):
        """Tallenna analyysi tulos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_analysis_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            self.logger.info(f"💾 Analyysi tulos tallennettu: {filename}")
            
        except Exception as e:
            self.logger.error(f"Virhe analyysi tuloksen tallentamisessa: {e}")
    
    async def run_continuous_trading(self):
        """Aja jatkuvaa tradingia"""
        self.logger.info("🚀 Käynnistetään jatkuva trading...")
        self.is_running = True
        
        try:
            while self.is_running:
                # Suorita analyysi sykli
                result = await self.run_full_analysis_cycle()
                
                # Päivitä position hinnat (mock)
                await self.update_position_prices()
                
                # Odota seuraavaa sykliä
                await asyncio.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Trading pysäytetty käyttäjän toimesta")
        except Exception as e:
            self.logger.error(f"Virhe jatkuvassa tradingissa: {e}")
        finally:
            self.is_running = False
            self.logger.info("🛑 Trading lopetettu")
    
    async def update_position_prices(self):
        """Päivitä position hinnat (mock)"""
        try:
            if not self.risk_engine.positions:
                return
            
            # Mock hinta päivitykset
            price_updates = {}
            for token_symbol in self.risk_engine.positions.keys():
                # Simuloi hinta muutosta
                current_price = self.risk_engine.positions[token_symbol].current_price
                change = np.random.normal(0, 0.02)  # 2% keskimääräinen muutos
                new_price = current_price * (1 + change)
                price_updates[token_symbol] = new_price
            
            self.risk_engine.update_position_prices(price_updates)
            
        except Exception as e:
            self.logger.error(f"Virhe position hintojen päivityksessä: {e}")
    
    def stop_trading(self):
        """Pysäytä trading"""
        self.is_running = False
        self.logger.info("⏹️ Trading pysäytetty")
    
    def get_bot_status(self) -> Dict:
        """Hae bot tila"""
        return {
            "is_running": self.is_running,
            "total_scans": self.total_scans,
            "total_signals": self.total_signals,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "success_rate": (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            "portfolio_summary": self.risk_engine.get_portfolio_summary(),
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None
        }

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Pääfunktio"""
    print("🚀 NextGen Trading Bot käynnistyy...")
    print("=" * 80)
    
    # Luo trading bot
    bot = NextGenTradingBot(initial_capital=10000.0)
    
    # Suorita yksi analyysi sykli
    print("🔄 Suoritetaan analyysi sykli...")
    result = await bot.run_full_analysis_cycle()
    
    if result["status"] == "success":
        print(f"✅ Analyysi onnistui!")
        print(f"   Tokenia analysoitu: {result['tokens_analyzed']}")
        print(f"   Signaalia generoitu: {result['signals_generated']}")
        print(f"   Kauppaa suoritettu: {result['trades_executed']}")
        
        # Näytä portfolio yhteenveto
        portfolio = result["portfolio_summary"]
        print(f"\n📊 PORTFOLIO YHTEENVETO:")
        print(f"   Portfolio arvo: ${portfolio['portfolio_value']:.2f}")
        print(f"   Nykyinen pääoma: ${portfolio['current_capital']:.2f}")
        print(f"   Kokonais exposure: ${portfolio['total_exposure']:.2f}")
        print(f"   Max drawdown: {portfolio['max_drawdown']:.2%}")
        print(f"   Avoimia positioneita: {len(portfolio['open_positions'])}")
        
        # Näytä avoimet positionit
        if portfolio['open_positions']:
            print(f"\n📈 AVOIMET POSITIONIT:")
            for token, pos in portfolio['open_positions'].items():
                print(f"   {token}: {pos['quantity']:.6f} @ ${pos['current_price']:.6f}")
                print(f"      P&L: ${pos['unrealized_pnl']:.2f} ({pos['pnl_percentage']:.1f}%)")
        
    else:
        print(f"❌ Analyysi epäonnistui: {result.get('error', 'Tuntematon virhe')}")
    
    # Näytä bot tila
    status = bot.get_bot_status()
    print(f"\n🤖 BOT TILA:")
    print(f"   Skannauksia: {status['total_scans']}")
    print(f"   Signaaleja: {status['total_signals']}")
    print(f"   Kauppoja: {status['total_trades']}")
    print(f"   Onnistumisprosentti: {status['success_rate']:.1f}%")
    
    print("=" * 80)
    print("✅ NextGen Trading Bot valmis!")

if __name__ == "__main__":
    asyncio.run(main())
