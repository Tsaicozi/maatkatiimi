"""
Pytest konfiguraatio ja fixture:t
Varmistaa että kaikki taustatehtävät siivotaan testeissä
"""

import asyncio
import pytest
import logging

# Aseta logging level testejä varten
logging.basicConfig(level=logging.WARNING)

@pytest.fixture(autouse=True)
def no_task_leaks(event_loop):
    """
    Automaattinen fixture joka varmistaa ettei mikään task jää eloon testeissä
    
    Tämä fixture ajetaan automaattisesti jokaisen testin jälkeen ja:
    1. Etsii kaikki pending taskit
    2. Peruuttaa ne
    3. Odottaa että ne päättyvät
    """
    # Ennen testiä - ei tarvitse tehdä mitään
    yield
    
    # Testin jälkeen - siivoa pending taskit
    pending = [t for t in asyncio.all_tasks(loop=event_loop) if not t.done()]
    
    if pending:
        print(f"🧹 Siivotaan {len(pending)} pending taskia...")
        
        # Peruuta kaikki pending taskit
        for task in pending:
            task.cancel()
        
        # Odota että ne päättyvät
        try:
            event_loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
            print("✅ Kaikki pending taskit siivottu")
        except Exception as e:
            print(f"⚠️ Virhe siivotessa taskeja: {e}")

@pytest.fixture
def event_loop():
    """
    Luo uusi event loop jokaiselle testille
    Varmistaa että testit eivät vaikuta toisiinsa
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def reset_logging():
    """
    Resetoi logging jokaisen testin jälkeen
    Varmistaa että testit eivät vaikuta toisiinsa
    """
    # Ennen testiä
    original_level = logging.getLogger().level
    
    yield
    
    # Testin jälkeen - resetoi logging
    logging.getLogger().setLevel(original_level)
    
    # Poista kaikki handlers
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)
    
    # Lisää takaisin basic handler
    logging.basicConfig(level=logging.WARNING)

@pytest.fixture
def mock_discovery_engine():
    """
    Mock DiscoveryEngine testejä varten
    """
    from discovery_engine import DiscoveryEngine, TokenCandidate
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    class MockDiscoveryEngine:
        def __init__(self):
            self.running = False
            self.processed_candidates = {}
            self.candidate_queue = asyncio.Queue()
        
        async def start(self):
            self.running = True
        
        async def stop(self):
            self.running = False
        
        async def wait_closed(self, timeout=None):
            pass
        
        def best_candidates(self, k=5, min_score=0.65):
            # Palauta mock kandidatteja
            candidates = []
            for i in range(min(k, 3)):
                candidate = TokenCandidate(
                    mint=f"MOCK_MINT_{i}",
                    symbol=f"MOCK{i}",
                    name=f"Mock Token {i}",
                    overall_score=0.7 + (i * 0.1),
                    source="mock_test"
                )
                candidates.append(candidate)
            return candidates
    
    return MockDiscoveryEngine()

@pytest.fixture
def mock_telegram_bot():
    """
    Mock TelegramBot testejä varten
    """
    class MockTelegramBot:
        def __init__(self):
            self.sent_messages = []
        
        async def send_message(self, message: str):
            self.sent_messages.append(message)
            return {"ok": True, "result": {"message_id": len(self.sent_messages)}}
    
    return MockTelegramBot()


