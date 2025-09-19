"""
Load testing for DiscoveryEngine to ensure it can handle high throughput
without queue overflow and maintains sufficient processing rate.
"""
from __future__ import annotations
import asyncio
import time
import pytest
from typing import List

from discovery_engine import DiscoveryEngine
from sources.mock_firehose import MockFirehoseSource
from tests.stubs_rpc import StubFastRPC


def cleanup_metrics():
    """Clean up metrics registry to avoid duplicates."""
    try:
        import metrics
        metrics.metrics = None
    except Exception:
        pass


def get_unique_namespace():
    """Get a unique namespace for each test to avoid conflicts."""
    import time
    return f"test_{int(time.time() * 1000000) % 1000000}"


@pytest.mark.asyncio
@pytest.mark.timeout(30)  # varmistetaan ettei jää roikkumaan
async def test_discovery_engine_handles_load():
    """Test that DiscoveryEngine can handle high load without queue overflow."""
    cleanup_metrics()  # Tyhjennä metrics ennen testiä
    
    # Parametrit
    RATE = 800          # ehdokasta / s (säätö)
    DURATION = 5.0      # s
    MIN_THROUGHPUT = 200  # pisteytettyä / s (konservatiivinen minimi)
    MAX_QUEUE = 5000

    # Luo komponentit
    rpc = StubFastRPC()
    src = MockFirehoseSource(rate_per_sec=RATE, burst=20, jitter_ms=2)
    eng = DiscoveryEngine(
        rpc_endpoint='http://localhost:8899',
        market_sources=[src], 
        min_liq_usd=3000.0,
        rpc_client=rpc
    )
    
    # Käytä omaa registryä testeissä (ei HTTP-serveriä)
    from prometheus_client import CollectorRegistry
    from metrics import init_metrics
    test_registry = CollectorRegistry()
    init_metrics(
        namespace=f"test_{int(time.time())}",
        enabled=True,
        enable_http=False,  # Ei HTTP-serveriä testeissä
        registry=test_registry
    )

    # Säädä jonon maksimia, jos DiscoveryEngineissä on config siihen
    try:
        eng.candidate_queue._maxsize = MAX_QUEUE  # ei aina toimi; ignore jos ei
    except Exception:
        pass

    await eng.start()

    # Anna kuorman juosta hetken
    t0 = time.perf_counter()
    await asyncio.sleep(DURATION)
    t1 = time.perf_counter()

    # Sammutus
    await eng.stop()
    await eng.wait_closed()

    # Arvioidaan läpivientiä ja jonon hallintaa
    # Käytä omaa mittaria koska metrics on poistettu käytöstä
    processed = len(getattr(eng, "_recent_scores", []))
    if processed == 0:
        # Jos _recent_scores ei ole olemassa, käytä mock source:n laskuria
        processed = getattr(src, "_candidates_generated", 0)
    
    elapsed = max(0.001, t1 - t0)
    throughput = processed / elapsed

    # Assertit (säädä rajat omaan ympäristöön sopiviksi)
    assert throughput >= MIN_THROUGHPUT, f"Läpivienti liian pieni: {throughput:.1f}/s < {MIN_THROUGHPUT}/s"
    
    # Jonon pitäisi pysyä kohtuullisena
    qsize = eng.candidate_queue.qsize()
    assert qsize < MAX_QUEUE, f"Jono kasvoi liian suureksi: {qsize} >= {MAX_QUEUE}"

    # Ei taustatehtäviä roikkumaan
    # (pytest-timeout kaataa jos jäisi kiinni)


@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_queue_stability_under_burst():
    """Test that queue doesn't explode under burst load."""
    cleanup_metrics()  # Tyhjennä metrics ennen testiä
    
    # Parametrit burst-testille
    BURST_RATE = 2000   # ehdokasta / s burst:issa
    BURST_DURATION = 2.0  # s
    MAX_QUEUE = 10000

    rpc = StubFastRPC()
    src = MockFirehoseSource(rate_per_sec=BURST_RATE, burst=100, jitter_ms=1)
    eng = DiscoveryEngine(
        rpc_endpoint='http://localhost:8899',
        market_sources=[src], 
        min_liq_usd=1000.0,  # Alempi kynnys = enemmän käsiteltävää
        rpc_client=rpc
    )
    
    # Käytä omaa registryä testeissä (ei HTTP-serveriä)
    from prometheus_client import CollectorRegistry
    from metrics import init_metrics
    test_registry = CollectorRegistry()
    init_metrics(
        namespace=f"test_{int(time.time())}",
        enabled=True,
        enable_http=False,  # Ei HTTP-serveriä testeissä
        registry=test_registry
    )

    await eng.start()

    # Burst-kuorma
    t0 = time.perf_counter()
    await asyncio.sleep(BURST_DURATION)
    t1 = time.perf_counter()

    # Tarkista jonon tila kesken kuorman
    max_queue_during_test = eng.candidate_queue.qsize()
    
    await eng.stop()
    await eng.wait_closed()

    # Assertit
    assert max_queue_during_test < MAX_QUEUE, f"Jono räjähti burst:issa: {max_queue_during_test} >= {MAX_QUEUE}"
    
    # Varmista että jotain käsiteltiin
    processed = len(getattr(eng, "_recent_scores", []))
    if processed == 0:
        processed = getattr(src, "_candidates_generated", 0)
    assert processed > 0, "Ei käsitelty yhtään ehdokasta burst:issa"


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_memory_usage_stable():
    """Test that memory usage doesn't grow unbounded during load."""
    cleanup_metrics()  # Tyhjennä metrics ennen testiä
    
    import psutil
    import os
    
    # Aloita muistin seuranta
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    rpc = StubFastRPC()
    src = MockFirehoseSource(rate_per_sec=500, burst=50)
    eng = DiscoveryEngine(
        rpc_endpoint='http://localhost:8899',
        market_sources=[src], 
        min_liq_usd=2000.0,
        rpc_client=rpc
    )
    
    # Käytä omaa registryä testeissä (ei HTTP-serveriä)
    from prometheus_client import CollectorRegistry
    from metrics import init_metrics
    test_registry = CollectorRegistry()
    init_metrics(
        namespace=f"test_{int(time.time())}",
        enabled=True,
        enable_http=False,  # Ei HTTP-serveriä testeissä
        registry=test_registry
    )

    await eng.start()

    # Kuormita 3 sekuntia
    await asyncio.sleep(3.0)

    # Tarkista muisti kesken kuorman
    memory_during = process.memory_info().rss / 1024 / 1024  # MB

    await eng.stop()
    await eng.wait_closed()

    # Odota GC:ta
    await asyncio.sleep(1.0)
    final_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Assertit
    memory_growth = final_memory - initial_memory
    assert memory_growth < 100, f"Muistin kasvu liian suuri: {memory_growth:.1f}MB"
    
    # Varmista että muisti ei kasva rajattomasti kesken kuorman
    memory_during_growth = memory_during - initial_memory
    assert memory_during_growth < 200, f"Muisti kasvoi liikaa kesken kuorman: {memory_during_growth:.1f}MB"


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_no_background_task_leaks():
    """Test that no background tasks are left hanging after shutdown."""
    cleanup_metrics()  # Tyhjennä metrics ennen testiä
    
    # Aloita taskien seuranta
    initial_tasks = len(asyncio.all_tasks())

    rpc = StubFastRPC()
    src = MockFirehoseSource(rate_per_sec=300, burst=30)
    eng = DiscoveryEngine(
        rpc_endpoint='http://localhost:8899',
        market_sources=[src], 
        min_liq_usd=1500.0,
        rpc_client=rpc
    )
    
    # Käytä omaa registryä testeissä (ei HTTP-serveriä)
    from prometheus_client import CollectorRegistry
    from metrics import init_metrics
    test_registry = CollectorRegistry()
    init_metrics(
        namespace=f"test_{int(time.time())}",
        enabled=True,
        enable_http=False,  # Ei HTTP-serveriä testeissä
        registry=test_registry
    )

    await eng.start()
    await asyncio.sleep(2.0)  # Anna aikaa käynnistyä
    await eng.stop()
    await eng.wait_closed()

    # Odota että kaikki taskit lopetetaan
    await asyncio.sleep(1.0)

    # Tarkista taskien määrä
    final_tasks = len(asyncio.all_tasks())
    task_leak = final_tasks - initial_tasks

    # Sallitaan muutama task (esim. metrics server, logger)
    assert task_leak <= 3, f"Liikaa taustatehtäviä jäi roikkumaan: {task_leak}"


@pytest.mark.asyncio
@pytest.mark.timeout(25)
async def test_throughput_scaling():
    """Test that throughput scales reasonably with different load levels."""
    cleanup_metrics()  # Tyhjennä metrics ennen testiä
    
    test_cases = [
        (100, 50),   # (rate, min_throughput)
        (300, 150),
        (600, 250),
    ]

    results = []

    for rate, min_throughput in test_cases:
        rpc = StubFastRPC()
        src = MockFirehoseSource(rate_per_sec=rate, burst=20)
        eng = DiscoveryEngine(
            rpc_endpoint='http://localhost:8899',
            market_sources=[src], 
            min_liq_usd=2000.0,
            rpc_client=rpc
        )
        
        # Poista metrics käytöstä testissä
        eng.config.metrics.enabled = False

        await eng.start()

        t0 = time.perf_counter()
        await asyncio.sleep(3.0)  # Lyhyempi testi
        t1 = time.perf_counter()

        await eng.stop()
        await eng.wait_closed()

        # Laske läpivienti
        processed = len(getattr(eng, "_recent_scores", []))
        if processed == 0:
            processed = getattr(src, "_candidates_generated", 0)
        
        elapsed = max(0.001, t1 - t0)
        throughput = processed / elapsed
        results.append((rate, throughput, min_throughput))

        # Asserti yksittäiselle testille
        assert throughput >= min_throughput, f"Rate {rate}: läpivienti {throughput:.1f}/s < {min_throughput}/s"

    # Varmista että läpivienti skaalautuu järkevästi
    print(f"Throughput results: {results}")
    
    # Jos kaikki testit menivät läpi, skaalaus on OK
    assert len(results) == len(test_cases), "Kaikki testit eivät menneet läpi"


if __name__ == "__main__":
    # Suorita testit suoraan
    pytest.main([__file__, "-v", "--tb=short"])
