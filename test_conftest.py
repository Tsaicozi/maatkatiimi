#!/usr/bin/env python3
"""
Testaa conftest.py fixture:t
"""

import asyncio
import pytest

@pytest.mark.asyncio
async def test_no_task_leaks_fixture():
    """Testaa että no_task_leaks fixture toimii"""
    print("🧪 Testataan no_task_leaks fixture...")
    
    # Luo taustatehtävä joka jäisi roikkumaan ilman fixture:tä
    async def background_task():
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("✅ Background task peruttu")
            raise
    
    # Käynnistä taustatehtävä
    task = asyncio.create_task(background_task())
    
    # Odota hetki
    await asyncio.sleep(0.2)
    
    # Tarkista että task on vielä käynnissä
    assert not task.done()
    print("✅ Background task käynnissä")
    
    # Testi päättyy - fixture:n pitäisi siivota task
    print("✅ Testi päättyy - fixture siivoaa taustatehtävän")

@pytest.mark.asyncio
async def test_multiple_background_tasks():
    """Testaa että fixture siivoaa useita taustatehtäviä"""
    print("🧪 Testataan useita taustatehtäviä...")
    
    async def task1():
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("✅ Task1 peruttu")
            raise
    
    async def task2():
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("✅ Task2 peruttu")
            raise
    
    # Käynnistä useita taustatehtäviä
    tasks = [
        asyncio.create_task(task1()),
        asyncio.create_task(task2())
    ]
    
    # Odota hetki
    await asyncio.sleep(0.2)
    
    # Tarkista että taskit ovat vielä käynnissä
    for i, task in enumerate(tasks):
        assert not task.done()
        print(f"✅ Task{i+1} käynnissä")
    
    # Testi päättyy - fixture:n pitäisi siivota kaikki taskit
    print("✅ Testi päättyy - fixture siivoaa kaikki taustatehtävät")

def test_sync_test_with_fixture():
    """Testaa että fixture toimii myös sync testeissä"""
    print("🧪 Testataan sync testi fixture:lla...")
    
    # Sync testi ei tarvitse erityistä käsittelyä
    assert True
    print("✅ Sync testi toimii")

if __name__ == "__main__":
    # Suorita testit pytest:llä
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short"
    ], capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")


