#!/usr/bin/env python3
"""
Luo .env-tiedosto Birdeye-avaimella
"""

import os
from pathlib import Path
from getpass import getpass

def create_env_file():
    """Luo .env-tiedosto interaktiivisesti"""
    
    print("=" * 60)
    print("🔧 LUO .ENV-TIEDOSTO")
    print("=" * 60)
    
    env_path = Path(".env")
    
    # Tarkista onko jo olemassa
    if env_path.exists():
        print("\n⚠️ .env-tiedosto on jo olemassa!")
        
        # Lue nykyinen sisältö
        with open(env_path, "r") as f:
            content = f.read()
            
        if "BIRDEYE_API_KEY" in content:
            print("✅ BIRDEYE_API_KEY löytyy jo .env-tiedostosta")
            print("\nNykyiset Birdeye-avaimet:")
            for line in content.split("\n"):
                if "BIRDEYE" in line and not line.startswith("#"):
                    key_name = line.split("=")[0]
                    print(f"  - {key_name}")
            
            update = input("\nHaluatko päivittää avaimet? (y/n): ").lower()
            if update != 'y':
                print("✅ Käytetään nykyisiä avaimia")
                return
        
        backup = input("\nHaluatko tehdä varmuuskopion? (y/n): ").lower()
        if backup == 'y':
            import shutil
            shutil.copy(env_path, f"{env_path}.backup")
            print(f"✅ Varmuuskopio: {env_path}.backup")
    
    # Kerää tiedot
    print("\n📝 Anna Birdeye API-avain:")
    print("(Voit hankkia sen osoitteesta: https://birdeye.so/)")
    
    birdeye_key = getpass("BIRDEYE_API_KEY: ").strip()
    
    if not birdeye_key:
        print("❌ Avain ei voi olla tyhjä!")
        return
    
    # Kysy haluaako lisätä useampia avaimia
    additional_keys = []
    print("\nHaluatko lisätä useampia avaimia? (parempi rate limit -hallinta)")
    
    for i in range(1, 6):  # Max 5 lisäavainta
        key = getpass(f"BIRDEYE_API_KEY_{i} (enter = ohita): ").strip()
        if key:
            additional_keys.append((f"BIRDEYE_API_KEY_{i}", key))
        else:
            break
    
    # Luo .env sisältö
    lines = []
    
    # Jos on olemassa oleva tiedosto, säilytä muut rivit
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                # Ohita vanhat Birdeye-avaimet
                if "BIRDEYE_API_KEY" not in line:
                    lines.append(line.rstrip())
    
    # Lisää Birdeye-osio
    if lines and lines[-1]:  # Lisää tyhjä rivi jos tarvetta
        lines.append("")
    
    lines.append("# Birdeye API Configuration")
    lines.append(f"BIRDEYE_API_KEY={birdeye_key}")
    
    for key_name, key_value in additional_keys:
        lines.append(f"{key_name}={key_value}")
    
    # Salausavain
    print("\nHaluatko asettaa salausavaimen avainten salaukseen?")
    print("(Suositeltavaa turvallisuuden vuoksi)")
    
    use_encryption = input("Käytä salausta? (y/n): ").lower()
    if use_encryption == 'y':
        password = getpass("Salausavain (enter = oletus): ").strip()
        if password:
            lines.append("")
            lines.append("# Encryption password for key storage")
            lines.append(f"BIRDEYE_KEY_PASSWORD={password}")
    
    # Kirjoita tiedosto
    with open(env_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"\n✅ .env-tiedosto luotu/päivitetty!")
    print(f"   Avaimia yhteensä: {1 + len(additional_keys)}")
    
    # Testaa heti
    print("\n🧪 Testataan avain...")
    os.system("python3 test_birdeye_key.py")


if __name__ == "__main__":
    create_env_file()