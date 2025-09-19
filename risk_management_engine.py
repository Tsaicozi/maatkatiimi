"""
Risk Management Engine - Kehittynyt riskienhallinta ja automaattinen trading
Täydentää NextGen Token Scanner Bot:ia
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import json
import asyncio
from enum import Enum

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"

@dataclass
class Position:
    """Trading position"""
    token_symbol: str
    token_name: str
    entry_price: float
    current_price: float
    quantity: float
    position_value: float
    unrealized_pnl: float
    realized_pnl: float
    stop_loss: float
    take_profit: float
    risk_score: float
    status: PositionStatus
    entry_time: datetime
    exit_time: Optional[datetime] = None
    max_drawdown: float = 0.0
    trailing_stop: Optional[float] = None

@dataclass
class RiskMetrics:
    """Riskimittarit"""
    portfolio_value: float
    total_exposure: float
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    beta: float
    correlation_matrix: Dict[str, Dict[str, float]]
    concentration_risk: float
    liquidity_risk: float

@dataclass
class TradingRule:
    """Trading sääntö"""
    rule_name: str
    condition: str
    action: str
    parameters: Dict
    enabled: bool = True
    priority: int = 1

class RiskManagementEngine:
    """Kehittynyt riskienhallinta moottori"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.risk_metrics = RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, {}, 0, 0)
        self.trading_rules: List[TradingRule] = []
        self.logger = logging.getLogger(__name__)
        
        # Riskienhallinta parametrit
        self.max_position_size = 0.05  # 5% portfolio per position
        self.max_total_exposure = 0.8  # 80% portfolio exposure
        self.max_drawdown_limit = 0.15  # 15% max drawdown
        self.stop_loss_percentage = 0.1  # 10% stop loss
        self.take_profit_percentage = 0.3  # 30% take profit
        
        # Alusta trading säännöt
        self.initialize_trading_rules()
    
    def initialize_trading_rules(self):
        """Alusta trading säännöt"""
        self.trading_rules = [
            TradingRule(
                rule_name="Max Position Size",
                condition="position_size > max_position_size",
                action="reduce_position",
                parameters={"max_size": self.max_position_size}
            ),
            TradingRule(
                rule_name="Stop Loss",
                condition="unrealized_pnl < -stop_loss_percentage",
                action="close_position",
                parameters={"stop_loss": self.stop_loss_percentage}
            ),
            TradingRule(
                rule_name="Take Profit",
                condition="unrealized_pnl > take_profit_percentage",
                action="close_position",
                parameters={"take_profit": self.take_profit_percentage}
            ),
            TradingRule(
                rule_name="Max Drawdown",
                condition="portfolio_drawdown > max_drawdown_limit",
                action="close_all_positions",
                parameters={"max_drawdown": self.max_drawdown_limit}
            ),
            TradingRule(
                rule_name="Trailing Stop",
                condition="price > entry_price * 1.1",
                action="update_trailing_stop",
                parameters={"trailing_percentage": 0.05}
            )
        ]
    
    def calculate_position_size(self, available_cash: float, risk_score: float, confidence: float) -> float:
        """Laske position koko riskin mukaan"""
        try:
            # Perus position koko (max 1% portfolio:sta)
            base_size = available_cash * 0.01  # 1% position
            
            # Säätö riskin mukaan
            risk_adjustment = 1.0 - (risk_score / 10.0)  # Korkea riski = pienempi position
            risk_adjustment = max(risk_adjustment, 0.1)  # Min 10% position
            
            # Säätö luottamuksen mukaan
            confidence_adjustment = confidence  # Korkea luottamus = suurempi position
            
            # Yksinkertaistettu säätö
            market_cap_adjustment = 1.0  # Oletetaan että token on jo suodatettu
            
            # Säätö likviditeetin mukaan
            liquidity_adjustment = 1.0  # Oletetaan että token on jo suodatettu
            
            # Laske lopullinen position koko
            final_size = (base_size * risk_adjustment * confidence_adjustment * 
                         market_cap_adjustment * liquidity_adjustment)
            
            # Rajoita position koko
            final_size = min(final_size, available_cash * 0.1)  # Max 10% käteisestä
            final_size = max(final_size, 10.0)  # Min $10
            
            return final_size
            
        except Exception as e:
            self.logger.error(f"Virhe position koon laskennassa: {e}")
            return 100.0  # Fallback position koko
    
    def calculate_risk_score(self, token_data, technical_indicators, trend_analysis) -> float:
        """Laske tokenin riski skoori"""
        try:
            risk_score = 5.0  # Aloita keskimääräisellä riskillä
            
            # Market cap riski
            if token_data.market_cap < 1_000_000:
                risk_score += 3.0  # Korkea riski
            elif token_data.market_cap < 10_000_000:
                risk_score += 1.5  # Keski riski
            elif token_data.market_cap < 100_000_000:
                risk_score += 0.5  # Matala riski
            
            # Volatiliteetti riski
            if hasattr(token_data, 'price_change_24h'):
                if abs(token_data.price_change_24h) > 50:
                    risk_score += 2.0  # Korkea volatiliteetti
                elif abs(token_data.price_change_24h) > 20:
                    risk_score += 1.0  # Keski volatiliteetti
            
            # Likviditeetti riski
            if token_data.liquidity < 100_000:
                risk_score += 2.0  # Matala likviditeetti
            elif token_data.liquidity < 1_000_000:
                risk_score += 1.0  # Keski likviditeetti
            
            # Ikä riski
            if token_data.age_days < 7:
                risk_score += 2.0  # Uusi token
            elif token_data.age_days < 30:
                risk_score += 1.0  # Keski-ikäinen token
            
            # Tekninen riski
            if technical_indicators:
                if technical_indicators.rsi > 80 or technical_indicators.rsi < 20:
                    risk_score += 1.0  # Ylimyynti/ylimyynti
                
                if technical_indicators.atr > token_data.price * 0.1:
                    risk_score += 1.0  # Korkea volatiliteetti
            
            # Trendi riski
            if trend_analysis:
                if trend_analysis.trend_strength < 30:
                    risk_score += 1.0  # Heikko trendi
                
                if trend_analysis.breakout_probability < 0.3:
                    risk_score += 0.5  # Matala breakout todennäköisyys
            
            return min(max(risk_score, 0), 10)  # Rajoita 0-10 välille
            
        except Exception as e:
            self.logger.error(f"Virhe riski skoorin laskennassa: {e}")
            return 7.0  # Korkea riski fallback
    
    def can_open_position(self, token_symbol: str, position_size: float) -> Tuple[bool, str]:
        """Tarkista voiko avata position"""
        try:
            # Tarkista onko jo position tälle tokenille
            if token_symbol in self.positions:
                return False, f"Position jo olemassa tokenille {token_symbol}"
            
            # Tarkista portfolio exposure
            current_exposure = self.calculate_total_exposure()
            if current_exposure + position_size > self.max_total_exposure * self.current_capital:
                return False, f"Liikaa exposure: {current_exposure + position_size:.2f} > {self.max_total_exposure * self.current_capital:.2f}"
            
            # Tarkista drawdown
            if self.risk_metrics.max_drawdown > self.max_drawdown_limit:
                return False, f"Max drawdown ylitetty: {self.risk_metrics.max_drawdown:.2%} > {self.max_drawdown_limit:.2%}"
            
            # Tarkista likviditeetti
            if position_size > self.current_capital * 0.1:
                return False, f"Liian suuri position: {position_size:.2f} > {self.current_capital * 0.1:.2f}"
            
            return True, "OK"
            
        except Exception as e:
            self.logger.error(f"Virhe position avaamisen tarkistuksessa: {e}")
            return False, f"Virhe: {e}"
    
    def open_position(self, token_data, entry_price: float, position_size: float, 
                     stop_loss: float, take_profit: float, risk_score: float) -> bool:
        """Avaa uusi position"""
        try:
            token_symbol = token_data.symbol
            
            # Tarkista voiko avata position
            can_open, reason = self.can_open_position(token_symbol, position_size)
            if not can_open:
                self.logger.warning(f"Ei voi avata position {token_symbol}: {reason}")
                return False
            
            # Laske quantity
            quantity = position_size / entry_price
            
            # Luo position
            position = Position(
                token_symbol=token_symbol,
                token_name=token_data.name,
                entry_price=entry_price,
                current_price=entry_price,
                quantity=quantity,
                position_value=position_size,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_score=risk_score,
                status=PositionStatus.OPEN,
                entry_time=datetime.now(),
                max_drawdown=0.0
            )
            
            # Lisää position
            self.positions[token_symbol] = position
            
            # Päivitä pääoma
            self.current_capital -= position_size
            
            self.logger.info(f"✅ Avattu position {token_symbol}: {quantity:.6f} @ ${entry_price:.6f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe position avaamisessa: {e}")
            return False
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """Päivitä position hinnat"""
        try:
            for token_symbol, new_price in price_updates.items():
                if token_symbol in self.positions:
                    position = self.positions[token_symbol]
                    position.current_price = new_price
                    position.position_value = position.quantity * new_price
                    position.unrealized_pnl = (new_price - position.entry_price) * position.quantity
                    
                    # Päivitä max drawdown
                    if position.unrealized_pnl < position.max_drawdown:
                        position.max_drawdown = position.unrealized_pnl
                    
                    # Päivitä trailing stop
                    if position.trailing_stop is None and new_price > position.entry_price * 1.1:
                        position.trailing_stop = new_price * 0.95
                    elif position.trailing_stop is not None and new_price > position.trailing_stop * 1.05:
                        position.trailing_stop = new_price * 0.95
            
        except Exception as e:
            self.logger.error(f"Virhe position hintojen päivityksessä: {e}")
    
    def check_trading_rules(self) -> List[Dict]:
        """Tarkista trading säännöt ja generoi toimenpiteet"""
        actions = []
        
        try:
            for rule in self.trading_rules:
                if not rule.enabled:
                    continue
                
                # Tarkista sääntö
                if rule.rule_name == "Max Position Size":
                    for token_symbol, position in self.positions.items():
                        position_size_pct = position.position_value / self.current_capital
                        if position_size_pct > rule.parameters["max_size"]:
                            actions.append({
                                "action": "reduce_position",
                                "token": token_symbol,
                                "reason": f"Position koko {position_size_pct:.2%} > {rule.parameters['max_size']:.2%}"
                            })
                
                elif rule.rule_name == "Stop Loss":
                    for token_symbol, position in self.positions.items():
                        pnl_pct = position.unrealized_pnl / position.position_value
                        if pnl_pct < -rule.parameters["stop_loss"]:
                            actions.append({
                                "action": "close_position",
                                "token": token_symbol,
                                "reason": f"Stop loss: {pnl_pct:.2%} < -{rule.parameters['stop_loss']:.2%}"
                            })
                
                elif rule.rule_name == "Take Profit":
                    for token_symbol, position in self.positions.items():
                        pnl_pct = position.unrealized_pnl / position.position_value
                        if pnl_pct > rule.parameters["take_profit"]:
                            actions.append({
                                "action": "close_position",
                                "token": token_symbol,
                                "reason": f"Take profit: {pnl_pct:.2%} > {rule.parameters['take_profit']:.2%}"
                            })
                
                elif rule.rule_name == "Max Drawdown":
                    portfolio_drawdown = self.calculate_portfolio_drawdown()
                    if portfolio_drawdown > rule.parameters["max_drawdown"]:
                        actions.append({
                            "action": "close_all_positions",
                            "reason": f"Portfolio drawdown {portfolio_drawdown:.2%} > {rule.parameters['max_drawdown']:.2%}"
                        })
                
                elif rule.rule_name == "Trailing Stop":
                    for token_symbol, position in self.positions.items():
                        if position.trailing_stop is not None and position.current_price < position.trailing_stop:
                            actions.append({
                                "action": "close_position",
                                "token": token_symbol,
                                "reason": f"Trailing stop: ${position.current_price:.6f} < ${position.trailing_stop:.6f}"
                            })
            
        except Exception as e:
            self.logger.error(f"Virhe trading sääntöjen tarkistuksessa: {e}")
        
        return actions
    
    def execute_actions(self, actions: List[Dict]) -> List[Dict]:
        """Suorita toimenpiteet"""
        results = []
        
        try:
            for action in actions:
                if action["action"] == "close_position":
                    result = self.close_position(action["token"], action["reason"])
                    results.append(result)
                
                elif action["action"] == "close_all_positions":
                    result = self.close_all_positions(action["reason"])
                    results.append(result)
                
                elif action["action"] == "reduce_position":
                    result = self.reduce_position(action["token"], 0.5, action["reason"])
                    results.append(result)
            
        except Exception as e:
            self.logger.error(f"Virhe toimenpiteiden suorittamisessa: {e}")
        
        return results
    
    def close_position(self, token_symbol: str, reason: str) -> Dict:
        """Sulje position"""
        try:
            if token_symbol not in self.positions:
                return {"success": False, "reason": f"Position {token_symbol} ei löytynyt"}
            
            position = self.positions[token_symbol]
            
            # Laske realized P&L
            realized_pnl = position.unrealized_pnl
            position.realized_pnl = realized_pnl
            position.status = PositionStatus.CLOSED
            position.exit_time = datetime.now()
            
            # Päivitä pääoma
            self.current_capital += position.position_value
            
            # Siirrä suljettuun positioniin
            self.closed_positions.append(position)
            del self.positions[token_symbol]
            
            self.logger.info(f"✅ Suljettu position {token_symbol}: P&L ${realized_pnl:.2f} - {reason}")
            
            return {
                "success": True,
                "token": token_symbol,
                "realized_pnl": realized_pnl,
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Virhe position sulkemisessa: {e}")
            return {"success": False, "reason": f"Virhe: {e}"}
    
    def close_all_positions(self, reason: str) -> Dict:
        """Sulje kaikki positionit"""
        try:
            closed_positions = []
            total_pnl = 0.0
            
            for token_symbol in list(self.positions.keys()):
                result = self.close_position(token_symbol, reason)
                if result["success"]:
                    closed_positions.append(token_symbol)
                    total_pnl += result["realized_pnl"]
            
            self.logger.warning(f"🚨 Suljettu kaikki positionit: {len(closed_positions)} positionia, P&L ${total_pnl:.2f} - {reason}")
            
            return {
                "success": True,
                "closed_positions": closed_positions,
                "total_pnl": total_pnl,
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Virhe kaikkien positionien sulkemisessa: {e}")
            return {"success": False, "reason": f"Virhe: {e}"}
    
    def reduce_position(self, token_symbol: str, reduction_factor: float, reason: str) -> Dict:
        """Vähennä position koko"""
        try:
            if token_symbol not in self.positions:
                return {"success": False, "reason": f"Position {token_symbol} ei löytynyt"}
            
            position = self.positions[token_symbol]
            
            # Laske uusi koko
            new_quantity = position.quantity * reduction_factor
            quantity_to_sell = position.quantity - new_quantity
            
            # Laske realized P&L osittaiselle myynnille
            realized_pnl = (position.current_price - position.entry_price) * quantity_to_sell
            
            # Päivitä position
            position.quantity = new_quantity
            position.position_value = new_quantity * position.current_price
            position.realized_pnl += realized_pnl
            
            # Päivitä pääoma
            self.current_capital += quantity_to_sell * position.current_price
            
            self.logger.info(f"📉 Vähennetty position {token_symbol}: {quantity_to_sell:.6f} myyty, P&L ${realized_pnl:.2f} - {reason}")
            
            return {
                "success": True,
                "token": token_symbol,
                "quantity_sold": quantity_to_sell,
                "realized_pnl": realized_pnl,
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Virhe position vähentämisessä: {e}")
            return {"success": False, "reason": f"Virhe: {e}"}
    
    def calculate_total_exposure(self) -> float:
        """Laske kokonais exposure"""
        return sum(position.position_value for position in self.positions.values())
    
    def calculate_portfolio_drawdown(self) -> float:
        """Laske portfolio drawdown"""
        try:
            if not self.closed_positions:
                return 0.0
            
            # Laske portfolio arvo
            portfolio_value = self.current_capital + self.calculate_total_exposure()
            
            # Laske peak
            peak_value = self.initial_capital
            for position in self.closed_positions:
                if position.realized_pnl > 0:
                    peak_value += position.realized_pnl
            
            # Laske drawdown
            if peak_value > 0:
                drawdown = (peak_value - portfolio_value) / peak_value
                return max(drawdown, 0.0)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Virhe portfolio drawdown laskennassa: {e}")
            return 0.0
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Laske riskimittarit"""
        try:
            portfolio_value = self.current_capital + self.calculate_total_exposure()
            total_exposure = self.calculate_total_exposure()
            max_drawdown = self.calculate_portfolio_drawdown()
            
            # Laske VaR (yksinkertainen toteutus)
            if self.closed_positions:
                returns = [pos.realized_pnl / pos.position_value for pos in self.closed_positions if pos.position_value > 0]
                if returns:
                    var_95 = np.percentile(returns, 5) * portfolio_value
                    var_99 = np.percentile(returns, 1) * portfolio_value
                else:
                    var_95 = var_99 = 0.0
            else:
                var_95 = var_99 = 0.0
            
            # Laske Sharpe ratio (yksinkertainen toteutus)
            if self.closed_positions:
                total_return = sum(pos.realized_pnl for pos in self.closed_positions)
                if total_return > 0:
                    sharpe_ratio = total_return / (portfolio_value * 0.1)  # Oletetaan 10% volatiliteetti
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0
            
            # Laske korrelaatio matriisi (placeholder)
            correlation_matrix = {}
            
            # Laske konsentraatio riski
            if portfolio_value > 0:
                concentration_risk = max([pos.position_value / portfolio_value for pos in self.positions.values()], default=0.0)
            else:
                concentration_risk = 0.0
            
            # Laske likviditeetti riski
            liquidity_risk = 0.0
            for position in self.positions.values():
                # Yksinkertainen likviditeetti riski
                if position.position_value > self.current_capital * 0.1:
                    liquidity_risk += 0.1
            
            self.risk_metrics = RiskMetrics(
                portfolio_value=portfolio_value,
                total_exposure=total_exposure,
                max_drawdown=max_drawdown,
                var_95=var_95,
                var_99=var_99,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=0.0,  # Placeholder
                calmar_ratio=0.0,   # Placeholder
                beta=0.0,           # Placeholder
                correlation_matrix=correlation_matrix,
                concentration_risk=concentration_risk,
                liquidity_risk=liquidity_risk
            )
            
            return self.risk_metrics
            
        except Exception as e:
            self.logger.error(f"Virhe riskimittarien laskennassa: {e}")
            return self.risk_metrics
    
    def get_portfolio_summary(self) -> Dict:
        """Hae portfolio yhteenveto"""
        try:
            risk_metrics = self.calculate_risk_metrics()
            
            # Laske position yhteenveto
            position_summary = {}
            for token_symbol, position in self.positions.items():
                position_summary[token_symbol] = {
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "quantity": position.quantity,
                    "position_value": position.position_value,
                    "unrealized_pnl": position.unrealized_pnl,
                    "pnl_percentage": (position.unrealized_pnl / position.position_value) * 100,
                    "risk_score": position.risk_score,
                    "days_held": (datetime.now() - position.entry_time).days
                }
            
            # Laske suljettujen positionien yhteenveto
            closed_summary = {
                "total_positions": len(self.closed_positions),
                "total_realized_pnl": sum(pos.realized_pnl for pos in self.closed_positions),
                "winning_positions": len([pos for pos in self.closed_positions if pos.realized_pnl > 0]),
                "losing_positions": len([pos for pos in self.closed_positions if pos.realized_pnl < 0])
            }
            
            return {
                "portfolio_value": risk_metrics.portfolio_value,
                "current_capital": self.current_capital,
                "total_exposure": risk_metrics.total_exposure,
                "max_drawdown": risk_metrics.max_drawdown,
                "var_95": risk_metrics.var_95,
                "sharpe_ratio": risk_metrics.sharpe_ratio,
                "concentration_risk": risk_metrics.concentration_risk,
                "liquidity_risk": risk_metrics.liquidity_risk,
                "open_positions": position_summary,
                "closed_positions": closed_summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Virhe portfolio yhteenvedon haussa: {e}")
            return {}
    
    def save_portfolio_state(self, filename: str = None):
        """Tallenna portfolio tila"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_state_{timestamp}.json"
            
            portfolio_data = {
                "initial_capital": self.initial_capital,
                "current_capital": self.current_capital,
                "positions": {k: asdict(v) for k, v in self.positions.items()},
                "closed_positions": [asdict(pos) for pos in self.closed_positions],
                "risk_metrics": asdict(self.risk_metrics),
                "trading_rules": [asdict(rule) for rule in self.trading_rules],
                "timestamp": datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(portfolio_data, f, indent=2, default=str)
            
            self.logger.info(f"💾 Portfolio tila tallennettu: {filename}")
            
        except Exception as e:
            self.logger.error(f"Virhe portfolio tilan tallentamisessa: {e}")
    
    def load_portfolio_state(self, filename: str):
        """Lataa portfolio tila"""
        try:
            with open(filename, 'r') as f:
                portfolio_data = json.load(f)
            
            self.initial_capital = portfolio_data["initial_capital"]
            self.current_capital = portfolio_data["current_capital"]
            
            # Lataa positionit
            self.positions = {}
            for k, v in portfolio_data["positions"].items():
                v["status"] = PositionStatus(v["status"])
                v["entry_time"] = datetime.fromisoformat(v["entry_time"])
                if v["exit_time"]:
                    v["exit_time"] = datetime.fromisoformat(v["exit_time"])
                self.positions[k] = Position(**v)
            
            # Lataa suljetut positionit
            self.closed_positions = []
            for pos_data in portfolio_data["closed_positions"]:
                pos_data["status"] = PositionStatus(pos_data["status"])
                pos_data["entry_time"] = datetime.fromisoformat(pos_data["entry_time"])
                if pos_data["exit_time"]:
                    pos_data["exit_time"] = datetime.fromisoformat(pos_data["exit_time"])
                self.closed_positions.append(Position(**pos_data))
            
            self.logger.info(f"📂 Portfolio tila ladattu: {filename}")
            
        except Exception as e:
            self.logger.error(f"Virhe portfolio tilan lataamisessa: {e}")

# =============================================================================
# TESTING
# =============================================================================

def test_risk_management():
    """Testaa riskienhallintaa"""
    print("🧪 Testataan riskienhallintaa...")
    
    # Luo riskienhallinta moottori
    risk_engine = RiskManagementEngine(initial_capital=10000.0)
    
    # Luo mock token data
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class MockTokenData:
        symbol: str
        name: str
        price: float
        market_cap: float
        liquidity: float
        age_days: int
        price_change_24h: float
    
    # Testaa position avaamista
    token_data = MockTokenData(
        symbol="TEST",
        name="Test Token",
        price=1.0,
        market_cap=5_000_000,
        liquidity=500_000,
        age_days=15,
        price_change_24h=10.0
    )
    
    # Laske riski skoori
    risk_score = risk_engine.calculate_risk_score(token_data, None, None)
    print(f"✅ Risk skoori: {risk_score:.1f}/10")
    
    # Laske position koko
    position_size = risk_engine.calculate_position_size(token_data, risk_score, 0.8)
    print(f"✅ Position koko: ${position_size:.2f}")
    
    # Avaa position
    success = risk_engine.open_position(
        token_data, 
        entry_price=1.0, 
        position_size=position_size,
        stop_loss=0.9,
        take_profit=1.3,
        risk_score=risk_score
    )
    
    if success:
        print("✅ Position avattu onnistuneesti")
        
        # Päivitä hinta
        risk_engine.update_position_prices({"TEST": 1.1})
        
        # Tarkista trading säännöt
        actions = risk_engine.check_trading_rules()
        print(f"✅ Trading sääntöjä tarkistettu: {len(actions)} toimenpidettä")
        
        # Hae portfolio yhteenveto
        summary = risk_engine.get_portfolio_summary()
        print(f"✅ Portfolio arvo: ${summary['portfolio_value']:.2f}")
        print(f"✅ Max drawdown: {summary['max_drawdown']:.2%}")
        
        # Tallenna tila
        risk_engine.save_portfolio_state("test_portfolio.json")
        print("✅ Portfolio tila tallennettu")
    
    print("=" * 60)
    print("✅ Riskienhallinta testi valmis!")

if __name__ == "__main__":
    test_risk_management()
