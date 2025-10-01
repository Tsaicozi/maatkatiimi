#!/usr/bin/env python3
"""
Telegram Rate Limiter with Backoff
Estää Telegram API:n tukkimisen ja toteuttaa eksponentiaalisen backoff:in
"""

import asyncio
import time
import logging
from typing import Optional, List
from dataclasses import dataclass
from collections import deque

log = logging.getLogger(__name__)

@dataclass
class MessageBuffer:
    """Viesti bufferi batching:lle"""
    messages: List[str]
    timestamp: float
    priority: int = 0  # 0=normaali, 1=korkea

class TelegramRateLimiter:
    """
    Telegram API rate limiter ja backoff-mechanismi
    
    Features:
    - Rate limiting (max 1 viesti/sekunti)
    - Exponential backoff virheiden jälkeen
    - Message batching
    - Priority queue
    """
    
    def __init__(self,
                 rate_limit_sec: float = 1,
                 max_backoff_sec: float = 30,
                 backoff_multiplier: float = 2.0,
                 batch_size: int = 5):
        try:
            self.rate_limit_sec = float(rate_limit_sec)
        except (TypeError, ValueError):
            log.warning("Invalid rate_limit_sec=%s, fallback 1.0", rate_limit_sec)
            self.rate_limit_sec = 1.0

        try:
            self.max_backoff_sec = float(max_backoff_sec)
        except (TypeError, ValueError):
            log.warning("Invalid max_backoff_sec=%s, fallback 30.0", max_backoff_sec)
            self.max_backoff_sec = 30.0

        try:
            self.backoff_multiplier = float(backoff_multiplier)
        except (TypeError, ValueError):
            log.warning("Invalid backoff_multiplier=%s, fallback 2.0", backoff_multiplier)
            self.backoff_multiplier = 2.0

        try:
            self.batch_size = int(batch_size)
        except (TypeError, ValueError):
            log.warning("Invalid batch_size=%s, fallback 5", batch_size)
            self.batch_size = 5

        if self.rate_limit_sec < 0:
            log.warning("rate_limit_sec %.2f < 0, clamped to 0", self.rate_limit_sec)
            self.rate_limit_sec = 0.0
        if self.max_backoff_sec < 0:
            log.warning("max_backoff_sec %.2f < 0, clamped to 0", self.max_backoff_sec)
            self.max_backoff_sec = 0.0
        if self.backoff_multiplier < 1.0:
            log.warning("backoff_multiplier %.2f < 1.0, clamped to 1.0", self.backoff_multiplier)
            self.backoff_multiplier = 1.0
        
        # Rate limiting
        self.last_send_time = 0.0
        self.send_times = deque(maxlen=10)  # Viimeisimmät lähetysajat
        
        # Backoff
        self.current_backoff = 0.0
        self.consecutive_errors = 0
        
        # Message batching
        self.message_buffer: List[MessageBuffer] = []
        self.buffer_lock = asyncio.Lock()
        
        log.info(f"📱 Telegram Rate Limiter alustettu: {rate_limit_sec}s rate limit, {max_backoff_sec}s max backoff")

    async def _wait_for_rate_limit(self):
        """Odota että rate limit sallii lähetyksen"""
        now = time.time()
        time_since_last = now - self.last_send_time
        
        if time_since_last < self.rate_limit_sec:
            wait_time = self.rate_limit_sec - time_since_last
            log.debug(f"⏳ Rate limit: odotetaan {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        # Päivitä lähetysajat
        self.last_send_time = time.time()
        self.send_times.append(self.last_send_time)

    async def _apply_backoff(self):
        """Sovella eksponentiaalinen backoff"""
        if self.current_backoff > 0:
            log.warning(f"⏳ Backoff: odotetaan {self.current_backoff:.1f}s")
            await asyncio.sleep(self.current_backoff)

    def _update_backoff(self, success: bool):
        """Päivitä backoff-tila"""
        if success:
            # Onnistunut kutsu → nollaa backoff
            self.current_backoff = 0.0
            self.consecutive_errors = 0
        else:
            # Epäonnistunut kutsu → kasvata backoff
            self.consecutive_errors += 1
            self.current_backoff = min(
                self.max_backoff_sec,
                self.current_backoff * self.backoff_multiplier + 1.0
            )
            log.warning(f"📈 Backoff kasvatettu: {self.current_backoff:.1f}s (virheitä: {self.consecutive_errors})")

    async def send_message(self, 
                          send_func: callable, 
                          message: str, 
                          priority: int = 0,
                          use_batching: bool = True) -> bool:
        """
        Lähetä viesti rate limiting:lla ja backoff:lla
        
        Args:
            send_func: Telegram lähetysfunktio
            message: Lähetettävä viesti
            priority: Prioriteetti (0=normaali, 1=korkea)
            use_batching: Käytä batching:ia jos mahdollista
        
        Returns:
            bool: Onnistuiko lähetys
        """
        try:
            # Korkean prioriteetin viestit lähetetään heti
            if priority > 0:
                return await self._send_immediate(send_func, message)
            
            # Normaalit viestit batcheen
            if use_batching:
                await self._add_to_buffer(message, priority)
                return await self._process_buffer(send_func)
            else:
                return await self._send_immediate(send_func, message)
                
        except Exception as e:
            log.error(f"❌ Telegram lähetysvirhe: {e}")
            self._update_backoff(False)
            return False

    async def _send_immediate(self, send_func: callable, message: str) -> bool:
        """Lähetä viesti heti (korkea prioriteetti)"""
        await self._apply_backoff()
        await self._wait_for_rate_limit()
        
        try:
            await send_func(message)
            self._update_backoff(True)
            log.debug("✅ Telegram viesti lähetetty")
            return True
        except Exception as e:
            log.error(f"❌ Telegram lähetysvirhe: {e}")
            self._update_backoff(False)
            return False

    async def _add_to_buffer(self, message: str, priority: int):
        """Lisää viesti bufferiin"""
        async with self.buffer_lock:
            self.message_buffer.append(MessageBuffer(
                messages=[message],
                timestamp=time.time(),
                priority=priority
            ))

    async def _process_buffer(self, send_func: callable) -> bool:
        """Käsittele viestibufferi"""
        async with self.buffer_lock:
            if not self.message_buffer:
                return True
            
            # Ryhmittele viestit
            messages_to_send = []
            current_priority = 0
            
            # Käsittele korkean prioriteetin viestit ensin
            high_priority = [b for b in self.message_buffer if b.priority > 0]
            normal_priority = [b for b in self.message_buffer if b.priority == 0]
            
            for buffer in high_priority + normal_priority:
                messages_to_send.extend(buffer.messages)
                if len(messages_to_send) >= self.batch_size:
                    break
            
            # Poista käsitellyt bufferit
            self.message_buffer = self.message_buffer[len(messages_to_send):]
        
        if messages_to_send:
            # Yhdistä viestit
            combined_message = "\n\n".join(messages_to_send)
            return await self._send_immediate(send_func, combined_message)
        
        return True

    async def flush_buffer(self, send_func: callable) -> bool:
        """Tyhjennä viestibufferi"""
        async with self.buffer_lock:
            if not self.message_buffer:
                return True
            
            all_messages = []
            for buffer in self.message_buffer:
                all_messages.extend(buffer.messages)
            
            self.message_buffer.clear()
        
        if all_messages:
            combined_message = "\n\n".join(all_messages)
            return await self._send_immediate(send_func, combined_message)
        
        return True

    def get_stats(self) -> dict:
        """Hae rate limiter tilastot"""
        now = time.time()
        recent_sends = [t for t in self.send_times if now - t < 60]  # Viimeisen minuutin
        
        return {
            "rate_limit_sec": self.rate_limit_sec,
            "current_backoff": self.current_backoff,
            "consecutive_errors": self.consecutive_errors,
            "messages_in_buffer": len(self.message_buffer),
            "recent_sends_per_minute": len(recent_sends),
            "last_send_time": self.last_send_time
        }

# Globaalinen rate limiter instanssi
_rate_limiter: Optional[TelegramRateLimiter] = None

def init_telegram_rate_limiter(rate_limit_sec: int = 1,
                              max_backoff_sec: int = 30,
                              backoff_multiplier: float = 2.0,
                              batch_size: int = 5) -> TelegramRateLimiter:
    """Alusta globaali Telegram rate limiter"""
    global _rate_limiter
    _rate_limiter = TelegramRateLimiter(rate_limit_sec, max_backoff_sec, backoff_multiplier, batch_size)
    return _rate_limiter

def get_telegram_rate_limiter() -> Optional[TelegramRateLimiter]:
    """Hae globaali Telegram rate limiter"""
    return _rate_limiter
