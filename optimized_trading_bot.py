#!/usr/bin/env python3
"""
Optimized Trading Bot - Toteuttaa kehitetyn strategian
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import os
from dotenv import load_dotenv

# Lataa environment variables
load_dotenv()

# Konfiguroi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OptimizedToken:
    """Optimoitu token"""
    symbol: str
    name: str
    address: str
    price: float
    market_cap: float
    volume_24h: float
    price_change_1h: float
    price_change_24h: float
    age_minutes: float
    liquidity: float
    holders: int
    fresh_holders_1d: float
    top_10_percent: float
    dev_tokens_percent: float
    social_score: float
    technical_score: float
    momentum_score: float
    risk_score: float
    overall_score: float
    timestamp: str

class OptimizedTradingBot:
    """Optimoitu trading bot"""
    
    def __init__(self):
        self.positions = {}
        self.portfolio_value = 10000.0
        self.available_cash = 10000.0
        self.total_trades = 0
        self.successful_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Strategia parametrit
        self.strategy_params = {
            "entry_threshold": 0.75,
            "exit_threshold": 0.30,
            "position_size": 0.012,  # 1.2%
            "stop_loss": 0.15,  # 15%
            "take_profit": 0.30,  # 30%
            "max_positions": 15,
            "max_drawdown": 0.20,  # 20%
            "daily_loss_limit": 0.05,  # 5%
            "max_hold_time": 15,  # minutes
            "correlation_limit": 0.7
        }
        
        # Performance tracking
        self.performance_metrics = {
            "total_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0
        }
        
    async def run_optimized_cycle(self) -> Dict[str, Any]:
        """Suorita optimoitu trading sykli"""
        logger.info("🚀 Aloitetaan optimoitu trading sykli...")
        
        try:
            # 1. Skannaa ultra-fresh tokenit
            tokens = await self._scan_ultra_fresh_tokens()
            logger.info(f"✅ Löydettiin {len(tokens)} ultra-fresh tokenia")
            
            # 2. Analysoi tokenit
            analyzed_tokens = await self._analyze_tokens(tokens)
            logger.info(f"✅ Analysoitu {len(analyzed_tokens)} tokenia")
            
            # 3. Generoi signaalit
            signals = await self._generate_optimized_signals(analyzed_tokens)
            logger.info(f"✅ Generoitu {len(signals)} signaalia")
            
            # 4. Suorita kaupat
            trades_executed = await self._execute_optimized_trades(signals)
            logger.info(f"✅ Suoritettu {trades_executed} kauppaa")
            
            # 5. Päivitä performance
            await self._update_performance_metrics()
            
            # 6. Tallenna tulokset
            results = {
                "timestamp": datetime.now().isoformat(),
                "tokens_scanned": len(tokens),
                "tokens_analyzed": len(analyzed_tokens),
                "signals_generated": len(signals),
                "trades_executed": trades_executed,
                "portfolio_value": self.portfolio_value,
                "available_cash": self.available_cash,
                "total_pnl": self.total_pnl,
                "daily_pnl": self.daily_pnl,
                "positions": len(self.positions),
                "performance_metrics": self.performance_metrics
            }
            
            self._save_results(results)
            
            logger.info("✅ Optimoitu trading sykli valmis!")
            return results
            
        except Exception as e:
            logger.error(f"❌ Virhe optimoidussa trading syklissä: {e}")
            raise
    
    async def _scan_ultra_fresh_tokens(self) -> List[OptimizedToken]:
        """Skannaa ultra-fresh tokenit"""
        # Simuloi ultra-fresh tokenien skannaus
        tokens = []
        
        # Generoi mock ultra-fresh tokenit
        for i in range(8):
            token = OptimizedToken(
                symbol=f"TOKEN{i+1}",
                name=f"Ultra Fresh Token {i+1}",
                address=f"mock_address_{i+1}",
                price=0.0001 * (i + 1),
                market_cap=20000 + (i * 10000),
                volume_24h=50000 + (i * 20000),
                price_change_1h=50 + (i * 10),
                price_change_24h=100 + (i * 20),
                age_minutes=1 + (i * 0.5),
                liquidity=10000 + (i * 5000),
                holders=1000 + (i * 200),
                fresh_holders_1d=5 + (i * 1),
                top_10_percent=25 + (i * 2),
                dev_tokens_percent=0.5 + (i * 0.1),
                social_score=7 + (i * 0.5),
                technical_score=8 + (i * 0.3),
                momentum_score=8.5 + (i * 0.2),
                risk_score=6 + (i * 0.5),
                overall_score=7.5 + (i * 0.3),
                timestamp=datetime.now().isoformat()
            )
            tokens.append(token)
        
        return tokens
    
    async def _analyze_tokens(self, tokens: List[OptimizedToken]) -> List[Dict[str, Any]]:
        """Analysoi tokenit optimoidulla metodilla"""
        analyzed = []
        
        for token in tokens:
            # Laske optimoidut skoorit
            analysis = {
                "token": token,
                "entry_score": self._calculate_entry_score(token),
                "exit_score": self._calculate_exit_score(token),
                "risk_score": self._calculate_risk_score(token),
                "momentum_score": self._calculate_momentum_score(token),
                "social_score": self._calculate_social_score(token),
                "technical_score": self._calculate_technical_score(token),
                "overall_score": self._calculate_overall_score(token),
                "recommendation": self._get_recommendation(token),
                "confidence": self._calculate_confidence(token)
            }
            
            analyzed.append(analysis)
        
        return analyzed
    
    def _calculate_entry_score(self, token: OptimizedToken) -> float:
        """Laske entry skoori"""
        score = 0.0
        
        # Age score (1-5 min = optimal)
        if 1 <= token.age_minutes <= 5:
            score += 2.0
        elif token.age_minutes < 1:
            score += 1.5
        else:
            score += 1.0
        
        # Market cap score (20K-100K = optimal)
        if 20000 <= token.market_cap <= 100000:
            score += 2.0
        elif token.market_cap < 20000:
            score += 1.5
        else:
            score += 1.0
        
        # Volume score
        if token.volume_24h > 50000:
            score += 2.0
        elif token.volume_24h > 20000:
            score += 1.5
        else:
            score += 1.0
        
        # Price momentum score
        if token.price_change_1h > 50:
            score += 2.0
        elif token.price_change_1h > 25:
            score += 1.5
        else:
            score += 1.0
        
        # Social score
        if token.social_score > 7:
            score += 1.5
        elif token.social_score > 5:
            score += 1.0
        else:
            score += 0.5
        
        return min(score, 10.0)
    
    def _calculate_exit_score(self, token: OptimizedToken) -> float:
        """Laske exit skoori"""
        score = 0.0
        
        # Profit target reached
        if hasattr(token, 'current_profit') and token.current_profit >= 0.30:
            score += 3.0
        
        # Stop loss triggered
        if hasattr(token, 'current_profit') and token.current_profit <= -0.15:
            score += 3.0
        
        # Time exit
        if hasattr(token, 'hold_time') and token.hold_time >= 15:
            score += 2.0
        
        # Technical breakdown
        if token.technical_score < 5:
            score += 2.0
        
        # Volume decline
        if hasattr(token, 'volume_decline') and token.volume_decline > 0.5:
            score += 2.0
        
        return min(score, 10.0)
    
    def _calculate_risk_score(self, token: OptimizedToken) -> float:
        """Laske riski skoori"""
        score = 0.0
        
        # Market cap risk
        if token.market_cap < 10000:
            score += 2.0
        elif token.market_cap < 50000:
            score += 1.0
        
        # Liquidity risk
        if token.liquidity < 5000:
            score += 2.0
        elif token.liquidity < 20000:
            score += 1.0
        
        # Holder concentration risk
        if token.top_10_percent > 50:
            score += 2.0
        elif token.top_10_percent > 35:
            score += 1.0
        
        # Dev tokens risk
        if token.dev_tokens_percent > 5:
            score += 2.0
        elif token.dev_tokens_percent > 2:
            score += 1.0
        
        # Volatility risk
        if token.price_change_1h > 100:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_momentum_score(self, token: OptimizedToken) -> float:
        """Laske momentum skoori"""
        score = 0.0
        
        # Price momentum
        if token.price_change_1h > 50:
            score += 3.0
        elif token.price_change_1h > 25:
            score += 2.0
        elif token.price_change_1h > 10:
            score += 1.0
        
        # Volume momentum
        if token.volume_24h > 100000:
            score += 2.0
        elif token.volume_24h > 50000:
            score += 1.5
        elif token.volume_24h > 20000:
            score += 1.0
        
        # Fresh holders momentum
        if token.fresh_holders_1d > 10:
            score += 2.0
        elif token.fresh_holders_1d > 5:
            score += 1.5
        elif token.fresh_holders_1d > 3:
            score += 1.0
        
        # Age momentum (fresher = better)
        if token.age_minutes < 2:
            score += 2.0
        elif token.age_minutes < 5:
            score += 1.5
        else:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_social_score(self, token: OptimizedToken) -> float:
        """Laske sosiaalinen skoori"""
        return token.social_score
    
    def _calculate_technical_score(self, token: OptimizedToken) -> float:
        """Laske tekninen skoori"""
        return token.technical_score
    
    def _calculate_overall_score(self, token: OptimizedToken) -> float:
        """Laske kokonaisskoori"""
        entry_score = self._calculate_entry_score(token)
        momentum_score = self._calculate_momentum_score(token)
        social_score = self._calculate_social_score(token)
        technical_score = self._calculate_technical_score(token)
        risk_score = self._calculate_risk_score(token)
        
        # Painotettu keskiarvo
        overall = (
            entry_score * 0.25 +
            momentum_score * 0.25 +
            social_score * 0.20 +
            technical_score * 0.20 +
            (10 - risk_score) * 0.10  # Risk score käännetty
        )
        
        return min(overall, 10.0)
    
    def _get_recommendation(self, token: OptimizedToken) -> str:
        """Hae suositus"""
        overall_score = self._calculate_overall_score(token)
        
        if overall_score >= 8.0:
            return "STRONG_BUY"
        elif overall_score >= 7.0:
            return "BUY"
        elif overall_score >= 6.0:
            return "HOLD"
        elif overall_score >= 5.0:
            return "WEAK_SELL"
        else:
            return "SELL"
    
    def _calculate_confidence(self, token: OptimizedToken) -> float:
        """Laske luottamus"""
        overall_score = self._calculate_overall_score(token)
        risk_score = self._calculate_risk_score(token)
        
        # Korkea skoori + matala riski = korkea luottamus
        confidence = (overall_score / 10.0) * (1 - risk_score / 10.0)
        
        return min(confidence, 1.0)
    
    async def _generate_optimized_signals(self, analyzed_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generoi optimoidut signaalit"""
        signals = []
        
        # Tarkista olemassa olevat positiot
        for symbol, position in self.positions.items():
            # Generoi SELL signaalit olemassa oleville positiioille
            if self._should_sell_position(position):
                signal = {
                    "token": position["token"],
                    "signal_type": "SELL",
                    "confidence": 0.8,
                    "reason": "Optimized exit criteria met",
                    "entry_price": position["entry_price"],
                    "current_price": position["current_price"],
                    "pnl": position["pnl"],
                    "pnl_percentage": position["pnl_percentage"]
                }
                signals.append(signal)
        
        # Generoi BUY signaalit uusille tokeneille
        for analysis in analyzed_tokens:
            token = analysis["token"]
            
            # Ohita jos position jo olemassa
            if token.symbol in self.positions:
                continue
            
            # Tarkista entry kriteerit
            if self._should_buy_token(analysis):
                signal = {
                    "token": token,
                    "signal_type": "BUY",
                    "confidence": analysis["confidence"],
                    "entry_score": analysis["entry_score"],
                    "overall_score": analysis["overall_score"],
                    "risk_score": analysis["risk_score"],
                    "recommendation": analysis["recommendation"],
                    "target_price": token.price * 1.30,  # 30% target
                    "stop_loss": token.price * 0.85,  # 15% stop loss
                    "position_size": self._calculate_position_size(token, analysis["confidence"])
                }
                signals.append(signal)
        
        return signals
    
    def _should_sell_position(self, position: Dict[str, Any]) -> bool:
        """Tarkista pitäisikö myydä position"""
        # Profit target
        if position["pnl_percentage"] >= 30:
            return True
        
        # Stop loss
        if position["pnl_percentage"] <= -15:
            return True
        
        # Time exit
        if position["hold_time"] >= 15:
            return True
        
        # Technical breakdown
        if position["technical_score"] < 5:
            return True
        
        return False
    
    def _should_buy_token(self, analysis: Dict[str, Any]) -> bool:
        """Tarkista pitäisikö ostaa token"""
        token = analysis["token"]
        
        # Peruskriteerit
        if not (1 <= token.age_minutes <= 5):
            return False
        
        if not (20000 <= token.market_cap <= 100000):
            return False
        
        if not (token.price_change_1h >= 25):
            return False
        
        if not (3 <= token.fresh_holders_1d <= 12):
            return False
        
        if not (token.top_10_percent <= 35):
            return False
        
        if not (token.dev_tokens_percent <= 1):
            return False
        
        # Skoori kriteerit
        if analysis["overall_score"] < 7.0:
            return False
        
        if analysis["confidence"] < 0.7:
            return False
        
        if analysis["risk_score"] > 7.0:
            return False
        
        return True
    
    def _calculate_position_size(self, token: OptimizedToken, confidence: float) -> float:
        """Laske position koko"""
        base_size = self.available_cash * self.strategy_params["position_size"]
        
        # Säätö luottamuksen mukaan
        confidence_adjustment = confidence
        
        # Säätö riskin mukaan
        risk_score = self._calculate_risk_score(token)
        risk_adjustment = 1 - (risk_score / 10.0)
        
        # Säätö volatiliteetin mukaan
        volatility_adjustment = 1.0
        if token.price_change_1h > 100:
            volatility_adjustment = 0.8
        elif token.price_change_1h > 50:
            volatility_adjustment = 0.9
        
        # Laske lopullinen koko
        final_size = base_size * confidence_adjustment * risk_adjustment * volatility_adjustment
        
        # Rajoita koko
        final_size = min(final_size, self.available_cash * 0.05)  # Max 5%
        final_size = max(final_size, 10.0)  # Min $10
        
        return final_size
    
    async def _execute_optimized_trades(self, signals: List[Dict[str, Any]]) -> int:
        """Suorita optimoidut kaupat"""
        trades_executed = 0
        
        for signal in signals:
            try:
                if signal["signal_type"] == "BUY":
                    if await self._execute_buy_trade(signal):
                        trades_executed += 1
                elif signal["signal_type"] == "SELL":
                    if await self._execute_sell_trade(signal):
                        trades_executed += 1
            except Exception as e:
                logger.error(f"Virhe kaupan suorittamisessa: {e}")
                continue
        
        return trades_executed
    
    async def _execute_buy_trade(self, signal: Dict[str, Any]) -> bool:
        """Suorita ostokauppa"""
        token = signal["token"]
        
        # Tarkista rajoitukset
        if len(self.positions) >= self.strategy_params["max_positions"]:
            logger.warning(f"Ei voi ostaa {token.symbol}: Liikaa positioita")
            return False
        
        if self.available_cash < signal["position_size"]:
            logger.warning(f"Ei voi ostaa {token.symbol}: Ei tarpeeksi käteistä")
            return False
        
        # Suorita kauppa
        position_size = signal["position_size"]
        quantity = position_size / token.price
        
        self.positions[token.symbol] = {
            "token": token,
            "entry_price": token.price,
            "current_price": token.price,
            "quantity": quantity,
            "position_value": position_size,
            "entry_time": datetime.now(),
            "hold_time": 0,
            "pnl": 0.0,
            "pnl_percentage": 0.0,
            "technical_score": token.technical_score,
            "social_score": token.social_score,
            "overall_score": signal["overall_score"]
        }
        
        self.available_cash -= position_size
        self.total_trades += 1
        
        logger.info(f"✅ Ostettu {token.symbol}: {quantity:.2f} @ ${token.price:.6f} (${position_size:.2f})")
        return True
    
    async def _execute_sell_trade(self, signal: Dict[str, Any]) -> bool:
        """Suorita myyntikauppa"""
        token = signal["token"]
        
        if token.symbol not in self.positions:
            return False
        
        position = self.positions[token.symbol]
        
        # Laske PnL
        pnl = (token.price - position["entry_price"]) * position["quantity"]
        pnl_percentage = (pnl / position["position_value"]) * 100
        
        # Päivitä cash
        self.available_cash += position["position_value"] + pnl
        self.total_pnl += pnl
        self.daily_pnl += pnl
        
        if pnl > 0:
            self.successful_trades += 1
        
        # Poista position
        del self.positions[token.symbol]
        
        logger.info(f"✅ Myyty {token.symbol}: PnL ${pnl:.2f} ({pnl_percentage:+.1f}%)")
        return True
    
    async def _update_performance_metrics(self):
        """Päivitä performance-metriikat"""
        if self.total_trades > 0:
            self.performance_metrics["win_rate"] = self.successful_trades / self.total_trades
        
        self.performance_metrics["total_return"] = self.total_pnl / 10000.0
        
        # Laske drawdown
        if self.total_pnl < 0:
            self.current_drawdown = abs(self.total_pnl) / 10000.0
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        self.performance_metrics["max_drawdown"] = self.max_drawdown
    
    def _save_results(self, results: Dict[str, Any]):
        """Tallenna tulokset"""
        filename = f"optimized_trading_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Tulokset tallennettu: {filename}")
    
    def print_performance_summary(self):
        """Tulosta performance-yhteenveto"""
        print("\n" + "="*80)
        print("📊 OPTIMOIDUN BOTIN PERFORMANCE")
        print("="*80)
        print(f"💰 Portfolio arvo: ${self.portfolio_value:,.2f}")
        print(f"💵 Käteinen: ${self.available_cash:,.2f}")
        print(f"📈 Kokonais PnL: ${self.total_pnl:,.2f}")
        print(f"📊 Päivittäinen PnL: ${self.daily_pnl:,.2f}")
        print(f"🎯 Positiot: {len(self.positions)}")
        print(f"📊 Kokonaiskauppoja: {self.total_trades}")
        print(f"✅ Onnistuneita: {self.successful_trades}")
        print(f"📈 Voittoprosentti: {self.performance_metrics['win_rate']:.1%}")
        print(f"📊 Kokonaistuotto: {self.performance_metrics['total_return']:.1%}")
        print(f"📉 Max drawdown: {self.performance_metrics['max_drawdown']:.1%}")
        print("="*80)

async def main():
    """Pääfunktio"""
    try:
        # Luo optimoitu bot
        bot = OptimizedTradingBot()
        
        # Suorita optimoitu sykli
        results = await bot.run_optimized_cycle()
        
        # Tulosta yhteenveto
        bot.print_performance_summary()
        
        print(f"\n🎯 SYKLIN TULOKSET:")
        print(f"  • Skannattu: {results['tokens_scanned']} tokenia")
        print(f"  • Analysoitu: {results['tokens_analyzed']} tokenia")
        print(f"  • Signaalit: {results['signals_generated']} kpl")
        print(f"  • Kaupat: {results['trades_executed']} kpl")
        
    except Exception as e:
        logger.error(f"❌ Virhe optimoidussa botissa: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
