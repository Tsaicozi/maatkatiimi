#!/usr/bin/env python3
"""
Demo Automaattinen Solana token trader
Simuloi automaattisen trading:n ilman oikeita transaktioita
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import random

from real_solana_token_scanner import RealSolanaTokenScanner, RealSolanaToken
from demo_solana_trader import DemoSolanaTrader

load_dotenv()

@dataclass
class DemoPosition:
    """Demo trading position"""
    token_address: str
    symbol: str
    entry_price_sol: float
    entry_amount_sol: float
    token_amount: float
    entry_time: datetime
    entry_tx: str
    stop_loss_price: float
    take_profit_price: float
    max_hold_hours: int = 1  # Demo: lyhyt hold
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DemoPosition':
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        return cls(**data)

@dataclass
class DemoTradingStats:
    """Demo trading statistiikka"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl_sol: float = 0.0
    total_fees_sol: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0
    start_balance_sol: float = 1.0  # Demo start
    current_balance_sol: float = 1.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def net_pnl_sol(self) -> float:
        return self.total_pnl_sol - self.total_fees_sol

class DemoSolanaAutoTrader:
    """Demo automaattinen Solana token trader"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Demo konfiguraatio
        self.config = {
            "position_size_sol": 0.05,  # Demo size
            "max_positions": 2,         # Demo max
            "stop_loss_percent": 30,
            "take_profit_percent": 50,
            "max_hold_hours": 1,        # Demo: lyhyt hold
            "cooldown_hours": 1,        # Demo: lyhyt cooldown
            "min_score_threshold": 7.0,
            "slippage_bps": 100,
        }
        
        # Demo state
        self.positions: Dict[str, DemoPosition] = {}
        self.cooldown_tokens: Dict[str, datetime] = {}
        self.stats = DemoTradingStats()
        
        # Components
        self.scanner = None
        self.trader = None
        
        # Demo state file
        self.state_file = "demo_trader_state.json"
        
        self.logger.info("🚀 Demo SolanaAutoTrader alustettu")
        self.logger.info(f"📊 Demo konfiguraatio: {self.config}")

    def _setup_logging(self) -> logging.Logger:
        """Aseta logging"""
        logger = logging.getLogger("DemoSolanaAutoTrader")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger

    async def __aenter__(self):
        """Async context manager entry"""
        # Alusta components
        self.scanner = RealSolanaTokenScanner()
        await self.scanner.__aenter__()
        
        self.trader = DemoSolanaTrader("demo_private_key")
        await self.trader.__aenter__()
        
        # Lataa demo state
        await self.load_state()
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.save_state()
        
        if self.scanner:
            await self.scanner.__aexit__(exc_type, exc_val, exc_tb)
        if self.trader:
            await self.trader.__aexit__(exc_type, exc_val, exc_tb)

    async def load_state(self):
        """Lataa demo state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    
                # Lataa positions
                if 'positions' in data:
                    self.positions = {
                        addr: DemoPosition.from_dict(pos_data)
                        for addr, pos_data in data['positions'].items()
                    }
                    
                # Lataa cooldowns
                if 'cooldown_tokens' in data:
                    self.cooldown_tokens = {
                        addr: datetime.fromisoformat(time_str)
                        for addr, time_str in data['cooldown_tokens'].items()
                    }
                    
                # Lataa stats
                if 'stats' in data:
                    stats_data = data['stats']
                    self.stats = DemoTradingStats(**stats_data)
                    
                self.logger.info(f"📂 Demo state ladattu: {len(self.positions)} positiota")
                
        except Exception as e:
            self.logger.error(f"Virhe demo staten latauksessa: {e}")

    async def save_state(self):
        """Tallenna demo state"""
        try:
            data = {
                'positions': {
                    addr: pos.to_dict()
                    for addr, pos in self.positions.items()
                },
                'cooldown_tokens': {
                    addr: time.isoformat()
                    for addr, time in self.cooldown_tokens.items()
                },
                'stats': asdict(self.stats),
                'last_update': datetime.now(ZoneInfo("Europe/Helsinki")).isoformat(),
                'note': 'DEMO DATA - Ei oikeaa trading dataa!'
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.debug("💾 Demo state tallennettu")
            
        except Exception as e:
            self.logger.error(f"Virhe demo staten tallennuksessa: {e}")

    async def scan_and_evaluate_tokens(self) -> List[RealSolanaToken]:
        """Skannaa ja arvioi tokenit (demo)"""
        try:
            self.logger.info("🔍 Skannataan demo tokeneita...")
            
            # Skannaa tokenit
            tokens = await self.scanner.scan_new_tokens()
            
            if not tokens:
                self.logger.info("❌ Ei löytynyt demo tokeneita")
                return []
            
            # Suodata ja järjestä (demo)
            filtered_tokens = []
            for token in tokens:
                # Tarkista että ei ole jo positiossa
                if token.address in self.positions:
                    continue
                    
                # Tarkista cooldown
                if token.address in self.cooldown_tokens:
                    cooldown_end = self.cooldown_tokens[token.address] + timedelta(hours=self.config["cooldown_hours"])
                    if datetime.now() < cooldown_end:
                        continue
                        
                # Tarkista score threshold
                if token.overall_score >= self.config["min_score_threshold"]:
                    filtered_tokens.append(token)
            
            # Järjestä scoren mukaan
            filtered_tokens.sort(key=lambda t: t.overall_score, reverse=True)
            
            self.logger.info(f"✅ {len(filtered_tokens)} demo tokenia läpäisi suodatuksen")
            return filtered_tokens
            
        except Exception as e:
            self.logger.error(f"Virhe demo tokenien skannauksessa: {e}")
            return []

    async def open_position(self, token: RealSolanaToken) -> bool:
        """Avaa demo positio"""
        try:
            # Tarkista että on tilaa uudelle positiolle
            if len(self.positions) >= self.config["max_positions"]:
                self.logger.info("❌ Demo: Maksimi positioiden määrä saavutettu")
                return False
                
            # Tarkista demo balance
            balance = await self.trader.get_sol_balance()
            position_size = self.config["position_size_sol"]
            gas_fee = await self.trader.estimate_gas_fee()
            
            if balance < position_size + gas_fee:
                self.logger.warning(f"❌ Demo: Ei riittävästi SOL:ia. Balance: {balance:.6f}")
                return False
                
            self.logger.info(f"🔄 Demo: Avataan positio {token.symbol}")
            
            # Demo osto
            result = await self.trader.buy_token(
                token.address,
                position_size,
                self.config["slippage_bps"]
            )
            
            if not result:
                self.logger.error("❌ Demo token osto epäonnistui")
                return False
                
            tx_hash, token_amount = result
            
            # Laske stop loss ja take profit
            entry_price = position_size / token_amount if token_amount > 0 else 0
            stop_loss_price = entry_price * (1 - self.config["stop_loss_percent"] / 100)
            take_profit_price = entry_price * (1 + self.config["take_profit_percent"] / 100)
            
            # Luo demo positio
            position = DemoPosition(
                token_address=token.address,
                symbol=token.symbol,
                entry_price_sol=entry_price,
                entry_amount_sol=position_size,
                token_amount=token_amount,
                entry_time=datetime.now(),
                entry_tx=tx_hash,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                max_hold_hours=self.config["max_hold_hours"]
            )
            
            self.positions[token.address] = position
            
            # Päivitä demo stats
            self.stats.total_trades += 1
            self.stats.total_fees_sol += gas_fee
            
            # Tallenna demo state
            await self.save_state()
            
            self.logger.info(f"✅ Demo positio avattu: {token.symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe demo position avauksessa: {e}")
            return False

    async def close_position(self, position: DemoPosition, reason: str) -> bool:
        """Sulje demo positio"""
        try:
            self.logger.info(f"🔄 Demo: Suljetaan positio {position.symbol} - {reason}")
            
            # Demo myynti
            result = await self.trader.sell_token(
                position.token_address,
                position.token_amount,
                self.config["slippage_bps"]
            )
            
            if not result:
                self.logger.error("❌ Demo token myynti epäonnistui")
                return False
                
            tx_hash, sol_received = result
            
            # Laske demo PnL
            pnl_sol = sol_received - position.entry_amount_sol
            pnl_percent = (pnl_sol / position.entry_amount_sol) * 100
            
            # Päivitä demo stats
            gas_fee = await self.trader.estimate_gas_fee()
            self.stats.total_fees_sol += gas_fee
            self.stats.total_pnl_sol += pnl_sol
            
            if pnl_sol > 0:
                self.stats.winning_trades += 1
                if pnl_sol > self.stats.best_trade_pnl:
                    self.stats.best_trade_pnl = pnl_sol
            else:
                self.stats.losing_trades += 1
                if pnl_sol < self.stats.worst_trade_pnl:
                    self.stats.worst_trade_pnl = pnl_sol
            
            # Päivitä demo balance
            self.stats.current_balance_sol = await self.trader.get_sol_balance()
            
            # Poista positio ja lisää cooldown
            del self.positions[position.token_address]
            self.cooldown_tokens[position.token_address] = datetime.now()
            
            # Tallenna demo state
            await self.save_state()
            
            self.logger.info(f"✅ Demo positio suljettu: {position.symbol}, PnL: {pnl_sol:+.6f} SOL ({pnl_percent:+.1f}%)")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe demo position sulkemisessa: {e}")
            return False

    async def monitor_positions(self):
        """Monitoroi demo positioita"""
        if not self.positions:
            return
            
        self.logger.info(f"👀 Monitoroidaan {len(self.positions)} demo positiota...")
        
        for address, position in list(self.positions.items()):
            try:
                # Hae demo hinta (random muutos)
                price_change = random.uniform(-0.5, 0.5)  # ±50% random muutos
                current_price = position.entry_price_sol * (1 + price_change)
                
                # Tarkista exit ehdot
                should_exit = False
                exit_reason = ""
                
                # Stop loss
                if current_price <= position.stop_loss_price:
                    should_exit = True
                    exit_reason = f"Demo Stop Loss ({current_price:.8f} <= {position.stop_loss_price:.8f})"
                
                # Take profit
                elif current_price >= position.take_profit_price:
                    should_exit = True
                    exit_reason = f"Demo Take Profit ({current_price:.8f} >= {position.take_profit_price:.8f})"
                
                # Max hold time (demo: lyhyt)
                elif datetime.now() - position.entry_time > timedelta(hours=position.max_hold_hours):
                    should_exit = True
                    exit_reason = f"Demo Max Hold Time ({position.max_hold_hours}h)"
                
                # Demo: 30% chance exit randomly
                elif random.random() < 0.3:
                    should_exit = True
                    exit_reason = "Demo Random Exit"
                
                # Sulje positio jos tarpeen
                if should_exit:
                    await self.close_position(position, exit_reason)
                else:
                    # Logita status
                    pnl_percent = ((current_price - position.entry_price_sol) / position.entry_price_sol) * 100
                    self.logger.info(f"📊 Demo {position.symbol}: {current_price:.8f} SOL ({pnl_percent:+.1f}%)")
                    
            except Exception as e:
                self.logger.error(f"Virhe demo position {position.symbol} monitoroinnissa: {e}")

    async def cleanup_cooldowns(self):
        """Siivoa demo cooldownit"""
        now = datetime.now()
        cooldown_hours = self.config["cooldown_hours"]
        
        expired_cooldowns = [
            addr for addr, time in self.cooldown_tokens.items()
            if now - time > timedelta(hours=cooldown_hours)
        ]
        
        for addr in expired_cooldowns:
            del self.cooldown_tokens[addr]
            
        if expired_cooldowns:
            self.logger.info(f"🧹 Demo: Poistettu {len(expired_cooldowns)} vanhaa cooldownia")

    async def print_status(self):
        """Tulosta demo status"""
        balance = await self.trader.get_sol_balance()
        
        self.logger.info("=" * 60)
        self.logger.info("📊 DEMO SOLANA AUTO TRADER STATUS")
        self.logger.info("=" * 60)
        self.logger.info(f"💰 Demo SOL Balance: {balance:.6f}")
        self.logger.info(f"📈 Demo Active Positions: {len(self.positions)}")
        self.logger.info(f"❄️  Demo Cooldown Tokens: {len(self.cooldown_tokens)}")
        self.logger.info(f"🎯 Demo Total Trades: {self.stats.total_trades}")
        self.logger.info(f"✅ Demo Win Rate: {self.stats.win_rate:.1f}%")
        self.logger.info(f"💵 Demo Net PnL: {self.stats.net_pnl_sol:+.6f} SOL")
        
        if self.positions:
            self.logger.info("\n🔍 Demo Active Positions:")
            for pos in self.positions.values():
                age_minutes = (datetime.now() - pos.entry_time).total_seconds() / 60
                self.logger.info(f"  {pos.symbol}: {pos.entry_amount_sol:.3f} SOL, {age_minutes:.1f}min")
        
        self.logger.info("=" * 60)

    async def run_trading_cycle(self):
        """Suorita demo trading cycle"""
        try:
            self.logger.info("🔄 Demo: Aloitetaan trading cycle...")
            
            # 1. Siivoa cooldownit
            await self.cleanup_cooldowns()
            
            # 2. Monitoroi olemassa olevat positiot
            await self.monitor_positions()
            
            # 3. Etsi uusia demo mahdollisuuksia
            if len(self.positions) < self.config["max_positions"]:
                tokens = await self.scan_and_evaluate_tokens()
                
                # Avaa demo positioita parhaista tokeneista
                for token in tokens[:self.config["max_positions"] - len(self.positions)]:
                    success = await self.open_position(token)
                    if success:
                        # Odota hetki ennen seuraavaa
                        await asyncio.sleep(1)
            
            # 4. Tulosta demo status
            await self.print_status()
            
            self.logger.info("✅ Demo trading cycle valmis")
            
        except Exception as e:
            self.logger.error(f"Virhe demo trading cyclessa: {e}")

# Main funktio
async def main():
    """Demo main funktio"""
    try:
        print("🚀 DEMO Solana Auto Trader")
        print("⚠️  HUOM: Tämä on DEMO versio - ei oikeaa tradinggia!")
        print("")
        
        async with DemoSolanaAutoTrader() as trader:
            # Aja demo cycle
            await trader.run_trading_cycle()
                
    except KeyboardInterrupt:
        print("👋 Demo trader pysäytetty")
    except Exception as e:
        print(f"❌ Demo virhe: {e}")

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())