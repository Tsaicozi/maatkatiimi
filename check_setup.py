#!/usr/bin/env python3
"""
Solana Auto Trader - Setup Checker
Tarkistaa että kaikki riippuvuudet ja konfiguraatiot ovat kunnossa ennen käynnistystä.
"""

import os
import sys
from pathlib import Path

# Värikoodit
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark():
    return f"{GREEN}✓{RESET}"

def x_mark():
    return f"{RED}✗{RESET}"

def warning_mark():
    return f"{YELLOW}⚠{RESET}"

def print_header(text):
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*50}{RESET}\n")

def check_python_version():
    """Tarkista Python-versio"""
    print("Tarkistetaan Python-versio...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"{check_mark()} Python {version.major}.{version.minor}.{version.micro} OK")
        return True
    else:
        print(f"{x_mark()} Python {version.major}.{version.minor}.{version.micro} - Tarvitaan Python 3.10+")
        return False

def check_dependencies():
    """Tarkista että tarvittavat kirjastot on asennettu"""
    print("\nTarkistetaan riippuvuudet...")
    required = [
        'solana',
        'solders',
        'requests',
        'base58',
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"{check_mark()} {package}")
        except ImportError:
            print(f"{x_mark()} {package} - PUUTTUU")
            missing.append(package)
    
    if missing:
        print(f"\n{RED}Asenna puuttuvat paketit:{RESET}")
        print(f"pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Tarkista että .env2 on olemassa ja sisältää tarvittavat kentät"""
    print("\nTarkistetaan .env2-tiedosto...")
    
    if not os.path.exists('.env2'):
        print(f"{x_mark()} .env2-tiedostoa ei löydy")
        print(f"\n{YELLOW}Kopioi .env2.example → .env2 ja täytä arvot:{RESET}")
        print(f"cp .env2.example .env2")
        print(f"nano .env2")
        return False
    
    print(f"{check_mark()} .env2 löytyy")
    
    # Tarkista pakolliset kentät
    required_fields = [
        'SOLANA_RPC_URL',
        'PHANTOM_PRIVATE_KEY',
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID',
        'POSITION_SIZE_SOL',
        'MAX_POSITIONS',
        'STOP_LOSS_PCT',
        'TAKE_PROFIT_PCT',
    ]
    
    missing_fields = []
    placeholder_fields = []
    
    with open('.env2', 'r') as f:
        content = f.read()
    
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)
        elif f"{field}=" in content:
            # Tarkista onko placeholder-arvo
            for line in content.split('\n'):
                if line.startswith(f"{field}="):
                    value = line.split('=', 1)[1].strip()
                    if not value or 'your_' in value.lower() or 'here' in value.lower():
                        placeholder_fields.append(field)
    
    if missing_fields:
        print(f"{x_mark()} Puuttuvia kenttiä: {', '.join(missing_fields)}")
        return False
    
    if placeholder_fields:
        print(f"{warning_mark()} Täytä seuraavat kentät .env2:ssa:")
        for field in placeholder_fields:
            print(f"   - {field}")
        return False
    
    print(f"{check_mark()} Kaikki pakolliset kentät täytetty")
    return True

def check_wallet():
    """Tarkista että wallet private key on kelvollinen"""
    print("\nTarkistetaan Phantom wallet...")
    
    try:
        from solana.rpc.api import Client
        from solders.keypair import Keypair
        import base58
        
        # Lataa .env2
        env_vars = {}
        with open('.env2', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
        
        private_key = env_vars.get('PHANTOM_PRIVATE_KEY', '')
        
        if not private_key or 'your_' in private_key.lower():
            print(f"{x_mark()} PHANTOM_PRIVATE_KEY ei ole asetettu")
            print(f"\n{YELLOW}Luo uusi lompakko:{RESET}")
            print(f"python create_solana_wallet.py")
            return False
        
        # Yritä luoda keypair
        try:
            keypair = Keypair.from_base58_string(private_key)
            print(f"{check_mark()} Private key on kelvollinen")
            print(f"   Wallet address: {keypair.pubkey()}")
            
            # Tarkista saldo
            rpc_url = env_vars.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
            client = Client(rpc_url)
            
            try:
                balance_resp = client.get_balance(keypair.pubkey())
                balance_lamports = balance_resp.value if hasattr(balance_resp, 'value') else 0
                balance_sol = balance_lamports / 1e9
                
                if balance_sol < 0.05:
                    print(f"{warning_mark()} Saldo: {balance_sol:.4f} SOL - Liian vähän!")
                    print(f"   Lähetä vähintään 0.1 SOL osoitteeseen: {keypair.pubkey()}")
                    return True  # Config OK, mutta varoitus
                else:
                    print(f"{check_mark()} Saldo: {balance_sol:.4f} SOL")
            except Exception as e:
                print(f"{warning_mark()} Ei voitu tarkistaa saldoa: {e}")
            
            return True
            
        except Exception as e:
            print(f"{x_mark()} Private key ei ole kelvollinen: {e}")
            return False
    
    except ImportError as e:
        print(f"{warning_mark()} Ei voitu tarkistaa walletia (puuttuva kirjasto): {e}")
        return True  # Älä estä setuppia tämän takia

def check_telegram():
    """Tarkista Telegram-konfiguraatio"""
    print("\nTarkistetaan Telegram...")
    
    try:
        import requests
        
        # Lataa .env2
        env_vars = {}
        with open('.env2', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
        
        token = env_vars.get('TELEGRAM_TOKEN', '')
        chat_id = env_vars.get('TELEGRAM_CHAT_ID', '')
        
        if not token or 'your_' in token.lower():
            print(f"{x_mark()} TELEGRAM_TOKEN ei ole asetettu")
            print(f"\n{YELLOW}Luo botti: https://t.me/BotFather{RESET}")
            return False
        
        if not chat_id or chat_id == '123456789':
            print(f"{x_mark()} TELEGRAM_CHAT_ID ei ole asetettu")
            print(f"\n{YELLOW}Hae chat ID:{RESET}")
            print(f"1. Lähetä viesti botille Telegramissa")
            print(f"2. Avaa: https://api.telegram.org/bot{token}/getUpdates")
            print(f"3. Etsi 'chat':{'id'}")
            return False
        
        # Testaa lähetys
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': '✅ Solana Auto Trader - Setup tarkistus OK!'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"{check_mark()} Telegram-yhteys OK")
            print(f"   Testviesti lähetetty!")
            return True
        else:
            print(f"{x_mark()} Telegram-yhteys epäonnistui: {response.text}")
            return False
    
    except Exception as e:
        print(f"{warning_mark()} Ei voitu testata Telegram-yhteyttä: {e}")
        return True  # Älä estä setuppia

def check_files():
    """Tarkista että tarvittavat tiedostot on olemassa"""
    print("\nTarkistetaan tiedostot...")
    
    required_files = [
        'solana_token_scanner.py',
        'solana_trader.py',
        'solana_auto_trader.py',
        'requirements.txt',
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"{check_mark()} {file}")
        else:
            print(f"{x_mark()} {file} - PUUTTUU")
            missing.append(file)
    
    if missing:
        print(f"\n{RED}Kloonaa repository uudelleen tai päivitä:{RESET}")
        print(f"git pull origin main")
        return False
    
    return True

def main():
    print_header("🚀 Solana Auto Trader - Setup Checker")
    
    checks = [
        ("Python-versio", check_python_version),
        ("Riippuvuudet", check_dependencies),
        ("Tiedostot", check_files),
        ("Konfiguraatio (.env2)", check_env_file),
        ("Wallet", check_wallet),
        ("Telegram", check_telegram),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"{x_mark()} Virhe tarkistuksessa '{name}': {e}")
            results.append((name, False))
    
    # Yhteenveto
    print_header("📊 Yhteenveto")
    
    all_passed = True
    for name, passed in results:
        status = check_mark() if passed else x_mark()
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print(f"{GREEN}{'='*50}{RESET}")
        print(f"{GREEN}✅ Kaikki tarkistukset läpäisty!{RESET}")
        print(f"{GREEN}{'='*50}{RESET}\n")
        print(f"{BLUE}Voit nyt käynnistää botin:{RESET}")
        print(f"python solana_auto_trader.py\n")
        return 0
    else:
        print(f"{RED}{'='*50}{RESET}")
        print(f"{RED}❌ Jotkut tarkistukset epäonnistuivat{RESET}")
        print(f"{RED}{'='*50}{RESET}\n")
        print(f"{YELLOW}Korjaa ylläolevat ongelmat ja aja uudelleen:{RESET}")
        print(f"python check_setup.py\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

