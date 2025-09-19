# sources/mock_firehose.py
from __future__ import annotations
import asyncio, time, random, contextlib
from typing import Optional
from discovery_engine import TokenCandidate

class MockFirehoseSource:
    """
    Synteettinen lähde, joka työntää queueen N ehdokasta/sek. Käyttö kuormitustestissä.
    - rate_per_sec: tavoitelähetykset per sekunti (kokonaisluku)
    - burst: montako ehdokasta per tikki (helpottaa suuria nopeuksia)
    - jitter_ms: aikajitteri, ettei synny täydellistä lukkiutumista
    """
    def __init__(self, *, rate_per_sec: int = 500, burst: int = 10, jitter_ms: int = 5):
        self.rate = max(1, int(rate_per_sec))
        self.burst = max(1, int(burst))
        self.jitter_ms = max(0, int(jitter_ms))
        self._stop = asyncio.Event()
        self._candidates_generated = 0  # Laskuri tuotetuille ehdokkaille

    async def run(self, queue):
        try:
            # Lasketaan tikkien tahti: montako burstia/sek
            bursts_per_sec = max(1, self.rate // self.burst)
            tick = 1.0 / bursts_per_sec
            mint_counter = 0
            
            while not self._stop.is_set():
                # lähetä burst
                now = time.time()
                for _ in range(self.burst):
                    mint_counter += 1
                    c = TokenCandidate(
                        mint=f"MockMint{mint_counter:08d}",
                        symbol=f"MOCK{mint_counter%999}",
                        name=f"Mock Token {mint_counter}",
                        liquidity_usd=random.uniform(1000, 100000),
                        age_minutes=random.uniform(0, 60),
                        lp_locked=random.random() > 0.3,
                        mint_authority_renounced=random.random() > 0.2,
                        freeze_authority_renounced=random.random() > 0.2
                    )
                    try:
                        queue.put_nowait(c)
                        self._candidates_generated += 1  # Kasvata laskuria
                    except asyncio.QueueFull:
                        # Queue täynnä, ohita tämä ehdokas
                        pass

                # pieni jitter
                if self.jitter_ms:
                    await asyncio.sleep(tick + random.uniform(0, self.jitter_ms/1000.0))
                else:
                    await asyncio.sleep(tick)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Kuormitustestissä virheitä voi tulla QueueFull tms. — nielaistaan hillitysti
            await asyncio.sleep(0.01)

    def stop(self):
        self._stop.set()
