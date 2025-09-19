#!/usr/bin/env python3
"""
HybridTradingBot Integration Tests
Testaa HybridTradingBot:in integraatiota DiscoveryEnginen kanssa
"""

import pytest
import asyncio
from unittest.mock import patch, Mock
from hybrid_trading_bot import HybridTradingBot


@pytest.mark.asyncio
async def test_hybrid_bot_with_discovery():
    """
    Testaa HybridTradingBot:in run_analysis_cycle() metodia
    DiscoveryEngine käynnistyy taustalle, mutta ilman lähdeadaptereita se idlaa deterministisesti
    """
    # Luo bot instance
    bot = HybridTradingBot()
    
    try:
        # Käynnistä discovery taustalle, mutta ilman lähteitä se idlaa deterministisesti
        res = await bot.run_analysis_cycle()
        
        # Tarkista että vastaus sisältää vaaditut kentät
        assert isinstance(res, dict)
        assert "hot_candidates" in res
        assert isinstance(res["hot_candidates"], list)
        
        # Tarkista muita odotettuja kenttiä
        expected_keys = [
            "tokens_found", "signals_generated", "trades_executed",
            "timestamp", "tokens_scanned", "tokens_analyzed",
            "portfolio_value", "portfolio_pnl", "active_positions",
            "performance_metrics", "risk_metrics", "tokens", "positions", "signals"
        ]
        
        for key in expected_keys:
            assert key in res, f"Puuttuva avain: {key}"
        
        # Tarkista että hot_candidates on lista
        assert isinstance(res["hot_candidates"], list)
        
        # Tarkista että portfolio tiedot ovat oikeassa muodossa
        assert isinstance(res["portfolio_value"], (int, float))
        assert isinstance(res["portfolio_pnl"], (int, float))
        assert isinstance(res["active_positions"], int)
        
        # Tarkista että performance_metrics on dict
        assert isinstance(res["performance_metrics"], dict)
        
        # Tarkista että risk_metrics on dict
        assert isinstance(res["risk_metrics"], dict)
        
    finally:
        # Varmista siisti sammutus
        await bot.stop()


@pytest.mark.asyncio
async def test_hybrid_bot_discovery_engine_integration():
    """
    Testaa että HybridTradingBot:in DiscoveryEngine integraatio toimii
    """
    bot = HybridTradingBot()
    
    try:
        # Tarkista että DiscoveryEngine on alustettu
        assert hasattr(bot, 'discovery_engine')
        
        if bot.discovery_engine is not None:
            # Tarkista DiscoveryEngine perustiedot
            assert hasattr(bot.discovery_engine, 'rpc_endpoint')
            assert hasattr(bot.discovery_engine, 'market_sources')
            assert hasattr(bot.discovery_engine, 'min_liq_usd')
            
            # Tarkista että market_sources on lista (voi olla tyhjä)
            assert isinstance(bot.discovery_engine.market_sources, list)
            
            # Tarkista että min_liq_usd on positiivinen
            assert bot.discovery_engine.min_liq_usd > 0
            
            print(f"✅ DiscoveryEngine löytyy: {len(bot.discovery_engine.market_sources)} lähdettä")
        else:
            print("⚠️ DiscoveryEngine on None (ei virhe)")
        
        # Testaa run_analysis_cycle
        result = await bot.run_analysis_cycle()
        
        # Tarkista että hot_candidates kenttä löytyy
        assert "hot_candidates" in result
        assert isinstance(result["hot_candidates"], list)
        
        print(f"✅ run_analysis_cycle onnistui: {len(result['hot_candidates'])} hot candidates")
        
    finally:
        await bot.stop()


@pytest.mark.asyncio
async def test_hybrid_bot_with_mock_discovery():
    """
    Testaa HybridTradingBot:ia mock DiscoveryEnginellä
    """
    # Mock DiscoveryEngine
    class MockDiscoveryEngine:
        def __init__(self):
            self.running = False
            self.processed_candidates = {}
        
        async def start(self):
            self.running = True
        
        async def stop(self):
            self.running = False
        
        async def wait_closed(self, timeout=None):
            pass
        
        def best_candidates(self, k=5, min_score=0.65):
            # Palauta mock kandidatteja
            from discovery_engine import TokenCandidate
            candidates = []
            for i in range(min(k, 2)):
                candidate = TokenCandidate(
                    mint=f"MOCK_MINT_{i}",
                    symbol=f"MOCK{i}",
                    name=f"Mock Token {i}",
                    overall_score=0.7 + (i * 0.1),
                    source="mock_test"
                )
                candidates.append(candidate)
            return candidates
    
    # Luo bot ja korvaa DiscoveryEngine mock:lla
    bot = HybridTradingBot()
    bot.discovery_engine = MockDiscoveryEngine()
    
    try:
        # Testaa run_analysis_cycle mock:lla
        result = await bot.run_analysis_cycle()
        
        # Tarkista että vastaus on oikeassa muodossa
        assert isinstance(result, dict)
        assert "hot_candidates" in result
        assert isinstance(result["hot_candidates"], list)
        
        # Mock:lla pitäisi olla hot candidates
        assert len(result["hot_candidates"]) > 0
        
        print(f"✅ Mock test onnistui: {len(result['hot_candidates'])} hot candidates")
        
    finally:
        await bot.stop()


@pytest.mark.asyncio
async def test_hybrid_bot_error_handling():
    """
    Testaa HybridTradingBot:in virheenkäsittelyä
    """
    bot = HybridTradingBot()
    
    try:
        # Testaa että bot käsittelee virheet gracefulisti
        result = await bot.run_analysis_cycle()
        
        # Vaikka olisi virheitä, vastaus pitäisi olla dict
        assert isinstance(result, dict)
        
        # Jos on virhe, sen pitäisi olla 'error' kentässä
        if "error" in result:
            assert isinstance(result["error"], str)
            print(f"⚠️ Virhe havaittu: {result['error']}")
        else:
            print("✅ Ei virheitä")
        
    finally:
        await bot.stop()


def test_hybrid_bot_initialization():
    """
    Testaa HybridTradingBot:in alustusta (sync test)
    """
    bot = HybridTradingBot()
    
    # Tarkista perustiedot
    assert hasattr(bot, 'portfolio')
    assert hasattr(bot, 'telegram_bot')
    assert hasattr(bot, 'discovery_engine')
    
    # Tarkista portfolio
    assert isinstance(bot.portfolio, dict)
    assert 'cash' in bot.portfolio
    assert 'positions' in bot.portfolio
    assert 'total_value' in bot.portfolio
    
    # Tarkista että portfolio arvot ovat järkeviä
    assert bot.portfolio['cash'] > 0
    assert bot.portfolio['total_value'] > 0
    assert isinstance(bot.portfolio['positions'], dict)
    
    print("✅ HybridTradingBot alustus onnistui")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])


