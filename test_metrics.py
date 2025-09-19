#!/usr/bin/env python3
"""
Testaa metrics toimivuutta
"""

import time
import asyncio
from metrics import init_metrics, metrics

async def test_metrics():
    """Testaa metrics toimivuutta"""
    print("🧪 Testataan metrics:ia...")
    
    # Alusta metrics
    actual_port = init_metrics(namespace="test_bot", host="127.0.0.1", port=9109, enabled=True)
    print(f"Metrics käynnistetty portissa: {actual_port}")
    
    # Hae metrics uudelleen
    from metrics import metrics as global_metrics
    
    if global_metrics:
        # Testaa metrics kutsut
        global_metrics.candidates_seen.inc()
        global_metrics.candidates_filtered.inc()
        global_metrics.candidates_scored.inc()
        global_metrics.telegram_sent.inc()
        global_metrics.rpc_errors.inc()
        global_metrics.source_errors.inc()
        global_metrics.loop_restarts.inc()
        
        global_metrics.queue_depth.set(5)
        global_metrics.engine_running.set(1)
        global_metrics.hot_candidates_gauge.set(3)
        
        global_metrics.score_hist.observe(0.75)
        global_metrics.rpc_latency.observe(0.1)
        global_metrics.cycle_duration.observe(2.5)
        
        print("✅ Metrics kutsut suoritettu")
    else:
        print("❌ Metrics ei alustettu")
    
    # Odota hetki että metrics server ehtii käynnistyä
    await asyncio.sleep(1)
    
    print("🎉 Metrics testi valmis!")

if __name__ == "__main__":
    asyncio.run(test_metrics())
