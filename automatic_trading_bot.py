"""
Automatic Trading Bot - Toimii itsenäisesti ja lähettää raportit Telegramiin
"""

import asyncio
import logging
import json
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Importoi komponentit
from demo_trading_bot import DemoNextGenTradingBot
from real_trading_bot import RealNextGenTradingBot
from telegram_bot_integration import TelegramBot

# Ladataan API-avaimet
load_dotenv()

class AutomaticTradingBot:
    """Automaattinen trading bot joka toimii itsenäisesti"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.logger = self.setup_logging()
        
        # Alusta komponentit
        self.trading_bot = RealNextGenTradingBot(telegram_bot=None)  # Telegram bot alustetaan myöhemmin
        self.telegram_bot = TelegramBot()
        
        # Automaattinen toiminta
        self.is_running = False
        self.scan_interval = 60  # 1 minuutti skannaus (reaaliaikainen)
        self.report_interval = 3600  # 1 tunti raportit
        self.last_scan_time = None
        self.last_report_time = None
        
        # Tilastot
        self.daily_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "start_time": datetime.now()
        }
        
        # Signaali käsittely
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("🚀 Automaattinen Trading Bot alustettu")
    
    def setup_logging(self):
        """Aseta logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automatic_trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Käsittele signaalit (Ctrl+C)"""
        self.logger.info(f"📡 Vastaanotettu signaali {signum}")
        asyncio.create_task(self.shutdown())
    
    async def startup(self):
        """Käynnistä bot"""
        try:
            self.logger.info("🚀 Käynnistetään automaattinen trading bot...")
            
            # Lähetä käynnistys ilmoitus
            await self.telegram_bot.send_startup_message()
            
            # Alusta päivän tilastot
            self.reset_daily_stats()
            
            # Käynnistä automaattinen toiminta
            self.is_running = True
            await self.run_automatic_trading()
            
        except Exception as e:
            self.logger.error(f"Virhe käynnistyksessä: {e}")
            await self.telegram_bot.send_error_alert(f"Käynnistys virhe: {e}")
    
    async def shutdown(self):
        """Sammuta bot"""
        try:
            self.logger.info("🛑 Sammutetaan automaattinen trading bot...")
            
            self.is_running = False
            
            # Lähetä sammutus ilmoitus
            await self.telegram_bot.send_shutdown_message()
            
            # Tallenna lopulliset tilastot
            await self.save_final_stats()
            
            self.logger.info("✅ Bot sammutettu onnistuneesti")
            
        except Exception as e:
            self.logger.error(f"Virhe sammutuksessa: {e}")
        finally:
            sys.exit(0)
    
    async def run_automatic_trading(self):
        """Aja automaattista tradingia"""
        self.logger.info("🔄 Aloitetaan automaattinen trading...")
        
        try:
            while self.is_running:
                current_time = datetime.now()
                
                # Tarkista onko aika skannata
                if (self.last_scan_time is None or 
                    (current_time - self.last_scan_time).total_seconds() >= self.scan_interval):
                    
                    await self.run_trading_cycle()
                    self.last_scan_time = current_time
                
                # Tarkista onko aika lähettää raportti
                if (self.last_report_time is None or 
                    (current_time - self.last_report_time).total_seconds() >= self.report_interval):
                    
                    await self.send_hourly_report()
                    self.last_report_time = current_time
                
                # Odota 10 sekuntia ennen seuraavaa tarkistusta (reaaliaikainen)
                await asyncio.sleep(10)
                
        except Exception as e:
            self.logger.error(f"Virhe automaattisessa tradingissa: {e}")
            await self.telegram_bot.send_error_alert(f"Automaattinen trading virhe: {e}")
    
    async def run_trading_cycle(self):
        """Suorita yksi trading sykli"""
        try:
            self.logger.info("🔄 Suoritetaan trading sykli...")
            
            # Suorita oikea analyysi sykli
            async with self.trading_bot as bot:
                bot.telegram_bot = self.telegram_bot  # Aseta Telegram bot
                result = await bot.run_analysis_cycle()
            
            if result.get("tokens_found", 0) > 0:
                # Päivitä tilastot
                self.update_daily_stats(result)
                
                self.logger.info(f"✅ Trading sykli valmis: {result.get('trades_executed', 0)} kauppaa")
            else:
                self.logger.warning(f"⚠️ Ei löytynyt tokeneita tällä skannauksella")
                
        except Exception as e:
            self.logger.error(f"Virhe trading syklissä: {e}")
            await self.telegram_bot.send_error_alert(f"Trading sykli virhe: {e}")
    
    async def send_trading_notifications(self, result: Dict):
        """Lähetä trading ilmoitukset reaaliajassa"""
        try:
            # Lähetä ilmoitus jos tehtiin kauppoja
            if result.get('trades_executed', 0) > 0:
                trades_count = result['trades_executed']
                message = f"💼 *{trades_count} uutta kauppaa suoritettu!*"
                await self.telegram_bot.send_message(message)
                
                # Lähetä yksityiskohtaiset tiedot kauppojen
                portfolio = result.get('portfolio_summary', {})
                positions = portfolio.get('positions', {})
                
                for token, position in positions.items():
                    await self.telegram_bot.send_position_opened({
                        'token': token,
                        'entry_price': position.get('entry_price', 0),
                        'position_size': position.get('position_value', 0),
                        'quantity': position.get('quantity', 0)
                    })
            
            # Lähetä ilmoitus jos generoitiin signaaleja
            if result.get('signals_generated', 0) > 0:
                signals_count = result['signals_generated']
                message = f"📡 *{signals_count} uutta signaalia generoitu!*"
                await self.telegram_bot.send_message(message)
            
            # Lähetä portfolio tilanne
            portfolio = result.get('portfolio_summary', {})
            if portfolio:
                portfolio_value = portfolio.get('portfolio_value', 0)
                open_positions = portfolio.get('open_positions', 0)
                message = f"📊 *Portfolio tilanne:*\n💰 Arvo: ${portfolio_value:.2f}\n📈 Avoimet: {open_positions}"
                await self.telegram_bot.send_message(message)
                
        except Exception as e:
            self.logger.error(f"Virhe trading ilmoitusten lähettämisessä: {e}")
    
    async def send_hourly_report(self):
        """Lähetä tunnin välinen raportti"""
        try:
            self.logger.info("📊 Lähetetään tunnin raportti...")
            
            # Hae bot tilastot
            bot_stats = self.trading_bot.get_bot_status()
            
            # Hae portfolio yhteenveto
            portfolio_summary = self.trading_bot.risk_engine.get_portfolio_summary()
            
            # Lähetä raportti
            await self.telegram_bot.send_hourly_report(portfolio_summary, bot_stats)
            
            self.logger.info("✅ Tunnin raportti lähetetty")
            
        except Exception as e:
            self.logger.error(f"Virhe tunnin raportin lähettämisessä: {e}")
            await self.telegram_bot.send_error_alert(f"Raportti virhe: {e}")
    
    async def send_daily_summary(self):
        """Lähetä päivän yhteenveto"""
        try:
            self.logger.info("📊 Lähetetään päivän yhteenveto...")
            
            await self.telegram_bot.send_daily_summary(self.daily_stats)
            
            self.logger.info("✅ Päivän yhteenveto lähetetty")
            
        except Exception as e:
            self.logger.error(f"Virhe päivän yhteenvedon lähettämisessä: {e}")
    
    def update_daily_stats(self, result: Dict):
        """Päivitä päivän tilastot"""
        try:
            trades_executed = result.get('trades_executed', 0)
            self.daily_stats['total_trades'] += trades_executed
            
            # Päivitä voittavat/häviävät kaupat
            portfolio = result.get('portfolio_summary', {})
            positions = portfolio.get('positions', {})
            
            for token, position in positions.items():
                pnl = position.get('unrealized_pnl', 0)
                if pnl > 0:
                    self.daily_stats['winning_trades'] += 1
                elif pnl < 0:
                    self.daily_stats['losing_trades'] += 1
                
                # Päivitä paras/huonoin kauppa
                if pnl > self.daily_stats['best_trade']:
                    self.daily_stats['best_trade'] = pnl
                if pnl < self.daily_stats['worst_trade']:
                    self.daily_stats['worst_trade'] = pnl
                
                self.daily_stats['total_pnl'] += pnl
            
        except Exception as e:
            self.logger.error(f"Virhe päivän tilastojen päivityksessä: {e}")
    
    def reset_daily_stats(self):
        """Nollaa päivän tilastot"""
        self.daily_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "start_time": datetime.now()
        }
    
    async def save_final_stats(self):
        """Tallenna lopulliset tilastot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"final_stats_{timestamp}.json"
            
            final_stats = {
                "daily_stats": self.daily_stats,
                "bot_stats": self.trading_bot.get_bot_status(),
                "portfolio_summary": self.trading_bot.risk_engine.get_portfolio_summary(),
                "end_time": datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(final_stats, f, indent=2, default=str)
            
            self.logger.info(f"💾 Lopulliset tilastot tallennettu: {filename}")
            
        except Exception as e:
            self.logger.error(f"Virhe lopullisten tilastojen tallentamisessa: {e}")
    
    async def check_daily_reset(self):
        """Tarkista onko aika nollata päivän tilastot"""
        try:
            current_time = datetime.now()
            start_time = self.daily_stats['start_time']
            
            # Jos on uusi päivä, nollaa tilastot
            if current_time.date() > start_time.date():
                await self.send_daily_summary()
                self.reset_daily_stats()
                self.logger.info("📅 Päivän tilastot nollattu")
                
        except Exception as e:
            self.logger.error(f"Virhe päivän nollauksen tarkistuksessa: {e}")
    
    def get_bot_status(self) -> Dict:
        """Hae bot tila"""
        return {
            "is_running": self.is_running,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "last_report_time": self.last_report_time.isoformat() if self.last_report_time else None,
            "scan_interval": self.scan_interval,
            "report_interval": self.report_interval,
            "daily_stats": self.daily_stats,
            "trading_bot_stats": self.trading_bot.get_bot_status()
        }

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Pääfunktio"""
    print("🚀 Automaattinen Trading Bot käynnistyy...")
    print("=" * 80)
    
    # Luo automaattinen bot
    bot = AutomaticTradingBot(initial_capital=10000.0)
    
    try:
        # Käynnistä bot
        await bot.startup()
        
    except KeyboardInterrupt:
        print("\n⏹️ Bot pysäytetty käyttäjän toimesta")
        await bot.shutdown()
    except Exception as e:
        print(f"❌ Virhe: {e}")
        await bot.shutdown()

if __name__ == "__main__":
    # Tarkista API avaimet
    if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
        print("⚠️ Varoitus: Telegram API avaimet puuttuvat!")
        print("Luo .env tiedosto ja lisää:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHAT_ID=your_chat_id")
        print("\nBot toimii ilman Telegram ilmoituksia...")
    
    # Käynnistä bot
    asyncio.run(main())
