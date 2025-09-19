#!/usr/bin/env python3
"""
Erillinen ajoskripti kuormitustestille.
Kehittäjä voi pyörittää ilman pytest:ia nopeaan testaamiseen ja debuggaamiseen.

Käyttö:
    python3 scripts/run_load_test.py
    python3 scripts/run_load_test.py --rate 2000 --duration 15
    python3 scripts/run_load_test.py --help
"""
from __future__ import annotations
import asyncio
import time
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Lisää projekti Python path:iin
sys.path.insert(0, str(Path(__file__).parent.parent))

from discovery_engine import DiscoveryEngine
from sources.mock_firehose import MockFirehoseSource
from tests.stubs_rpc import StubFastRPC


async def run_load_test(
    rate: int = 1000,
    duration: float = 10.0,
    burst: int = 25,
    jitter_ms: int = 2,
    min_liq_usd: float = 3000.0,
    max_queue: int = 10000,
    output_file: str = None
) -> Dict[str, Any]:
    """
    Suorita kuormitustesti DiscoveryEngine:lle.
    
    Args:
        rate: Ehdokkaiden määrä per sekunti
        duration: Testin kesto sekunneissa
        burst: Burst-koko (ehdokkaita per tikki)
        jitter_ms: Aikajitteri millisekunteina
        min_liq_usd: Minimilikviditeetti USD
        max_queue: Maksimijonon koko
        output_file: JSON-tiedosto tulosten tallentamiseen
    
    Returns:
        Testitulokset sanakirjana
    """
    print(f"🚀 Aloitetaan kuormitustesti...")
    print(f"   Rate: {rate} ehdokasta/s")
    print(f"   Duration: {duration}s")
    print(f"   Burst: {burst}")
    print(f"   Min liquidity: ${min_liq_usd:,.0f}")
    print(f"   Max queue: {max_queue:,}")
    print()

    # Luo komponentit
    rpc = StubFastRPC()
    src = MockFirehoseSource(rate_per_sec=rate, burst=burst, jitter_ms=jitter_ms)
    eng = DiscoveryEngine(
        rpc_endpoint='http://localhost:8899',
        market_sources=[src], 
        min_liq_usd=min_liq_usd,
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

    # Säädä jonon maksimia
    try:
        eng.candidate_queue._maxsize = max_queue
    except Exception:
        pass

    # Aloita testi
    print("⏱️  Käynnistetään DiscoveryEngine...")
    await eng.start()
    
    print("🔥 Kuormitustesti käynnissä...")
    t0 = time.perf_counter()
    await asyncio.sleep(duration)
    t1 = time.perf_counter()
    
    print("🛑 Sammutetaan...")
    await eng.stop()
    await eng.wait_closed()

    # Laske tulokset
    elapsed = max(0.001, t1 - t0)
    processed = len(getattr(eng, "_recent_scores", []))
    if processed == 0:
        processed = getattr(src, "_candidates_generated", 0)
    
    throughput = processed / elapsed
    final_queue_size = eng.candidate_queue.qsize()
    
    # Tulokset
    results = {
        "test_config": {
            "rate_per_sec": rate,
            "duration_sec": duration,
            "burst": burst,
            "jitter_ms": jitter_ms,
            "min_liq_usd": min_liq_usd,
            "max_queue": max_queue
        },
        "results": {
            "processed_items": processed,
            "elapsed_sec": elapsed,
            "throughput_per_sec": throughput,
            "final_queue_size": final_queue_size,
            "queue_utilization": (final_queue_size / max_queue) * 100 if max_queue > 0 else 0
        },
        "performance": {
            "items_per_second": throughput,
            "queue_stable": final_queue_size < max_queue * 0.8,  # < 80% täynnä
            "throughput_acceptable": throughput >= rate * 0.5,  # > 50% tavoitteesta
        },
        "timestamp": time.time(),
        "status": "completed"
    }

    # Tulosta tulokset
    print()
    print("📊 KUORMITUSTESTIN TULOKSET:")
    print("=" * 50)
    print(f"✅ Käsitelty: {processed:,} ehdokasta")
    print(f"⏱️  Kesto: {elapsed:.2f}s")
    print(f"🚀 Läpivienti: {throughput:.1f} ehdokasta/s")
    print(f"📦 Jonon koko lopussa: {final_queue_size:,}")
    print(f"📈 Jonon käyttöaste: {results['results']['queue_utilization']:.1f}%")
    print()
    
    # Suorituskyky-arvio
    print("🎯 SUORITUSKYKY-ARVIO:")
    print("-" * 30)
    if results['performance']['queue_stable']:
        print("✅ Jono stabiili (< 80% täynnä)")
    else:
        print("⚠️  Jono korkea (≥ 80% täynnä)")
    
    if results['performance']['throughput_acceptable']:
        print("✅ Läpivienti hyvä (≥ 50% tavoitteesta)")
    else:
        print("⚠️  Läpivienti heikko (< 50% tavoitteesta)")
    
    if throughput >= rate * 0.8:
        print("🚀 Erinomainen suorituskyky!")
    elif throughput >= rate * 0.5:
        print("👍 Hyvä suorituskyky")
    else:
        print("🐌 Suorituskyky voi parantua")

    # Tallenna tulokset tiedostoon
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Tulokset tallennettu: {output_file}")

    return results


async def run_multiple_tests():
    """Suorita useita testejä eri parametreilla."""
    test_cases = [
        {"rate": 500, "duration": 5.0, "name": "Kevyt kuorma"},
        {"rate": 1000, "duration": 5.0, "name": "Keskisuuri kuorma"},
        {"rate": 2000, "duration": 5.0, "name": "Korkea kuorma"},
        {"rate": 5000, "duration": 3.0, "name": "Erittäin korkea kuorma"},
    ]
    
    print("🧪 Suoritetaan useita kuormitustestejä...")
    print("=" * 60)
    
    all_results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 Testi {i}/{len(test_cases)}: {test_case['name']}")
        print("-" * 40)
        
        try:
            results = await run_load_test(
                rate=test_case['rate'],
                duration=test_case['duration'],
                burst=25,
                min_liq_usd=2000.0
            )
            all_results.append({
                "test_name": test_case['name'],
                **results
            })
        except Exception as e:
            print(f"❌ Testi epäonnistui: {e}")
            all_results.append({
                "test_name": test_case['name'],
                "status": "failed",
                "error": str(e)
            })
    
    # Yhteenveto
    print("\n📋 YHTEENVETO:")
    print("=" * 60)
    for result in all_results:
        if result.get('status') == 'completed':
            throughput = result['results']['throughput_per_sec']
            rate = result['test_config']['rate_per_sec']
            efficiency = (throughput / rate) * 100
            print(f"✅ {result['test_name']}: {throughput:.1f}/s ({efficiency:.1f}% tehokkuus)")
        else:
            print(f"❌ {result['test_name']}: Epäonnistui")
    
    return all_results


def main():
    """Pääfunktio komentorivikäyttöliittymälle."""
    parser = argparse.ArgumentParser(
        description="Kuormitustesti DiscoveryEngine:lle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esimerkkejä:
  python3 scripts/run_load_test.py
  python3 scripts/run_load_test.py --rate 2000 --duration 15
  python3 scripts/run_load_test.py --multi
  python3 scripts/run_load_test.py --output results.json
        """
    )
    
    parser.add_argument('--rate', type=int, default=1000,
                       help='Ehdokkaiden määrä per sekunti (default: 1000)')
    parser.add_argument('--duration', type=float, default=10.0,
                       help='Testin kesto sekunneissa (default: 10.0)')
    parser.add_argument('--burst', type=int, default=25,
                       help='Burst-koko (default: 25)')
    parser.add_argument('--jitter', type=int, default=2,
                       help='Aikajitteri millisekunteina (default: 2)')
    parser.add_argument('--min-liq', type=float, default=3000.0,
                       help='Minimilikviditeetti USD (default: 3000.0)')
    parser.add_argument('--max-queue', type=int, default=10000,
                       help='Maksimijonon koko (default: 10000)')
    parser.add_argument('--output', type=str,
                       help='JSON-tiedosto tulosten tallentamiseen')
    parser.add_argument('--multi', action='store_true',
                       help='Suorita useita testejä eri parametreilla')
    
    args = parser.parse_args()
    
    try:
        if args.multi:
            results = asyncio.run(run_multiple_tests())
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n💾 Kaikki tulokset tallennettu: {args.output}")
        else:
            asyncio.run(run_load_test(
                rate=args.rate,
                duration=args.duration,
                burst=args.burst,
                jitter_ms=args.jitter,
                min_liq_usd=args.min_liq,
                max_queue=args.max_queue,
                output_file=args.output
            ))
    except KeyboardInterrupt:
        print("\n⏹️  Testi keskeytetty käyttäjän toimesta")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Virhe: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
