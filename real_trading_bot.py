import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import asdict

from real_solana_token_scanner import RealSolanaTokenScanner, RealSolanaToken
from technical_analysis_engine import TechnicalAnalysisEngine
from risk_management_engine import RiskManagementEngine
from telegram_bot_integration import TelegramBot

class RealNextGenTradingBot:
    def __init__(self, telegram_bot: Optional[TelegramBot] = None):
        self.logger = logging.getLogger(__name__)
        self.telegram_bot = telegram_bot
        
        # Komponentit
        self.scanner = None
        self.technical_engine = TechnicalAnalysisEngine()
        self.risk_engine = RiskManagementEngine()
        
        # Portfolio
        self.positions = {}
        self.portfolio_value = 10000.0  # $10,000 alkuperäinen portfolio
        self.available_cash = 10000.0
        
        # Tilastot
        self.total_trades = 0
        self.successful_trades = 0
        self.total_pnl = 0.0
        
        # OPTIMOIDUT STRATEGIA PARAMETRIT (Agentti-tiimin kehittämä)
        self.strategy_params = {
            "entry_threshold": 0.75,      # 75% luottamus entryyn
            "exit_threshold": 0.30,       # 30% voittotavoite
            "position_size": 0.012,       # 1.2% portfolio:sta per trade
            "stop_loss": 0.15,            # 15% stop loss
            "take_profit": 0.30,          # 30% take profit
            "max_positions": 15,          # Max 15 positiota
            "max_drawdown": 0.20,         # 20% max drawdown
            "daily_loss_limit": 0.05,     # 5% päivittäinen tappioraja
            "max_hold_time": 15,          # 15 minuuttia max hold
            "correlation_limit": 0.7,     # 70% korrelaatioraja
            "ultra_fresh_age_min": 1,     # 1 minuutti min ikä
            "ultra_fresh_age_max": 5,     # 5 minuuttia max ikä
            "min_market_cap": 20000,      # $20K min market cap
            "max_market_cap": 100000,     # $100K max market cap
            "min_volume_spike": 3.0,      # 300% volume spike
            "min_price_momentum": 0.25,   # 25% price momentum
            "min_fresh_holders": 3.0,     # 3% fresh holders
            "max_fresh_holders": 12.0,    # 12% fresh holders
            "max_top_10_percent": 35.0,   # 35% max top 10%
            "max_dev_tokens": 1.0,        # 1% max dev tokens
            "min_technical_score": 7.0,   # 7.0 min technical score
            "min_momentum_score": 8.0,    # 8.0 min momentum score
            "max_risk_score": 7.0         # 7.0 max risk score
        }
        
        # Performance tracking
        self.performance_metrics = {
            "total_return": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "daily_pnl": 0.0,
            "current_drawdown": 0.0
        }

    async def __aenter__(self):
        self.scanner = RealSolanaTokenScanner()
        await self.scanner.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.scanner:
            await self.scanner.__aexit__(exc_type, exc_val, exc_tb)
    
    def _calculate_optimized_entry_score(self, token: RealSolanaToken) -> float:
        """Laske optimoitu entry skoori agentti-tiimin strategian mukaan"""
        score = 0.0
        
        # Age score (1-5 min = optimal)
        if self.strategy_params["ultra_fresh_age_min"] <= token.age_hours * 60 <= self.strategy_params["ultra_fresh_age_max"]:
            score += 2.0
        elif token.age_hours * 60 < self.strategy_params["ultra_fresh_age_min"]:
            score += 1.5
        else:
            score += 1.0
        
        # Market cap score (20K-100K = optimal)
        if self.strategy_params["min_market_cap"] <= token.market_cap <= self.strategy_params["max_market_cap"]:
            score += 2.0
        elif token.market_cap < self.strategy_params["min_market_cap"]:
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
        if token.price_change_1h >= self.strategy_params["min_price_momentum"] * 100:
            score += 2.0
        elif token.price_change_1h >= self.strategy_params["min_price_momentum"] * 50:
            score += 1.5
        else:
            score += 1.0
        
        # Fresh holders score
        if self.strategy_params["min_fresh_holders"] <= token.fresh_holders_1d <= self.strategy_params["max_fresh_holders"]:
            score += 1.5
        elif token.fresh_holders_1d < self.strategy_params["min_fresh_holders"]:
            score += 1.0
        else:
            score += 0.5
        
        # Top 10% holders score (pienempi = parempi)
        if token.top_10_percent <= self.strategy_params["max_top_10_percent"]:
            score += 1.5
        else:
            score += 0.5
        
        # Dev tokens score (pienempi = parempi)
        if token.dev_tokens_percent <= self.strategy_params["max_dev_tokens"]:
            score += 1.5
        else:
            score += 0.5
        
        return min(score, 10.0)
    
    def _calculate_optimized_risk_score(self, token: RealSolanaToken) -> float:
        """Laske optimoitu riski skoori"""
        score = 0.0
        
        # Market cap risk
        if token.market_cap < self.strategy_params["min_market_cap"]:
            score += 2.0
        elif token.market_cap < self.strategy_params["min_market_cap"] * 2.5:
            score += 1.0
        
        # Liquidity risk (simuloi)
        liquidity = token.market_cap * 0.1  # Simuloi liquidity
        if liquidity < 5000:
            score += 2.0
        elif liquidity < 20000:
            score += 1.0
        
        # Holder concentration risk
        if token.top_10_percent > 50:
            score += 2.0
        elif token.top_10_percent > self.strategy_params["max_top_10_percent"]:
            score += 1.0
        
        # Dev tokens risk
        if token.dev_tokens_percent > 5:
            score += 2.0
        elif token.dev_tokens_percent > self.strategy_params["max_dev_tokens"] * 2:
            score += 1.0
        
        # Volatility risk
        if token.price_change_1h > 100:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_optimized_momentum_score(self, token: RealSolanaToken) -> float:
        """Laske optimoitu momentum skoori"""
        score = 0.0
        
        # Price momentum
        if token.price_change_1h >= self.strategy_params["min_price_momentum"] * 200:
            score += 3.0
        elif token.price_change_1h >= self.strategy_params["min_price_momentum"] * 100:
            score += 2.0
        elif token.price_change_1h >= self.strategy_params["min_price_momentum"] * 50:
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
        age_minutes = token.age_hours * 60
        if age_minutes < 2:
            score += 2.0
        elif age_minutes < 5:
            score += 1.5
        else:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_optimized_overall_score(self, token: RealSolanaToken) -> float:
        """Laske optimoitu kokonaisskoori"""
        entry_score = self._calculate_optimized_entry_score(token)
        momentum_score = self._calculate_optimized_momentum_score(token)
        social_score = token.social_score
        technical_score = token.technical_score
        risk_score = self._calculate_optimized_risk_score(token)
        
        # Painotettu keskiarvo optimoidun strategian mukaan
        overall = (
            entry_score * 0.25 +           # 25% entry kriteerit
            momentum_score * 0.25 +        # 25% momentum
            social_score * 0.20 +          # 20% sosiaalinen
            technical_score * 0.20 +       # 20% tekninen
            (10 - risk_score) * 0.10       # 10% riski (käännetty)
        )
        
        return min(overall, 10.0)
    
    def _should_buy_token_optimized(self, token: RealSolanaToken) -> bool:
        """Tarkista pitäisikö ostaa token optimoidun strategian mukaan"""
        
        # Peruskriteerit
        age_minutes = token.age_hours * 60
        if not (self.strategy_params["ultra_fresh_age_min"] <= age_minutes <= self.strategy_params["ultra_fresh_age_max"]):
            return False
        
        if not (self.strategy_params["min_market_cap"] <= token.market_cap <= self.strategy_params["max_market_cap"]):
            return False
        
        if not (token.price_change_1h >= self.strategy_params["min_price_momentum"] * 100):
            return False
        
        if not (self.strategy_params["min_fresh_holders"] <= token.fresh_holders_1d <= self.strategy_params["max_fresh_holders"]):
            return False
        
        if not (token.top_10_percent <= self.strategy_params["max_top_10_percent"]):
            return False
        
        if not (token.dev_tokens_percent <= self.strategy_params["max_dev_tokens"]):
            return False
        
        # Skoori kriteerit
        overall_score = self._calculate_optimized_overall_score(token)
        if overall_score < self.strategy_params["min_technical_score"]:
            return False
        
        if token.technical_score < self.strategy_params["min_technical_score"]:
            return False
        
        if token.momentum_score < self.strategy_params["min_momentum_score"]:
            return False
        
        risk_score = self._calculate_optimized_risk_score(token)
        if risk_score > self.strategy_params["max_risk_score"]:
            return False
        
        return True
    
    def _should_sell_position_optimized(self, position: Dict) -> bool:
        """Tarkista pitäisikö myydä position optimoidun strategian mukaan"""
        
        # Profit target
        if position["pnl_percentage"] >= self.strategy_params["take_profit"] * 100:
            return True
        
        # Stop loss
        if position["pnl_percentage"] <= -self.strategy_params["stop_loss"] * 100:
            return True
        
        # Time exit
        if position["hold_time"] >= self.strategy_params["max_hold_time"]:
            return True
        
        # Technical breakdown
        if position.get("technical_score", 5) < 5:
            return True
        
        return False
    
    def _calculate_optimized_position_size(self, token: RealSolanaToken, confidence: float) -> float:
        """Laske optimoitu position koko"""
        base_size = self.available_cash * self.strategy_params["position_size"]
        
        # Säätö luottamuksen mukaan
        confidence_adjustment = confidence
        
        # Säätö riskin mukaan
        risk_score = self._calculate_optimized_risk_score(token)
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
    
    def _update_performance_metrics(self):
        """Päivitä performance-metriikat"""
        if self.total_trades > 0:
            self.performance_metrics["win_rate"] = self.successful_trades / self.total_trades
        
        self.performance_metrics["total_return"] = self.total_pnl / 10000.0
        
        # Laske drawdown
        if self.total_pnl < 0:
            self.performance_metrics["current_drawdown"] = abs(self.total_pnl) / 10000.0
            self.performance_metrics["max_drawdown"] = max(
                self.performance_metrics["max_drawdown"], 
                self.performance_metrics["current_drawdown"]
            )
        
        # Laske päivittäinen PnL
        self.performance_metrics["daily_pnl"] = self.total_pnl

    async def run_analysis_cycle(self) -> Dict:
        """Suorita analyysi sykli oikeilla tokeneilla"""
        self.logger.info("🔄 Aloitetaan oikea analyysi sykli...")
        
        try:
            # 1. Skannaa oikeita tokeneita
            tokens = await self.scanner.scan_new_tokens()
            
            if not tokens:
                self.logger.warning("Ei löytynyt oikeita tokeneita")
                return {
                    "tokens_found": 0,
                    "signals_generated": 0,
                    "trades_executed": 0,
                    "success_rate": 0.0
                }
            
            # 2. Analysoi jokainen token
            analyzed_tokens = []
            for token in tokens:
                try:
                    # Analysoi token
                    technical_analysis = self.technical_engine.analyze_token(token)
                    
                    # Päivitä token skoorit
                    token.technical_score = technical_analysis.get("momentum_score", 5.0)
                    token.overall_score = (token.social_score + token.technical_score + token.momentum_score) / 3
                    
                    analyzed_tokens.append({
                        "token": token,
                        "technical_analysis": technical_analysis
                    })
                    
                except Exception as e:
                    self.logger.error(f"Virhe tokenin {token.symbol} analyysissä: {e}")
                    continue
            
            # 3. Generoi trading signaalit
            signals = self._generate_trading_signals(analyzed_tokens)
            
            # 4. Suorita kaupat
            trades_executed = await self._execute_trades(signals)
            
            # Päivitä performance metrics
            self._update_performance_metrics()
            
            # 5. Päivitä tilastot
            self._update_statistics()
            
            # 6. Lähetä Telegram viestit
            if self.telegram_bot:
                await self._send_trading_notifications(analyzed_tokens, signals, trades_executed)
            
            # 7. Tallenna analyysi
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "strategy": "Ultra-Fresh Token Master Strategy (Optimized)",
                "strategy_version": "1.0.0",
                "tokens_found": len(tokens),
                "tokens_analyzed": len(analyzed_tokens),
                "signals_generated": len(signals),
                "trades_executed": trades_executed,
                "success_rate": (self.successful_trades / max(1, self.total_trades)) * 100,
                "portfolio_value": self.portfolio_value,
                "available_cash": self.available_cash,
                "total_pnl": self.total_pnl,
                "positions": {k: v for k, v in self.positions.items()},
                "tokens": [asdict(token) for token in tokens],
                "signals": signals,
                "performance_metrics": self.performance_metrics,
                "strategy_params": self.strategy_params
            }
            
            # Tallenna analyysi tiedostoon
            filename = f"real_trading_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(analysis_result, f, indent=2, default=str)
            
            self.logger.info(f"💾 Oikea analyysi tulos tallennettu: {filename}")
            self.logger.info(f"✅ Oikea analyysi sykli valmis: {len(tokens)} tokenia, {len(signals)} signaalia")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Virhe analyysi syklissä: {e}")
            return {
                "tokens_found": 0,
                "signals_generated": 0,
                "trades_executed": 0,
                "success_rate": 0.0,
                "error": str(e)
            }

    def _generate_trading_signals(self, analyzed_tokens: List[Dict]) -> List[Dict]:
        """Generoi trading signaalit oikeille tokeneille"""
        signals = []
        
        # Tarkista olemassa olevat positiot myyntiä varten
        for symbol, position in self.positions.items():
            try:
                # Hae token data
                token_data = next((t for t in analyzed_tokens if t["token"].symbol == symbol), None)
                if not token_data:
                    # Jos token dataa ei löydy, käytä vanhaa hintaa ja generoi SELL signaali
                    # Simuloi hintamuutosta
                    import random
                    price_change = random.uniform(-30, 30)  # -30% to +30%
                    current_price = position["entry_price"] * (1 + price_change / 100)
                    
                    # Laske PnL
                    current_pnl = (current_price - position["entry_price"]) * position["quantity"]
                    pnl_percentage = (current_pnl / position["position_value"]) * 100
                    
                    # SELL signaalit jos tappio yli 15% tai voitto yli 30%
                    if pnl_percentage >= 30 or pnl_percentage <= -15:
                        # Luo mock token
                        from real_solana_token_scanner import RealSolanaToken
                        mock_token = RealSolanaToken(
                            symbol=symbol,
                            name=position.get("token_name", symbol),
                            address=position.get("token_address", "mock"),
                            price=current_price,
                            market_cap=position.get("market_cap", 50000),
                            volume_24h=position.get("market_cap", 50000) * 0.8,
                            price_change_1h=price_change,
                            price_change_24h=price_change * 2,
                            price_change_7d=price_change * 3,
                            liquidity=position.get("market_cap", 50000) * 0.1,
                            holders=1000,
                            fresh_holders_1d=5.0,
                            fresh_holders_7d=15.0,
                            social_score=5.0,
                            technical_score=5.0,
                            momentum_score=5.0,
                            risk_score=5.0,
                            age_hours=0.1,
                            overall_score=5.0,
                            top_10_percent=25.0,
                            dev_tokens_percent=0.5,
                            timestamp="2025-09-12T13:00:00Z"
                        )
                        
                        signal = {
                            "token": mock_token,
                            "signal_type": "SELL",
                            "confidence": 0.8 if pnl_percentage >= 30 else 0.6,
                            "entry_price": position["entry_price"],
                            "current_price": current_price,
                            "target_price": current_price,
                            "stop_loss": current_price,
                            "pnl": current_pnl,
                            "pnl_percentage": pnl_percentage,
                            "reasoning": f"SELL: {symbol} PnL: {pnl_percentage:+.1f}%, Price change: {price_change:+.1f}%"
                        }
                        signals.append(signal)
                    continue
                
                token = token_data["token"]
                technical = token_data["technical_analysis"]
                
                # Laske PnL
                current_pnl = (token.price - position["entry_price"]) * position["quantity"]
                pnl_percentage = (current_pnl / position["position_value"]) * 100
                
                # SELL signaalit olemassa oleville positiioille OPTIMOIDULLA STRATEGIALLA
                if (pnl_percentage >= self.strategy_params["take_profit"] * 100 or  # Optimized profit target
                    pnl_percentage <= -self.strategy_params["stop_loss"] * 100 or  # Optimized stop loss
                    token.overall_score <= 3.0 or  # Matala skoori
                    token.price_change_1h <= -25):  # 25% lasku 1H
                    
                    signal = {
                        "token": token,
                        "signal_type": "SELL",
                        "confidence": 0.8 if pnl_percentage >= 30 else 0.6,
                        "entry_price": position["entry_price"],
                        "current_price": token.price,
                        "target_price": token.price,
                        "stop_loss": token.price,
                        "pnl": current_pnl,
                        "pnl_percentage": pnl_percentage,
                        "reasoning": f"SELL: {token.symbol} PnL: {pnl_percentage:+.1f}%, Skoori: {token.overall_score:.1f}/10, 1H: {token.price_change_1h:+.1f}%"
                    }
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Virhe SELL signaalin generoinnissa {symbol}: {e}")
                continue
        
        # Generoi BUY signaalit uusille tokeneille
        for item in analyzed_tokens:
            token = item["token"]
            technical = item["technical_analysis"]
            
            try:
                # Ohita jos position jo olemassa
                if token.symbol in self.positions:
                    continue
                
                # OPTIMOIDUT Ultra-fresh token signaali kriteerit (Agentti-tiimin strategia)
                # BUY signaalit - Ultra-fresh tokenit, korkea momentum OPTIMOIDULLA STRATEGIALLA
                if self._should_buy_token_optimized(token):
                    # Laske optimoidut skoorit
                    entry_score = self._calculate_optimized_entry_score(token)
                    overall_score = self._calculate_optimized_overall_score(token)
                    risk_score = self._calculate_optimized_risk_score(token)
                    momentum_score = self._calculate_optimized_momentum_score(token)
                    
                    # Laske luottamus
                    confidence = (overall_score / 10.0) * (1 - risk_score / 10.0)
                    
                    # Laske optimoidut hinnat
                    target_price = token.price * (1 + self.strategy_params["take_profit"])
                    stop_loss = token.price * (1 - self.strategy_params["stop_loss"])
                    
                    signal = {
                        "token": token,
                        "signal_type": "BUY",
                        "confidence": confidence,
                        "entry_score": entry_score,
                        "overall_score": overall_score,
                        "risk_score": risk_score,
                        "momentum_score": momentum_score,
                        "entry_price": token.price,
                        "target_price": target_price,
                        "stop_loss": stop_loss,
                        "position_size": self._calculate_optimized_position_size(token, confidence),
                        "strategy": "Ultra-Fresh Token Master Strategy",
                        "reasoning": f"OPTIMIZED BUY: {token.symbol} FDV: ${token.market_cap:,.0f}, +{token.price_change_1h:.0f}% 1H, Age: {token.age_hours*60:.0f}min, Fresh: {token.fresh_holders_1d:.1f}%, Top10: {token.top_10_percent:.1f}%, Dev: {token.dev_tokens_percent:.1f}%, Overall: {overall_score:.1f}/10, Risk: {risk_score:.1f}/10"
                    }
                    signals.append(signal)
                
                # SELL signaalit - Matala skoori, negatiivinen momentum
                elif (token.overall_score <= 4.0 and 
                      token.price_change_1h <= -20 and 
                      token.volume_24h < token.market_cap * 0.5):
                    
                    signal = {
                        "token": token,
                        "signal_type": "SELL",
                        "confidence": (10 - token.overall_score) / 10,
                        "entry_price": token.price,
                        "target_price": token.price * 0.8,  # 20% tappio
                        "stop_loss": token.price * 1.2,  # 20% nousu
                        "reasoning": f"SELL: {token.symbol} Skoori {token.overall_score:.1f}/10, {token.price_change_1h:.1f}% 1H, Vol: ${token.volume_24h:,.0f}"
                    }
                    signals.append(signal)
                
                # HOLD signaalit - Korkea skoori, vakaa kehitys
                elif (token.overall_score >= 7.5 and 
                      token.price_change_1h >= 0 and 
                      token.volume_24h >= token.market_cap * 1.0):
                    
                    signal = {
                        "token": token,
                        "signal_type": "HOLD",
                        "confidence": token.overall_score / 10,
                        "entry_price": token.price,
                        "target_price": token.price * 1.3,  # 30% tuotto
                        "stop_loss": token.price * 0.9,  # 10% tappio
                        "reasoning": f"HOLD: {token.symbol} Skoori {token.overall_score:.1f}/10, +{token.price_change_1h:.1f}% 1H, Vol: ${token.volume_24h:,.0f}"
                    }
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.error(f"Virhe signaalin generoinnissa tokenille {token.symbol}: {e}")
                continue
        
        return signals

    async def _execute_trades(self, signals: List[Dict]) -> int:
        """Suorita kaupat"""
        trades_executed = 0
        
        # Sulje vanhat positiot (yli 15 minuuttia) ja vapauta tilaa
        await self._close_old_positions()
        
        # Jos portfolio on täynnä, sulje vanhimmat positiot
        if len(self.positions) >= 15:
            await self._close_oldest_positions(5)  # Sulje 5 vanhinta
        
        for signal in signals:
            try:
                token = signal["token"]
                signal_type = signal["signal_type"]
                
                if signal_type == "BUY":
                    # Tarkista että ei ole jo position
                    if token.symbol in self.positions:
                        self.logger.warning(f"Ei voi avata position {token.symbol}: Position jo olemassa tokenille {token.symbol}")
                        continue
                    
                    # Rajoita position määrää (max 15)
                    if len(self.positions) >= 15:
                        self.logger.warning(f"Ei voi avata position {token.symbol}: Liikaa positioita ({len(self.positions)}/15)")
                        continue
                    
                    # Laske position koko OPTIMOIDULLA STRATEGIALLA
                    position_size = self._calculate_optimized_position_size(token, signal.get("confidence", 0.7))
                    
                    if position_size < 10:  # Min $10 position
                        continue
                    
                    # Laske quantity
                    quantity = position_size / token.price
                    
                    # Avaa position
                    self.positions[token.symbol] = {
                        "token_symbol": token.symbol,
                        "token_name": token.name,
                        "token_address": token.address,
                        "entry_price": token.price,
                        "current_price": token.price,
                        "quantity": quantity,
                        "position_value": position_size,
                        "unrealized_pnl": 0.0,
                        "entry_time": datetime.now(),
                        "risk_score": token.risk_score,
                        "age_minutes": token.age_hours * 60,
                        "market_cap": token.market_cap,
                        "target_price": signal["target_price"],
                        "stop_loss": signal["stop_loss"]
                    }
                    
                    # Päivitä cash
                    self.available_cash -= position_size
                    self.total_trades += 1
                    trades_executed += 1
                    
                    self.logger.info(f"✅ Avattu position {token.symbol}: {quantity:.6f} @ ${token.price:.6f} (Age: {token.age_hours*60:.0f}min, FDV: ${token.market_cap:,.0f})")
                    self.logger.info(f"✅ Avattu BUY position {token.symbol}: ${position_size:.2f} @ ${token.price:.6f}")
                    
                elif signal_type == "SELL":
                    # Sulje position jos olemassa
                    if token.symbol in self.positions:
                        position = self.positions[token.symbol]
                        pnl = (token.price - position["entry_price"]) * position["quantity"]
                        pnl_percentage = (pnl / position["position_value"]) * 100
                        
                        # Päivitä cash
                        self.available_cash += position["position_value"] + pnl
                        self.total_pnl += pnl
                        
                        if pnl > 0:
                            self.successful_trades += 1
                        
                        # Poista position
                        del self.positions[token.symbol]
                        trades_executed += 1
                        
                        self.logger.info(f"✅ Suljettu SELL position {token.symbol}: PnL ${pnl:.2f} ({pnl_percentage:+.1f}%)")
                        
                        # Lähetä Telegram viesti
                        if self.telegram_bot:
                            message = f"🔻 POSITION SULJETTU\n\n"
                            message += f"Token: {token.symbol}\n"
                            message += f"Entry: ${position['entry_price']:.6f}\n"
                            message += f"Exit: ${token.price:.6f}\n"
                            message += f"PnL: ${pnl:.2f} ({pnl_percentage:+.1f}%)\n"
                            message += f"Duration: {signal.get('reasoning', 'N/A')}"
                            await self.telegram_bot.send_message(message)
                        
            except Exception as e:
                self.logger.error(f"Virhe kaupan suorittamisessa {signal.get('token', {}).get('symbol', 'Unknown')}: {e}")
                continue
        
        return trades_executed

    async def _close_oldest_positions(self, count: int):
        """Sulje vanhimmat positiot"""
        if len(self.positions) < count:
            return
        
        # Lajittele positiot entry_time mukaan
        sorted_positions = sorted(
            self.positions.items(),
            key=lambda x: x[1]["entry_time"]
        )
        
        # Sulje vanhimmat
        for i in range(count):
            symbol, position = sorted_positions[i]
            await self.close_position(symbol, "Portfolio rotation")

    async def _close_old_positions(self):
        """Sulje vanhat positiot (yli 15 minuuttia)"""
        current_time = datetime.now()
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            entry_time = position["entry_time"]
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time)
            
            age_minutes = (current_time - entry_time).total_seconds() / 60
            
            # Sulje positiot yli 15 minuuttia vanhat
            if age_minutes > 15:
                positions_to_close.append(symbol)
        
        # Sulje vanhat positiot
        for symbol in positions_to_close:
            position = self.positions[symbol]
            current_price = position["current_price"]  # Käytä entry price jos ei päivitetty
            pnl = (current_price - position["entry_price"]) * position["quantity"]
            
            # Päivitä cash
            self.available_cash += position["position_value"] + pnl
            self.total_pnl += pnl
            
            if pnl > 0:
                self.successful_trades += 1
            
            # Poista position
            del self.positions[symbol]
            
            self.logger.info(f"🕐 Suljettu vanha position {symbol}: PnL ${pnl:.2f} (Age: {(current_time - position['entry_time']).total_seconds()/60:.0f}min)")

    def _update_statistics(self):
        """Päivitä tilastot"""
        # Laske portfolio arvo
        total_position_value = sum(pos["position_value"] for pos in self.positions.values())
        self.portfolio_value = self.available_cash + total_position_value
        
        # Laske success rate
        success_rate = (self.successful_trades / max(1, self.total_trades)) * 100
        
        self.logger.info(f"📊 Tilastot: {self.total_trades} kauppaa, {success_rate:.1f}% onnistunut")

    async def close_position(self, symbol: str, reason: str, current_price: float = None):
        """Sulje position"""
        if symbol not in self.positions:
            self.logger.warning(f"Position {symbol} ei löytynyt")
            return
        
        position = self.positions[symbol]
        
        # Käytä annettua hintaa tai entry hintaa
        if current_price is None:
            current_price = position["entry_price"]
        
        # Laske PnL
        pnl = (current_price - position["entry_price"]) * position["quantity"]
        pnl_percentage = (pnl / position["position_value"]) * 100
        
        # Päivitä cash
        self.available_cash += position["position_value"] + pnl
        self.total_pnl += pnl
        
        if pnl > 0:
            self.successful_trades += 1
        
        # Poista position
        del self.positions[symbol]
        
        self.logger.info(f"✅ Suljettu position {symbol}: PnL ${pnl:.2f} ({pnl_percentage:+.1f}%) - {reason}")
        
        return {
            "symbol": symbol,
            "pnl": pnl,
            "pnl_percentage": pnl_percentage,
            "reason": reason
        }

    def get_bot_status(self) -> Dict:
        """Hae botin status"""
        return {
            "positions": len(self.positions),
            "portfolio_value": self.portfolio_value,
            "available_cash": self.available_cash,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "total_pnl": self.total_pnl,
            "success_rate": (self.successful_trades / max(1, self.total_trades)) * 100
        }

    async def _send_trading_notifications(self, analyzed_tokens: List[Dict], signals: List[Dict], trades_executed: int):
        """Lähetä Telegram viestit - vain uusista kaupoista"""
        if not self.telegram_bot:
            return
        
        try:
            # Lähetä vain jos on uusia kauppoja
            if trades_executed > 0:
                message = f"🔄 Oikea Trading Sykli Valmis\n\n"
                message += f"📊 Löydetty: {len(analyzed_tokens)} tokenia\n"
                message += f"📡 Signaalit: {len(signals)} kpl\n"
                message += f"💰 Kaupat: {trades_executed} kpl\n"
                message += f"💼 Portfolio: ${self.portfolio_value:,.2f}\n"
                message += f"💵 Käteinen: ${self.available_cash:,.2f}\n"
                message += f"📈 PnL: ${self.total_pnl:,.2f}\n"
                message += f"🎯 Onnistumisprosentti: {(self.successful_trades / max(1, self.total_trades)) * 100:.1f}%"
            
                await self.telegram_bot.send_message(message)
            
            # Lähetä vain uusista kaupoista signaalit
            for signal in signals:
                signal_type = signal.get("signal_type", "UNKNOWN")
                if signal_type == "BUY" and trades_executed > 0:
                    token = signal.get("token")
                    if token:
                        message = f"🚀 ULTRA-FRESH BUY SIGNAL\n\n"
                        message += f"Token: {token.symbol} ({token.name})\n"
                        message += f"Address: {token.address[:8]}...{token.address[-8:]}\n"
                        message += f"Price: ${token.price:.6f}\n"
                        message += f"FDV: ${token.market_cap:,.0f}\n"
                        message += f"Age: {token.age_hours*60:.0f} min\n"
                        message += f"1H Change: +{token.price_change_1h:.1f}%\n"
                        message += f"Volume: ${token.volume_24h:,.0f}\n"
                        message += f"Score: {token.overall_score:.1f}/10\n"
                        message += f"Target: ${signal['target_price']:.6f}\n"
                        message += f"Stop Loss: ${signal['stop_loss']:.6f}\n"
                        message += f"Confidence: {signal['confidence']:.1%}"
                        
                        await self.telegram_bot.send_message(message)
                    
                elif signal_type == "SELL":
                    token = signal.get("token")
                    if token:
                        message = f"🔻 SELL SIGNAL\n\n"
                        message += f"Token: {token.symbol}\n"
                        message += f"Price: ${token.price:.6f}\n"
                        message += f"1H Change: {token.price_change_1h:.1f}%\n"
                        message += f"Score: {token.overall_score:.1f}/10\n"
                        message += f"Reason: {signal.get('reasoning', 'N/A')}"
                        
                        await self.telegram_bot.send_message(message)
            
            # Lähetä position päivitykset
            for symbol, position in self.positions.items():
                message = f"📊 Position Update\n\n"
                message += f"Token: {symbol}\n"
                message += f"Entry: ${position['entry_price']:.6f}\n"
                message += f"Current: ${position['current_price']:.6f}\n"
                message += f"PnL: ${position['unrealized_pnl']:.2f}\n"
                message += f"Value: ${position['position_value']:.2f}"
                
                await self.telegram_bot.send_message(message)
                
        except Exception as e:
            self.logger.error(f"Virhe Telegram viestien lähettämisessä: {e}")

# Test funktio
async def test_real_bot():
    """Testaa oikea trading bot"""
    async with RealNextGenTradingBot() as bot:
        result = await bot.run_analysis_cycle()
        print(f"\n📊 Oikea Trading Bot Test:")
        print(f"  Tokeneita löydetty: {result['tokens_found']}")
        print(f"  Signaaleja generoitu: {result['signals_generated']}")
        print(f"  Kauppoja suoritettu: {result['trades_executed']}")
        print(f"  Onnistumisprosentti: {result['success_rate']:.1f}%")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_real_bot())
