import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import aiohttp

from real_solana_token_scanner import RealSolanaTokenScanner, RealSolanaToken
from solana_trader import SolanaTrader

load_dotenv()

@dataclass
class Position:
    """Trading position"""
    token_address: str
    symbol: str
    entry_price_sol: float
    entry_amount_sol: float
    token_amount: float
    entry_time: datetime
    entry_tx: str
    stop_loss_price: float  # SOL
    take_profit_price: float  # SOL
    max_hold_hours: int = 48
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        return cls(**data)

@dataclass
class TradingStats:
    """Trading statistiikka"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl_sol: float = 0.0
    total_fees_sol: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0
    start_balance_sol: float = 0.0
    current_balance_sol: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def net_pnl_sol(self) -> float:
        return self.total_pnl_sol - self.total_fees_sol

class SolanaAutoTrader:
    """Automaattinen Solana token trader"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Konfiguraatio
        self.config = {
            "position_size_sol": float(os.getenv("POSITION_SIZE_SOL", "0.05")),
            "max_positions": int(os.getenv("MAX_POSITIONS", "3")),
            "stop_loss_percent": float(os.getenv("STOP_LOSS_PERCENT", "30")),
            "take_profit_percent": float(os.getenv("TAKE_PROFIT_PERCENT", "50")),
            "max_hold_hours": int(os.getenv("MAX_HOLD_HOURS", "48")),
            "cooldown_hours": int(os.getenv("COOLDOWN_HOURS", "24")),
            "min_score_threshold": float(os.getenv("MIN_SCORE_THRESHOLD", "7.0")),
            "slippage_bps": int(os.getenv("SLIPPAGE_BPS", "100")),  # 1%
        }
        
        # State
        self.positions: Dict[str, Position] = {}
        self.cooldown_tokens: Dict[str, datetime] = {}
        self.stats = TradingStats()
        
        # Components
        self.scanner = None
        self.trader = None
        
        # Telegram
        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # State file
        self.state_file = "solana_trader_state.json"
        
        self.logger.info("🚀 SolanaAutoTrader alustettu")
        self.logger.info(f"📊 Konfiguraatio: {self.config}")

    def _setup_logging(self) -> logging.Logger:
        """Aseta logging"""
        logger = logging.getLogger("SolanaAutoTrader")
        logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler("solana_auto_trader.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger

    async def __aenter__(self):
        """Async context manager entry"""
        # Alusta components
        self.scanner = RealSolanaTokenScanner()
        await self.scanner.__aenter__()
        
        private_key = os.getenv("PHANTOM_PRIVATE_KEY")
        if not private_key:
            raise ValueError("PHANTOM_PRIVATE_KEY puuttuu .env tiedostosta")
            
        self.trader = SolanaTrader(private_key)
        await self.trader.__aenter__()
        
        # Lataa state
        await self.load_state()
        
        # Alusta stats jos tyhjä
        if self.stats.start_balance_sol == 0.0:
            self.stats.start_balance_sol = await self.trader.get_sol_balance()
            
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.save_state()
        
        if self.scanner:
            await self.scanner.__aexit__(exc_type, exc_val, exc_tb)
        if self.trader:
            await self.trader.__aexit__(exc_type, exc_val, exc_tb)

    async def load_state(self):
        """Lataa trader state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    
                # Lataa positions
                if 'positions' in data:
                    self.positions = {
                        addr: Position.from_dict(pos_data)
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
                    self.stats = TradingStats(**stats_data)
                    
                self.logger.info(f"📂 State ladattu: {len(self.positions)} positiota, {len(self.cooldown_tokens)} cooldownia")
                
        except Exception as e:
            self.logger.error(f"Virhe staten latauksessa: {e}")

    async def save_state(self):
        """Tallenna trader state"""
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
                'last_update': datetime.now(ZoneInfo("Europe/Helsinki")).isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.debug("💾 State tallennettu")
            
        except Exception as e:
            self.logger.error(f"Virhe staten tallennuksessa: {e}")

    async def send_telegram_message(self, message: str):
        """Lähetä Telegram viesti"""
        if not self.telegram_token or not self.telegram_chat_id:
            self.logger.debug("Telegram ei konfiguroitu")
            return
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        self.logger.debug("📱 Telegram viesti lähetetty")
                    else:
                        self.logger.warning(f"Telegram virhe: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Telegram virhe: {e}")

    async def scan_and_evaluate_tokens(self) -> List[RealSolanaToken]:
        """Skannaa ja arvioi tokenit"""
        try:
            self.logger.info("🔍 Skannataan uusia tokeneita...")
            
            # Skannaa tokenit
            tokens = await self.scanner.scan_new_tokens()
            
            if not tokens:
                self.logger.info("❌ Ei löytynyt tokeneita")
                return []
            
            # Suodata ja järjestä
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
            
            self.logger.info(f"✅ {len(filtered_tokens)} tokenia läpäisi suodatuksen")
            return filtered_tokens
            
        except Exception as e:
            self.logger.error(f"Virhe tokenien skannauksessa: {e}")
            return []

    async def open_position(self, token: RealSolanaToken) -> bool:
        """Avaa uusi positio"""
        try:
            # Tarkista että on tilaa uudelle positiolle
            if len(self.positions) >= self.config["max_positions"]:
                self.logger.info("❌ Maksimi positioiden määrä saavutettu")
                return False
                
            # Tarkista balance
            balance = await self.trader.get_sol_balance()
            position_size = self.config["position_size_sol"]
            gas_fee = await self.trader.estimate_gas_fee()
            
            if balance < position_size + gas_fee:
                self.logger.warning(f"❌ Ei riittävästi SOL:ia. Balance: {balance:.6f}, tarvitaan: {position_size + gas_fee:.6f}")
                return False
                
            self.logger.info(f"🔄 Avataan positio: {token.symbol} ({token.address[:8]}...)")
            
            # Osta token
            result = await self.trader.buy_token(
                token.address,
                position_size,
                self.config["slippage_bps"]
            )
            
            if not result:
                self.logger.error("❌ Token osto epäonnistui")
                return False
                
            tx_hash, token_amount = result
            
            # Laske stop loss ja take profit
            entry_price = position_size / token_amount if token_amount > 0 else 0
            stop_loss_price = entry_price * (1 - self.config["stop_loss_percent"] / 100)
            take_profit_price = entry_price * (1 + self.config["take_profit_percent"] / 100)
            
            # Luo positio
            position = Position(
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
            
            # Päivitä stats
            self.stats.total_trades += 1
            self.stats.total_fees_sol += gas_fee
            
            # Tallenna state
            await self.save_state()
            
            # Telegram ilmoitus
            message = f"""
🟢 <b>POSITIO AVATTU</b>
Token: {token.symbol}
Hinta: {entry_price:.8f} SOL
Määrä: {position_size:.3f} SOL → {token_amount:.0f} tokenia
Stop Loss: -{self.config["stop_loss_percent"]}%
Take Profit: +{self.config["take_profit_percent"]}%
Score: {token.overall_score:.1f}/10
TX: {tx_hash[:16]}...
            """.strip()
            
            await self.send_telegram_message(message)
            
            self.logger.info(f"✅ Positio avattu: {token.symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe position avauksessa: {e}")
            return False

    async def close_position(self, position: Position, reason: str) -> bool:
        """Sulje positio"""
        try:
            self.logger.info(f"🔄 Suljetaan positio: {position.symbol} - {reason}")
            
            # Myy tokenit
            result = await self.trader.sell_token(
                position.token_address,
                position.token_amount,
                self.config["slippage_bps"]
            )
            
            if not result:
                self.logger.error("❌ Token myynti epäonnistui")
                return False
                
            tx_hash, sol_received = result
            
            # Laske PnL
            pnl_sol = sol_received - position.entry_amount_sol
            pnl_percent = (pnl_sol / position.entry_amount_sol) * 100
            
            # Päivitä stats
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
            
            # Päivitä current balance
            self.stats.current_balance_sol = await self.trader.get_sol_balance()
            
            # Poista positio ja lisää cooldown
            del self.positions[position.token_address]
            self.cooldown_tokens[position.token_address] = datetime.now()
            
            # Tallenna state
            await self.save_state()
            
            # Telegram ilmoitus
            pnl_emoji = "🟢" if pnl_sol > 0 else "🔴"
            message = f"""
{pnl_emoji} <b>POSITIO SULJETTU</b>
Token: {position.symbol}
Syy: {reason}
Sisään: {position.entry_amount_sol:.3f} SOL
Ulos: {sol_received:.3f} SOL
PnL: {pnl_sol:+.6f} SOL ({pnl_percent:+.1f}%)
Kesto: {(datetime.now() - position.entry_time).total_seconds() / 3600:.1f}h
TX: {tx_hash[:16]}...
            """.strip()
            
            await self.send_telegram_message(message)
            
            self.logger.info(f"✅ Positio suljettu: {position.symbol}, PnL: {pnl_sol:+.6f} SOL")
            return True
            
        except Exception as e:
            self.logger.error(f"Virhe position sulkemisessa: {e}")
            return False

    async def monitor_positions(self):
        """Monitoroi avoimia positioita"""
        if not self.positions:
            return
            
        self.logger.info(f"👀 Monitoroidaan {len(self.positions)} positiota...")
        
        for address, position in list(self.positions.items()):
            try:
                # Hae nykyinen hinta
                current_price = await self.trader.get_token_price_sol(address)
                if not current_price:
                    self.logger.warning(f"❌ Ei saatu hintaa tokenille {position.symbol}")
                    continue
                
                # Tarkista exit ehdot
                should_exit = False
                exit_reason = ""
                
                # Stop loss
                if current_price <= position.stop_loss_price:
                    should_exit = True
                    exit_reason = f"Stop Loss ({current_price:.8f} <= {position.stop_loss_price:.8f})"
                
                # Take profit
                elif current_price >= position.take_profit_price:
                    should_exit = True
                    exit_reason = f"Take Profit ({current_price:.8f} >= {position.take_profit_price:.8f})"
                
                # Max hold time
                elif datetime.now() - position.entry_time > timedelta(hours=position.max_hold_hours):
                    should_exit = True
                    exit_reason = f"Max Hold Time ({position.max_hold_hours}h)"
                
                # Sulje positio jos tarpeen
                if should_exit:
                    await self.close_position(position, exit_reason)
                else:
                    # Logita status
                    pnl_percent = ((current_price - position.entry_price_sol) / position.entry_price_sol) * 100
                    self.logger.info(f"📊 {position.symbol}: {current_price:.8f} SOL ({pnl_percent:+.1f}%)")
                    
            except Exception as e:
                self.logger.error(f"Virhe position {position.symbol} monitoroinnissa: {e}")

    async def cleanup_cooldowns(self):
        """Siivoa vanhat cooldownit"""
        now = datetime.now()
        cooldown_hours = self.config["cooldown_hours"]
        
        expired_cooldowns = [
            addr for addr, time in self.cooldown_tokens.items()
            if now - time > timedelta(hours=cooldown_hours)
        ]
        
        for addr in expired_cooldowns:
            del self.cooldown_tokens[addr]
            
        if expired_cooldowns:
            self.logger.info(f"🧹 Poistettu {len(expired_cooldowns)} vanhaa cooldownia")

    async def print_status(self):
        """Tulosta status"""
        balance = await self.trader.get_sol_balance()
        
        self.logger.info("=" * 60)
        self.logger.info("📊 SOLANA AUTO TRADER STATUS")
        self.logger.info("=" * 60)
        self.logger.info(f"💰 SOL Balance: {balance:.6f}")
        self.logger.info(f"📈 Active Positions: {len(self.positions)}")
        self.logger.info(f"❄️  Cooldown Tokens: {len(self.cooldown_tokens)}")
        self.logger.info(f"🎯 Total Trades: {self.stats.total_trades}")
        self.logger.info(f"✅ Win Rate: {self.stats.win_rate:.1f}%")
        self.logger.info(f"💵 Net PnL: {self.stats.net_pnl_sol:+.6f} SOL")
        
        if self.positions:
            self.logger.info("\n🔍 Active Positions:")
            for pos in self.positions.values():
                age_hours = (datetime.now() - pos.entry_time).total_seconds() / 3600
                self.logger.info(f"  {pos.symbol}: {pos.entry_amount_sol:.3f} SOL, {age_hours:.1f}h")
        
        self.logger.info("=" * 60)

    async def run_trading_cycle(self):
        """Suorita yksi trading cycle"""
        try:
            self.logger.info("🔄 Aloitetaan trading cycle...")
            
            # 1. Siivoa cooldownit
            await self.cleanup_cooldowns()
            
            # 2. Monitoroi olemassa olevat positiot
            await self.monitor_positions()
            
            # 3. Etsi uusia mahdollisuuksia
            if len(self.positions) < self.config["max_positions"]:
                tokens = await self.scan_and_evaluate_tokens()
                
                # Avaa positioita parhaista tokeneista
                for token in tokens[:self.config["max_positions"] - len(self.positions)]:
                    success = await self.open_position(token)
                    if success:
                        # Odota hetki ennen seuraavaa
                        await asyncio.sleep(2)
            
            # 4. Tulosta status
            await self.print_status()
            
            self.logger.info("✅ Trading cycle valmis")
            
        except Exception as e:
            self.logger.error(f"Virhe trading cyclessa: {e}")

    async def run_forever(self, cycle_interval_minutes: int = 30):
        """Aja trader ikuisesti"""
        self.logger.info(f"🚀 Aloitetaan automaattinen trading, cycle: {cycle_interval_minutes}min")
        
        try:
            while True:
                await self.run_trading_cycle()
                
                # Odota seuraavaan cycleen
                self.logger.info(f"😴 Odotetaan {cycle_interval_minutes} minuuttia...")
                await asyncio.sleep(cycle_interval_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️  Pysäytetään trader...")
        except Exception as e:
            self.logger.error(f"Kriittinen virhe: {e}")
            raise

# Main funktio
async def main():
    """Main funktio"""
    try:
        async with SolanaAutoTrader() as trader:
            # Aja yksi cycle tai ikuisesti
            if len(os.sys.argv) > 1 and os.sys.argv[1] == "--once":
                await trader.run_trading_cycle()
            else:
                await trader.run_forever()
                
    except KeyboardInterrupt:
        print("👋 Trader pysäytetty")
    except Exception as e:
        print(f"❌ Virhe: {e}")
        raise

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())