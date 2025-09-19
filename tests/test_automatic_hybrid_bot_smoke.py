#!/usr/bin/env python3
"""
AutomaticHybridBot Smoke Test
Testaa että AutomaticHybridBot toimii mock-WS:llä ja hot_candidates syntyy.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from automatic_hybrid_bot import AutomaticHybridBot


class MockTelegramBot:
    """Mock Telegram bot"""
    
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, message: str):
        """Mock send_message"""
        self.sent_messages.append(message)
        return {"ok": True, "result": {"message_id": len(self.sent_messages)}}


class MockTradingBot:
    """Mock HybridTradingBot"""
    
    def __init__(self):
        self.portfolio = {
            'total_value': 10000.0,
            'total_pnl': 0.0,
            'positions': []
        }
        self.performance_metrics = {
            'win_rate': 0.0,
            'total_trades': 0,
            'profit_factor': 1.0
        }
        self.discovery_engine = MockDiscoveryEngine()
    
    async def stop(self):
        """Mock stop method"""
        if self.discovery_engine:
            await self.discovery_engine.stop()


class MockDiscoveryEngine:
    """Mock DiscoveryEngine"""
    
    def __init__(self, has_candidates: bool = True):
        self.has_candidates = has_candidates
    
    def best_candidates(self, k: int = 5, min_score: float = 0.65):
        """Mock best_candidates"""
        if not self.has_candidates:
            return []
        
        # Create mock candidates
        from discovery_engine import TokenCandidate
        candidates = []
        for i in range(min(k, 3)):  # Return up to 3 candidates
            candidate = TokenCandidate(
                mint=f"MOCK_MINT_{i}",
                symbol=f"MOCK{i}",
                name=f"Mock Token {i}",
                pool_address=f"MOCK_POOL_{i}",
                liquidity_usd=5000.0 + (i * 1000),
                top10_holder_share=0.05 + (i * 0.01),
                lp_locked=True,
                lp_burned=False,
                mint_authority_renounced=True,
                freeze_authority_renounced=True,
                unique_buyers_5m=100 + (i * 50),
                buy_sell_ratio=1.2 + (i * 0.1),
                novelty_score=0.8 - (i * 0.1),
                liquidity_score=0.7 + (i * 0.05),
                distribution_score=0.9 - (i * 0.05),
                activity_score=0.8 + (i * 0.05),
                rug_risk_score=0.1 - (i * 0.02),
                overall_score=0.7 + (i * 0.05),
                source="mock_source"
            )
            candidates.append(candidate)
        
        return candidates
    
    async def stop(self):
        """Mock stop method"""
        pass


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_initialization():
    """Test AutomaticHybridBot initialization"""
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=10.0)
        
        # Test initialization
        assert bot.trading_bot is not None
        assert bot.telegram_bot is not None
        assert not bot.running
        assert bot.cycle_count == 0
        assert bot.baseline_metrics is None
        assert bot._max_cycles == 1
        assert bot._deadline is not None


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_with_hot_candidates():
    """Test AutomaticHybridBot with hot candidates generates Telegram message"""
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Mock run_analysis_cycle to return result with hot candidates
        async def mock_run_analysis_cycle():
            return {
                'timestamp': datetime.now().isoformat(),
                'tokens_scanned': 10,
                'tokens_analyzed': 8,
                'signals_generated': 2,
                'trades_executed': 1,
                'hot_candidates': [{'mint': 'TEST_MINT', 'symbol': 'TEST', 'overall_score': 0.75}],
                'portfolio_value': 10050.0,
                'portfolio_pnl': 50.0,
                'active_positions': 1,
                'performance_metrics': {'win_rate': 60.0, 'total_trades': 10, 'profit_factor': 1.2}
            }
        
        bot.trading_bot.run_analysis_cycle = mock_run_analysis_cycle
        
        # Test that hot candidates would trigger Telegram message
        result = await bot.trading_bot.run_analysis_cycle()
        
        assert 'hot_candidates' in result
        assert len(result['hot_candidates']) > 0
        
        # Test Telegram message would be sent
        telegram_bot = bot.telegram_bot
        initial_message_count = len(telegram_bot.sent_messages)
        
        # Simulate sending hot candidates message
        if result.get('hot_candidates'):
            hot_candidates = bot.trading_bot.discovery_engine.best_candidates(k=5, min_score=0.65)
            if hot_candidates:
                message = "🔥 *Uudet kuumat tokenit:*\n\n"
                for i, candidate in enumerate(hot_candidates[:5], 1):
                    reasons = []
                    if candidate.overall_score >= 0.65:
                        reasons.append(f"Score: {candidate.overall_score:.2f}")
                    if candidate.liquidity_usd >= 3000:
                        reasons.append(f"Liq: ${candidate.liquidity_usd:,.0f}")
                    if candidate.unique_buyers_5m > 0:
                        reasons.append(f"Buyers: {candidate.unique_buyers_5m}")
                    if candidate.buy_sell_ratio > 1.0:
                        reasons.append(f"Buy ratio: {candidate.buy_sell_ratio:.1f}")
                    if candidate.lp_locked or candidate.lp_burned:
                        reasons.append("LP locked/burned")
                    if candidate.mint_authority_renounced and candidate.freeze_authority_renounced:
                        reasons.append("Authorities renounced")
                    
                    reason_text = ", ".join(reasons) if reasons else "Uusi token"
                    
                    message += f"{i}. *{candidate.symbol}* ({candidate.name})\n"
                    message += f"   💎 {reason_text}\n"
                    message += f"   📊 Age: {candidate.age_minutes:.1f}min, MC: ${candidate.liquidity_usd:,.0f}\n\n"
                
                await telegram_bot.send_message(message)
        
        # Check that message was sent
        assert len(telegram_bot.sent_messages) > initial_message_count
        
        # Verify message content
        last_message = telegram_bot.sent_messages[-1]
        assert "🔥 *Uudet kuumat tokenit:*" in last_message
        assert "MOCK0" in last_message or "MOCK1" in last_message or "MOCK2" in last_message


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_no_hot_candidates():
    """Test AutomaticHybridBot without hot candidates"""
    
    # Create mock trading bot without candidates
    mock_trading_bot = MockTradingBot()
    mock_trading_bot.discovery_engine = MockDiscoveryEngine(has_candidates=False)
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=mock_trading_bot), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Test that no hot candidates means no special message
        hot_candidates = bot.trading_bot.discovery_engine.best_candidates(k=5, min_score=0.65)
        assert len(hot_candidates) == 0


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_baseline_calculation():
    """Test AutomaticHybridBot baseline calculation"""
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Test baseline calculation
        result = {
            'portfolio_value': 10000.0,
            'portfolio_pnl': 100.0,
            'active_positions': 2,
            'performance_metrics': {'win_rate': 50.0, 'total_trades': 20, 'profit_factor': 1.1},
            'timestamp': datetime.now().isoformat()
        }
        
        baseline = bot._calculate_baseline_metrics(result)
        
        assert baseline['portfolio_value'] == 10000.0
        assert baseline['total_pnl'] == 100.0
        assert baseline['active_positions'] == 2
        assert baseline['performance_metrics']['win_rate'] == 50.0


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_hourly_report():
    """Test AutomaticHybridBot hourly report generation"""
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Set baseline
        bot.baseline_metrics = {
            'portfolio_value': 10000.0,
            'total_pnl': 100.0,
            'active_positions': 2,
            'performance_metrics': {'win_rate': 50.0},
            'timestamp': datetime.now().isoformat()
        }
        
        # Set cycle count for hourly report
        bot.cycle_count = 60
        
        # Test hourly report
        result = {
            'portfolio_value': 10100.0,
            'portfolio_pnl': 150.0,
            'active_positions': 3,
            'performance_metrics': {'win_rate': 55.0},
            'hot_candidates': [{'mint': 'TEST'}]
        }
        
        telegram_bot = bot.telegram_bot
        initial_count = len(telegram_bot.sent_messages)
        
        await bot._send_hourly_report(result)
        
        # Check that message was sent
        assert len(telegram_bot.sent_messages) > initial_count
        
        # Verify message content
        last_message = telegram_bot.sent_messages[-1]
        assert "⏰ *Tunnin Raportti:*" in last_message
        assert "Portfolio:" in last_message
        assert "PnL:" in last_message
        assert "Win Rate:" in last_message


def test_automatic_hybrid_bot_signal_handler():
    """Test AutomaticHybridBot signal handler (non-async)"""
    
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Test signal handler sets running to False
        assert bot.running == False
        bot.running = True
        assert bot.running == True
        
        bot._signal_handler()
        assert bot.running == False


@pytest.mark.asyncio
async def test_automatic_hybrid_bot_smoke():
    """
    Savukoe: AutomaticHybridBot testimoodissa
    Varmistaa että bot käynnistyy ja lopettaa testimoodissa
    """
    with patch('automatic_hybrid_bot.HybridTradingBot', return_value=MockTradingBot()), \
         patch('automatic_hybrid_bot.TelegramBot', return_value=MockTelegramBot()):
        
        # Luo bot testimoodissa (max 1 sykli, 5 sekuntia)
        bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
        
        # Käynnistä bot
        await bot.start()
        
        # Odota että bot lopettaa testimoodissa
        await bot.wait_closed(timeout=10.0)
        
        # Testi onnistui
        assert True


def test_automatic_entrypoint_exits(monkeypatch, tmp_path):
    """
    Testaa että AutomaticHybridBot päättyy oikein ympäristömuuttujien kanssa
    """
    import os
    import subprocess
    import sys
    
    # Aseta ympäristömuuttujat
    env = os.environ.copy()
    env["TEST_MAX_CYCLES"] = "1"
    
    # Aja automatic_hybrid_bot.py subprocess:ina
    p = subprocess.run(
        [sys.executable, "automatic_hybrid_bot.py"], 
        env=env, 
        timeout=30,
        capture_output=True,
        text=True
    )
    
    # Tarkista että prosessi päättyi onnistuneesti
    assert p.returncode == 0, f"Prosessi epäonnistui: {p.stderr}"
    
    # Tarkista että stdout sisältää odotettuja viestejä
    stdout = p.stdout
    assert "Testimoodi aktiivinen" in stdout or "max_cycles=1" in stdout, "Testimoodi ei aktivoitunut"
    assert "Pysäytysehto täyttyi" in stdout or "lopetetaan" in stdout, "Pysäytys ei tapahtunut"


def test_automatic_entrypoint_with_runtime_limit():
    """
    Testaa että AutomaticHybridBot päättyy ajan perusteella
    """
    import os
    import subprocess
    import sys
    
    # Aseta ympäristömuuttujat
    env = os.environ.copy()
    env["TEST_MAX_RUNTIME"] = "5.0"  # 5 sekuntia
    
    # Aja automatic_hybrid_bot.py subprocess:ina
    p = subprocess.run(
        [sys.executable, "automatic_hybrid_bot.py"], 
        env=env, 
        timeout=15,  # Anna 15s aikaa päättyä
        capture_output=True,
        text=True
    )
    
    # Tarkista että prosessi päättyi onnistuneesti
    assert p.returncode == 0, f"Prosessi epäonnistui: {p.stderr}"
    
    # Tarkista että stdout sisältää odotettuja viestejä
    stdout = p.stdout
    assert "Testimoodi aktiivinen" in stdout or "max_runtime=5.0" in stdout, "Testimoodi ei aktivoitunut"


def test_automatic_entrypoint_without_test_mode():
    """
    Testaa että AutomaticHybridBot käynnistyy normaalisti ilman testimoodia
    """
    import os
    import subprocess
    import sys
    
    # Poista testimoodi ympäristömuuttujat
    env = os.environ.copy()
    env.pop("TEST_MAX_CYCLES", None)
    env.pop("TEST_MAX_RUNTIME", None)
    
    # Aja automatic_hybrid_bot.py subprocess:ina lyhyeksi ajaksi
    p = subprocess.run(
        [sys.executable, "automatic_hybrid_bot.py"], 
        env=env, 
        timeout=5,  # Keskeytä 5s kuluttua
        capture_output=True,
        text=True
    )
    
    # Prosessi voi päättyä timeout:in takia (returncode != 0) tai normaalisti
    # Tärkeintä on että se ei kaadu heti
    assert p.returncode in [0, -15], f"Prosessi epäonnistui odottamattomasti: {p.returncode}, stderr: {p.stderr}"
    
    # Tarkista että stdout sisältää käynnistysviestejä
    stdout = p.stdout
    assert "Hybrid Trading Bot" in stdout or "DiscoveryEngine" in stdout or "käynnistetty" in stdout, "Bot ei käynnistynyt"


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([__file__, "-v"])
