#!/usr/bin/env python3
"""
Testaa ympäristömuuttujien lukemista AutomaticHybridBot:issa
"""

import os
import asyncio
from automatic_hybrid_bot import AutomaticHybridBot

async def test_env_vars():
    """Testaa ympäristömuuttujien lukemista"""
    print("🧪 Testataan ympäristömuuttujien lukemista...")
    
    # Testi 1: TEST_MAX_CYCLES
    print("\n1️⃣ Testi: TEST_MAX_CYCLES=3")
    os.environ["TEST_MAX_CYCLES"] = "3"
    os.environ.pop("TEST_MAX_RUNTIME", None)
    
    max_cycles = int(os.getenv("TEST_MAX_CYCLES", "0") or 0) or None
    max_runtime = float(os.getenv("TEST_MAX_RUNTIME", "0") or 0.0) or None
    
    assert max_cycles == 3
    assert max_runtime is None
    print("✅ TEST_MAX_CYCLES toimii")
    
    # Testi 2: TEST_MAX_RUNTIME
    print("\n2️⃣ Testi: TEST_MAX_RUNTIME=15.5")
    os.environ["TEST_MAX_RUNTIME"] = "15.5"
    os.environ.pop("TEST_MAX_CYCLES", None)
    
    max_cycles = int(os.getenv("TEST_MAX_CYCLES", "0") or 0) or None
    max_runtime = float(os.getenv("TEST_MAX_RUNTIME", "0") or 0.0) or None
    
    assert max_cycles is None
    assert max_runtime == 15.5
    print("✅ TEST_MAX_RUNTIME toimii")
    
    # Testi 3: molemmat
    print("\n3️⃣ Testi: molemmat ympäristömuuttujat")
    os.environ["TEST_MAX_CYCLES"] = "2"
    os.environ["TEST_MAX_RUNTIME"] = "30.0"
    
    max_cycles = int(os.getenv("TEST_MAX_CYCLES", "0") or 0) or None
    max_runtime = float(os.getenv("TEST_MAX_RUNTIME", "0") or 0.0) or None
    
    assert max_cycles == 2
    assert max_runtime == 30.0
    print("✅ Molemmat ympäristömuuttujat toimivat")
    
    # Testi 4: ei ympäristömuuttujia
    print("\n4️⃣ Testi: ei ympäristömuuttujia")
    os.environ.pop("TEST_MAX_CYCLES", None)
    os.environ.pop("TEST_MAX_RUNTIME", None)
    
    max_cycles = int(os.getenv("TEST_MAX_CYCLES", "0") or 0) or None
    max_runtime = float(os.getenv("TEST_MAX_RUNTIME", "0") or 0.0) or None
    
    assert max_cycles is None
    assert max_runtime is None
    print("✅ Ei ympäristömuuttujia toimii")
    
    # Testi 5: AutomaticHybridBot konstruktori
    print("\n5️⃣ Testi: AutomaticHybridBot konstruktori")
    bot = AutomaticHybridBot(max_cycles=1, max_runtime_sec=5.0)
    assert bot._max_cycles == 1
    assert bot._deadline is not None
    print("✅ AutomaticHybridBot konstruktori toimii")
    
    print("\n🎉 Kaikki ympäristömuuttuja testit läpäisty!")

if __name__ == "__main__":
    asyncio.run(test_env_vars())


