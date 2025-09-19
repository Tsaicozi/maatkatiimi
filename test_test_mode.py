#!/usr/bin/env python3
"""
Testaa AutomaticHybridBot testimoodia
"""

import asyncio
import time
from automatic_hybrid_bot import AutomaticHybridBot

async def test_test_mode():
    """Testaa että testimoodi toimii oikein"""
    print("🧪 Testataan AutomaticHybridBot testimoodia...")
    
    # Testi 1: max_cycles
    print("\n1️⃣ Testi: max_cycles=2")
    bot1 = AutomaticHybridBot(max_cycles=2, max_runtime_sec=None)
    assert bot1._max_cycles == 2
    assert bot1._deadline is None
    print("✅ max_cycles parametri toimii")
    
    # Testi 2: max_runtime_sec
    print("\n2️⃣ Testi: max_runtime_sec=5.0")
    bot2 = AutomaticHybridBot(max_cycles=None, max_runtime_sec=5.0)
    assert bot2._max_cycles is None
    assert bot2._deadline is not None
    print("✅ max_runtime_sec parametri toimii")
    
    # Testi 3: molemmat
    print("\n3️⃣ Testi: molemmat parametrit")
    bot3 = AutomaticHybridBot(max_cycles=1, max_runtime_sec=10.0)
    assert bot3._max_cycles == 1
    assert bot3._deadline is not None
    print("✅ Molemmat parametrit toimivat")
    
    # Testi 4: ei parametreja (normaali käyttö)
    print("\n4️⃣ Testi: ei parametreja")
    bot4 = AutomaticHybridBot()
    assert bot4._max_cycles is None
    assert bot4._deadline is None
    print("✅ Normaali käyttö toimii")
    
    print("\n🎉 Kaikki testimoodi testit läpäisty!")

if __name__ == "__main__":
    asyncio.run(test_test_mode())


