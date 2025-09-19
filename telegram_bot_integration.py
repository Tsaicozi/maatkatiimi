"""
Telegram Bot Integration - Automaattiset raportit ja ilmoitukset
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import aiohttp
import os
from dotenv import load_dotenv
from telegram_rate_limiter import init_telegram_rate_limiter, get_telegram_rate_limiter

# Ladataan API-avaimet
load_dotenv()

class TelegramBot:
    """Telegram bot ilmoituksille ja raporteille"""
    
    _inited = False
    
    def __init__(self, rate_limit_sec: int = 1, max_backoff_sec: int = 30, backoff_multiplier: float = 2.0):
        if TelegramBot._inited:
            return
        TelegramBot._inited = True
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.logger = logging.getLogger(__name__)
        
        if not self.bot_token or not self.chat_id:
            self.logger.warning("⚠️ Telegram API avaimet puuttuvat! Ilmoitukset eivät toimi.")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info("✅ Telegram bot alustettu")
        
        # Alusta rate limiter
        self.rate_limiter = init_telegram_rate_limiter(
            rate_limit_sec=rate_limit_sec,
            max_backoff_sec=max_backoff_sec,
            backoff_multiplier=backoff_multiplier
        )
        
        # Pollauskentät komennoille
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_offset: int = 0
    
    async def _send_raw_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Lähetä viesti Telegramiin (raw API kutsu)"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Korjaa parse entities virheet poistamalla ongelmalliset merkit
            if parse_mode == "Markdown":
                # Poista ongelmalliset Markdown-merkit jotka aiheuttavat parse virheitä
                message = message.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        # Jos parse entities virhe, yritä ilman parse_mode:a
                        if "parse entities" in error_text and parse_mode != "None":
                            return await self._send_raw_message(message, "None")
                        raise Exception(f"API virhe {response.status}: {error_text}")
                        
        except Exception as e:
            raise Exception(f"Telegram lähetysvirhe: {e}")

    async def send_message(self, message: str, parse_mode: str = "Markdown", priority: int = 0) -> bool:
        """Lähetä viesti Telegramiin rate limiting:lla"""
        if not self.enabled:
            self.logger.warning("Telegram bot ei ole käytössä")
            return False
        
        # Käytä rate limiter:ia
        success = await self.rate_limiter.send_message(
            send_func=lambda msg: self._send_raw_message(msg, parse_mode),
            message=message,
            priority=priority
        )
        
        if success:
            self.logger.info("✅ Telegram viesti lähetetty")
        else:
            self.logger.warning("⚠️ Telegram viesti epäonnistui")
        
        return success
    
    async def send_trading_signal(self, signal: Dict) -> bool:
        """Lähetä trading signaali"""
        try:
            token = signal.get('token', {})
            symbol = token.get('symbol', 'UNKNOWN')
            name = token.get('name', 'Unknown Token')
            price = token.get('price', 0)
            signal_type = signal.get('signal_type', 'UNKNOWN')
            confidence = signal.get('confidence', 0)
            reasoning = signal.get('reasoning', 'No reasoning provided')
            
            message = f"""
🚀 *UUSI TRADING SIGNAALI*

*Token:* {symbol} ({name})
*Hinta:* ${price:.6f}
*Signaali:* {signal_type}
*Luottamus:* {confidence:.1%}
*Perustelut:* {reasoning}

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe trading signaalin lähettämisessä: {e}")
            return False
    
    async def send_position_opened(self, position: Dict) -> bool:
        """Lähetä position avattu ilmoitus"""
        try:
            symbol = position.get('token', 'UNKNOWN')
            entry_price = position.get('entry_price', 0)
            position_size = position.get('position_size', 0)
            quantity = position.get('quantity', 0)
            
            message = f"""
✅ *POSITION AVATTU*

*Token:* {symbol}
*Entry Hinta:* ${entry_price:.6f}
*Position Koko:* ${position_size:.2f}
*Määrä:* {quantity:.6f}

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe position avattu ilmoituksen lähettämisessä: {e}")
            return False
    
    async def send_position_closed(self, position: Dict) -> bool:
        """Lähetä position suljettu ilmoitus"""
        try:
            symbol = position.get('token', 'UNKNOWN')
            entry_price = position.get('entry_price', 0)
            exit_price = position.get('exit_price', 0)
            quantity = position.get('quantity', 0)
            pnl = position.get('realized_pnl', 0)
            pnl_percentage = position.get('pnl_percentage', 0)
            
            emoji = "🟢" if pnl > 0 else "🔴"
            
            message = f"""
{emoji} *POSITION SULJETTU*

*Token:* {symbol}
*Entry:* ${entry_price:.6f}
*Exit:* ${exit_price:.6f}
*Määrä:* {quantity:.6f}
*P&L:* ${pnl:.2f} ({pnl_percentage:+.1f}%)

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe position suljettu ilmoituksen lähettämisessä: {e}")
            return False
    
    async def send_hourly_report(self, portfolio_summary: Dict, bot_stats: Dict) -> bool:
        """Lähetä tunnin välinen raportti"""
        try:
            # Portfolio tiedot
            portfolio_value = portfolio_summary.get('portfolio_value', 0)
            current_capital = portfolio_summary.get('current_capital', 0)
            total_exposure = portfolio_summary.get('total_exposure', 0)
            open_positions = portfolio_summary.get('open_positions', 0)
            closed_positions = portfolio_summary.get('closed_positions', 0)
            
            # Bot tilastot
            total_scans = bot_stats.get('total_scans', 0)
            total_signals = bot_stats.get('total_signals', 0)
            total_trades = bot_stats.get('total_trades', 0)
            success_rate = bot_stats.get('success_rate', 0)
            
            # Laske päivän tuotto
            daily_return = 0
            if portfolio_value > 0 and current_capital > 0:
                daily_return = ((portfolio_value - 10000) / 10000) * 100  # Oletetaan 10k alku
            
            # Portfolio emoji
            portfolio_emoji = "📈" if daily_return > 0 else "📉" if daily_return < 0 else "📊"
            
            message = f"""
{portfolio_emoji} *TUNNIN RAPORTTI*

*Portfolio:*
💰 Arvo: ${portfolio_value:.2f}
💵 Käteinen: ${current_capital:.2f}
📊 Exposure: ${total_exposure:.2f}
📈 Avoimet: {open_positions}
📉 Suljetut: {closed_positions}
📊 Päivän tuotto: {daily_return:+.2f}%

*Bot Tilastot:*
🔍 Skannauksia: {total_scans}
📡 Signaaleja: {total_signals}
💼 Kauppoja: {total_trades}
✅ Onnistumis%: {success_rate:.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe tunnin raportin lähettämisessä: {e}")
            return False
    
    async def send_daily_summary(self, daily_stats: Dict) -> bool:
        """Lähetä päivän yhteenveto"""
        try:
            total_trades = daily_stats.get('total_trades', 0)
            winning_trades = daily_stats.get('winning_trades', 0)
            losing_trades = daily_stats.get('losing_trades', 0)
            total_pnl = daily_stats.get('total_pnl', 0)
            best_trade = daily_stats.get('best_trade', 0)
            worst_trade = daily_stats.get('worst_trade', 0)
            
            message = f"""
📊 *PÄIVÄN YHTEENVETO*

*Kauppatilastot:*
💼 Yhteensä: {total_trades}
🟢 Voittavat: {winning_trades}
🔴 Häviävät: {losing_trades}
💰 Kokonais P&L: ${total_pnl:.2f}

*Parhaat/Huonoimmat:*
🏆 Paras: ${best_trade:.2f}
💸 Huonoin: ${worst_trade:.2f}

📅 {datetime.now().strftime('%Y-%m-%d')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe päivän yhteenvedon lähettämisessä: {e}")
            return False
    
    async def send_error_alert(self, error_message: str) -> bool:
        """Lähetä virhe ilmoitus"""
        try:
            message = f"""
🚨 *VIRHE ILMOITUS*

{error_message}

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe virhe ilmoituksen lähettämisessä: {e}")
            return False
    
    async def send_startup_message(self) -> bool:
        """Lähetä käynnistys ilmoitus"""
        try:
            message = f"""
🚀 *NEXTGEN TRADING BOT KÄYNNISTYI*

Bot on nyt aktiivinen ja skannaa uusia tokeneita.
Saat tunnin välein raportteja ja reaaliaikaisia ilmoituksia.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe käynnistys ilmoituksen lähettämisessä: {e}")
            return False
    
    async def send_shutdown_message(self) -> bool:
        """Lähetä sammutus ilmoitus"""
        try:
            message = f"""
🛑 *NEXTGEN TRADING BOT SAMMUTETTU*

Bot on nyt pysäytetty.
Kaikki positionit säilyvät.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            return await self.send_message(message.strip())
            
        except Exception as e:
            self.logger.error(f"Virhe sammutus ilmoituksen lähettämisessä: {e}")
            return False
    
    async def send_stats_message(self, stats_data: Dict) -> bool:
        """Lähetä /stats-komento vastaus (parannettu)"""
        try:
            message = "📊 *Bot Tilastot*\n\n"
            
            # Min score effective
            min_score = stats_data.get('min_score_effective', 0.0)
            message += f"🎯 Min Score: {min_score:.2f}\n"
            
            # Source health
            source_health = stats_data.get('source_health', {})
            health_icons = []
            for source, health in source_health.items():
                icon = "✅" if health else "❌"
                health_icons.append(f"{source}: {icon}")
            message += f"🔗 Sources: {', '.join(health_icons)}\n"
            
            # Live trading status
            live_enabled = stats_data.get('live_trading_enabled', False)
            live_status = "🟢 ENABLED" if live_enabled else "🔴 DISABLED"
            message += f"🚀 Live Trading: {live_status}\n"
            
            # Burn-in kriteerit
            burn_in_status = stats_data.get('burn_in_status', {})
            if burn_in_status:
                hot_per_hour = burn_in_status.get('hot_per_hour', 0)
                p95_cycle = burn_in_status.get('p95_cycle', 0)
                spam_ratio = burn_in_status.get('spam_ratio', 0)
                
                hot_status = "✅" if hot_per_hour >= 2 else "⚠️"
                cycle_status = "✅" if p95_cycle <= 3 else "⚠️"
                spam_status = "✅" if spam_ratio <= 0.8 else "⚠️"
                
                message += f"\n📈 *Burn-in Kriteerit:*\n"
                message += f"🔥 Hot/h: {hot_status} {hot_per_hour:.1f}\n"
                message += f"⏱️ P95 cycle: {cycle_status} {p95_cycle:.1f}s\n"
                message += f"📊 Spam ratio: {spam_status} {spam_ratio:.1%}\n"
            
            # Viimeiset hot candidates
            hot_candidates = stats_data.get('hot_candidates', [])
            if hot_candidates:
                message += f"\n🔥 *Viimeiset Hot Candidates:*\n"
                for i, candidate in enumerate(hot_candidates[:5], 1):
                    symbol = candidate.get('symbol', 'unknown')
                    score = candidate.get('score', 0.0)
                    age = candidate.get('age_min', 0.0)
                    buyers = candidate.get('buyers_5m', 0)
                    sources = candidate.get('sources', [])
                    sources_text = ', '.join(sources) if sources else 'unknown'
                    message += f"{i}) {symbol} — {score:.2f}\n"
                    message += f"   • age: {age:.1f}m, buyers: {buyers}, sources: {sources_text}\n"
            else:
                message += "\n🔥 Ei hot candidates viime aikoina\n"
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Virhe lähettäessä stats viestiä: {e}")
            return False
    
    async def send_mute_message(self, duration_minutes: int) -> bool:
        """Lähetä /mute-komento vastaus"""
        try:
            message = f"🔇 *Ilmoitukset hiljennetty*\n\n"
            message += f"⏰ Kesto: {duration_minutes} minuuttia\n"
            message += f"📊 Keräys jatkuu normaalisti\n"
            message += f"🔔 Ilmoitukset palautuvat automaattisesti"
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Virhe lähettäessä mute viestiä: {e}")
            return False
    
    async def send_approve_message(self, mint: str, ttl_hours: int) -> bool:
        """Lähetä /approve-komento vastaus"""
        try:
            mint_short = f"{mint[:8]}...{mint[-8:]}" if len(mint) > 16 else mint
            
            message = f"✅ *Manuaalinen hyväksyntä*\n\n"
            message += f"🪙 Mint: `{mint_short}`\n"
            message += f"⏰ TTL: {ttl_hours} tuntia\n"
            message += f"🚀 Live-kauppa sallittu tälle tokenille"
            
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Virhe lähettäessä approve viestiä: {e}")
            return False
    
    async def send_shadow_analysis_message(self, analysis_summary: str) -> bool:
        """Lähetä shadow analysis viesti"""
        try:
            message = f"📊 *Shadow Analysis Raportti*\n\n{analysis_summary}"
            return await self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Virhe lähettäessä shadow analysis viestiä: {e}")
            return False

    async def start_polling(self, on_command: Callable[[str, int], None], poll_interval: float = 1.0, allowed_chat_id: Optional[int] = None) -> None:
        """Käynnistä komennonpollaus"""
        if not self.enabled:
            self.logger.warning("⚠️ Telegram bot ei ole käytössä - komennonpollaus ohitetaan")
            return
            
        if self._poll_task is not None:
            self.logger.warning("⚠️ Pollaus jo käynnissä")
            return
            
        self.logger.info("🔄 Käynnistetään Telegram komennonpollaus...")
        
        async def _poll_loop():
            while True:
                try:
                    url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
                    params = {
                        'timeout': 25,
                        'offset': self._poll_offset + 1
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params, timeout=30) as resp:
                            if resp.status != 200:
                                self.logger.warning(f"Telegram API virhe: {resp.status}")
                                await asyncio.sleep(5)
                                continue
                                
                            data = await resp.json()
                            if not data.get('ok'):
                                self.logger.warning(f"Telegram API vastaus virhe: {data}")
                                await asyncio.sleep(5)
                                continue
                                
                            updates = data.get('result', [])
                            
                            for update in updates:
                                self._poll_offset = max(self._poll_offset, update.get('update_id', 0))
                                
                                message = update.get('message') or {}
                                chat_id = message.get('chat', {}).get('id')
                                text = (message.get('text') or '').strip()
                                
                                # Tarkista chat_id-rajoitus
                                if allowed_chat_id is not None and chat_id != allowed_chat_id:
                                    continue
                                    
                                # Käsittele komennot
                                if text.startswith('/stats'):
                                    await on_command('/stats', chat_id)
                                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.warning(f"Pollaus virhe: {e}")
                    await asyncio.sleep(5)
                    
                await asyncio.sleep(poll_interval)
        
        self._poll_task = asyncio.create_task(_poll_loop())
        self.logger.info("✅ Telegram komennonpollaus käynnistetty")

    async def stop_polling(self) -> None:
        """Pysäytä komennonpollaus"""
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
            self.logger.info("🛑 Telegram komennonpollaus pysäytetty")

# Testaa Telegram bot
async def test_telegram_bot():
    """Testaa Telegram bot toiminnallisuutta"""
    print("🧪 Testataan Telegram bot...")
    
    bot = TelegramBot()
    
    if not bot.enabled:
        print("❌ Telegram bot ei ole käytössä - tarkista API avaimet")
        return
    
    # Testaa viesti
    success = await bot.send_message("🧪 Testi viesti NextGen Trading Bot:lta!")
    
    if success:
        print("✅ Telegram bot toimii!")
    else:
        print("❌ Telegram bot ei toimi")

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())
