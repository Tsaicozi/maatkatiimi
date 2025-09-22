#!/usr/bin/env python3
"""
Setup script for Birdeye API Key Management
Helppo tapa konfiguroida ja testata Birdeye-avaintenhallinta
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from getpass import getpass
from typing import List, Optional

# Lisää projektikansio polkuun
sys.path.insert(0, str(Path(__file__).parent))

from birdeye_key_manager import BirdeyeKeyManager, BirdeyeKeyBot
from birdeye_integration import birdeye

# Värikoodit terminaaliin
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Tulosta otsikko"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Tulosta onnistumisviesti"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Tulosta virheviesti"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Tulosta varoitus"""
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")


def print_info(text: str):
    """Tulosta info"""
    print(f"{Colors.CYAN}ℹ️ {text}{Colors.ENDC}")


async def check_existing_setup():
    """Tarkista onko avaintenhallinta jo konfiguroitu"""
    manager = BirdeyeKeyManager()
    
    # Tarkista onko avaintiedosto olemassa
    if Path("birdeye_keys.json").exists():
        print_info("Löytyi olemassa oleva konfiguraatio")
        
        # Lataa ja näytä status
        if await manager.load_keys():
            status = await manager.get_status()
            print(f"\n📊 Nykyinen tilanne:")
            print(f"  - Avaimia: {status['total_keys']}")
            print(f"  - Aktiivisia: {status['active_keys']}")
            return manager
    
    # Tarkista ympäristömuuttujat
    env_keys = []
    if os.getenv("BIRDEYE_API_KEY"):
        env_keys.append("BIRDEYE_API_KEY")
    
    for i in range(1, 11):
        if os.getenv(f"BIRDEYE_API_KEY_{i}"):
            env_keys.append(f"BIRDEYE_API_KEY_{i}")
    
    if env_keys:
        print_info(f"Löytyi {len(env_keys)} avainta ympäristömuuttujista")
        if await manager.load_keys():
            return manager
    
    # Tarkista config.yaml
    if Path("config.yaml").exists():
        import yaml
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
            key = config.get("sources", {}).get("birdeye", {}).get("api_key")
            if key and key != "null":
                print_warning("Löytyi avain config.yaml:sta (ei suositeltu!)")
                await manager.add_key(key, "config_yaml")
                return manager
    
    return None


async def setup_new_keys():
    """Aseta uudet API-avaimet"""
    print_header("Birdeye API Key Setup")
    
    manager = BirdeyeKeyManager()
    keys_added = 0
    
    print("Lisää Birdeye API-avaimia (tyhjä lopettaa):")
    print("Voit hankkia avaimia osoitteesta: https://birdeye.so/\n")
    
    while True:
        key_num = keys_added + 1
        key = getpass(f"API-avain {key_num} (enter = lopeta): ").strip()
        
        if not key:
            break
        
        name = input(f"Nimi avaimelle (enter = key_{key_num}): ").strip()
        if not name:
            name = f"key_{key_num}"
        
        print("Testataan avainta...")
        if await manager.add_key(key, name):
            print_success(f"Avain '{name}' lisätty ja toimii!")
            keys_added += 1
        else:
            print_error("Avain ei toimi tai on jo listassa")
    
    if keys_added > 0:
        await manager.save_keys()
        print_success(f"Lisätty {keys_added} avainta")
        return manager
    else:
        print_warning("Ei lisätty yhtään avainta")
        return None


async def create_env_file():
    """Luo .env-tiedostomalli"""
    print_header("Luo .env-tiedosto")
    
    env_path = Path(".env")
    
    if env_path.exists():
        print_warning(".env-tiedosto on jo olemassa")
        overwrite = input("Haluatko korvata sen? (y/n): ").lower()
        if overwrite != 'y':
            return
    
    print("\nLisää API-avaimia .env-tiedostoon:")
    keys = []
    
    while True:
        key = getpass(f"API-avain {len(keys) + 1} (enter = lopeta): ").strip()
        if not key:
            break
        keys.append(key)
    
    if not keys:
        print_warning("Ei avaimia lisättäväksi")
        return
    
    # Luo .env sisältö
    content = ["# Birdeye API Keys"]
    
    if len(keys) == 1:
        content.append(f"BIRDEYE_API_KEY={keys[0]}")
    else:
        for i, key in enumerate(keys, 1):
            content.append(f"BIRDEYE_API_KEY_{i}={key}")
    
    # Lisää salasana avainten salaukseen
    password = getpass("\nSalasana avainten salaukseen (enter = oletus): ").strip()
    if password:
        content.append(f"\n# Salausavain")
        content.append(f"BIRDEYE_KEY_PASSWORD={password}")
    
    # Kirjoita tiedosto
    with open(env_path, "w") as f:
        f.write("\n".join(content))
    
    print_success(f".env-tiedosto luotu {len(keys)} avaimella")
    
    # Lataa .env
    from dotenv import load_dotenv
    load_dotenv()


async def test_integration():
    """Testaa integraatio"""
    print_header("Testaa Birdeye-integraatio")
    
    if not await birdeye.initialize():
        print_error("Integraation alustus epäonnistui")
        return
    
    status = await birdeye.key_manager.get_status()
    print(f"\n📊 Status:")
    print(f"  - Avaimia: {status['total_keys']}")
    print(f"  - Aktiivisia: {status['active_keys']}")
    
    # Testaa API-kutsu
    print("\n🧪 Testataan API-kutsua...")
    
    # USDC mint
    test_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    token_info = await birdeye.get_token_info(test_mint)
    if token_info:
        data = token_info.get("data", {})
        print_success(f"Token: {data.get('symbol', 'Unknown')} - {data.get('name', 'Unknown')}")
    else:
        print_error("API-kutsu epäonnistui")
        return
    
    # Testaa uudet tokenit
    print("\n🆕 Haetaan uusia tokeneita...")
    new_tokens = await birdeye.get_new_tokens(limit=3)
    
    if new_tokens:
        print_success(f"Löytyi {len(new_tokens)} uutta tokenia:")
        for token in new_tokens:
            print(f"  - {token.get('symbol', '???')}: {token.get('name', 'Unknown')}")
    else:
        print_warning("Ei uusia tokeneita tai haku epäonnistui")


async def run_key_bot():
    """Käynnistä avaintenhallintabotti"""
    print_header("Käynnistä Birdeye Key Bot")
    
    bot = BirdeyeKeyBot()
    
    print_info("Botti valvoo ja hallitsee API-avaimia automaattisesti")
    print_info("Pysäytä painamalla Ctrl+C\n")
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n\nPysäytetään...")
        await bot.stop()
        print_success("Botti pysäytetty")


async def update_config_yaml():
    """Päivitä config.yaml poistamaan kovakoodattu avain"""
    print_header("Päivitä config.yaml")
    
    config_path = Path("config.yaml")
    if not config_path.exists():
        print_warning("config.yaml ei löydy")
        return
    
    import yaml
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Tarkista onko kovakoodattu avain
    old_key = config.get("sources", {}).get("birdeye", {}).get("api_key")
    
    if old_key and old_key != "null":
        print_warning(f"Löytyi kovakoodattu avain: {old_key[:8]}...")
        
        # Poista avain
        config["sources"]["birdeye"]["api_key"] = None
        config["sources"]["birdeye"]["use_key_manager"] = True
        
        # Varmuuskopio
        import shutil
        shutil.copy(config_path, f"{config_path}.backup")
        print_info(f"Varmuuskopio: {config_path}.backup")
        
        # Tallenna päivitetty config
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print_success("config.yaml päivitetty käyttämään avaintenhallintaa")
        
        # Lisää vanha avain manageriin
        manager = BirdeyeKeyManager()
        if await manager.add_key(old_key, "migrated_from_config"):
            print_success("Vanha avain siirretty turvalliseen tallennukseen")
    else:
        print_info("config.yaml on jo kunnossa")


async def main_menu():
    """Päävalikko"""
    print_header("🐦 Birdeye API Key Manager 🔑")
    
    # Tarkista nykyinen tilanne
    manager = await check_existing_setup()
    
    while True:
        print(f"\n{Colors.BOLD}Valikko:{Colors.ENDC}")
        print("1. Aseta uudet API-avaimet")
        print("2. Luo .env-tiedosto")
        print("3. Testaa integraatio")
        print("4. Näytä avainten status")
        print("5. Päivitä config.yaml")
        print("6. Käynnistä Key Bot (valvonta)")
        print("0. Lopeta")
        
        choice = input(f"\n{Colors.CYAN}Valinta: {Colors.ENDC}").strip()
        
        if choice == "1":
            manager = await setup_new_keys()
            
        elif choice == "2":
            await create_env_file()
            
        elif choice == "3":
            await test_integration()
            
        elif choice == "4":
            if not manager:
                manager = BirdeyeKeyManager()
                if not await manager.load_keys():
                    print_error("Ei avaimia ladattavissa")
                    continue
            
            status = await manager.get_status()
            print(f"\n📊 {Colors.BOLD}API Key Status:{Colors.ENDC}")
            print(f"  Avaimia yhteensä: {status['total_keys']}")
            print(f"  Aktiivisia: {status['active_keys']}")
            print(f"  Nykyinen: {status['current_key']}")
            
            print(f"\n  {Colors.BOLD}Tilastot:{Colors.ENDC}")
            for key, value in status['stats'].items():
                print(f"    {key}: {value}")
            
            print(f"\n  {Colors.BOLD}Avaimet:{Colors.ENDC}")
            for key in status['keys']:
                status_icon = "✅" if key['is_active'] else "❌"
                print(f"    {status_icon} {key['name']}")
                print(f"       Pyyntöjä: {key['request_count']}")
                print(f"       Virheitä: {key['error_count']}")
                
        elif choice == "5":
            await update_config_yaml()
            
        elif choice == "6":
            await run_key_bot()
            
        elif choice == "0":
            print_success("Hei hei! 👋")
            break
            
        else:
            print_warning("Virheellinen valinta")


if __name__ == "__main__":
    # Aseta lokitus
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Piilota salasanat lokista
    logging.getLogger("birdeye_key_manager").setLevel(logging.WARNING)
    
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n\n👋 Keskeytetty")
    except Exception as e:
        print_error(f"Odottamaton virhe: {e}")
        import traceback
        traceback.print_exc()