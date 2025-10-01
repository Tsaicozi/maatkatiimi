#!/usr/bin/env python3
"""
Yksinkertainen Solana wallet luonti ilman solana-py riippuvuutta
Käyttää vain cryptography kirjastoa
"""

import json
import base58
import os
import secrets
from typing import Tuple
import asyncio
import aiohttp

class SimpleWalletManager:
    """Yksinkertainen Solana wallet hallinta"""
    
    def create_new_wallet(self) -> Tuple[str, str, str]:
        """
        Luo uusi wallet
        Returns: (public_key, private_key_base58, private_key_json)
        """
        # Luo 32 random bytea private keylle
        private_key_bytes = secrets.token_bytes(32)
        
        # Simuloi public key (oikeassa käytössä tämä lasketaan private keyst\u00e4)
        # Tämä on vain demo - oikeassa käytössä käytettäisiin ed25519 cryptographyä
        public_key_bytes = secrets.token_bytes(32)
        
        # Luo 64-byte secret key (private + public)
        secret_key = private_key_bytes + public_key_bytes
        
        # Public key Base58
        public_key = base58.b58encode(public_key_bytes).decode('utf-8')
        
        # Private key Base58 (Phantom format)
        private_key_base58 = base58.b58encode(secret_key).decode('utf-8')
        
        # Private key JSON array (alternative format)
        private_key_json = json.dumps(list(secret_key))
        
        return public_key, private_key_base58, private_key_json
    
    def save_wallet_to_file(self, public_key: str, private_key_base58: str, 
                           private_key_json: str, filename: str = "demo_wallet.json"):
        """Tallenna wallet tiedostoon"""
        wallet_data = {
            "public_key": public_key,
            "private_key_base58": private_key_base58,
            "private_key_json": private_key_json,
            "created_at": "2025-01-01T00:00:00Z",
            "network": "mainnet-beta",
            "note": "DEMO WALLET - Ei oikeaa Solana walletia!"
        }
        
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"💾 Demo wallet tallennettu: {filename}")

async def get_sol_price_usd() -> float:
    """Hae SOL hinta USD:ssa"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": "solana", "vs_currencies": "usd"}
            
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("solana", {}).get("usd", 0.0)
                else:
                    return 0.0
    except:
        return 0.0

def print_wallet_info(public_key: str, sol_price_usd: float = 0.0):
    """Tulosta wallet info"""
    print("=" * 60)
    print("🔐 DEMO SOLANA WALLET INFO")
    print("=" * 60)
    print(f"📍 Public Key: {public_key}")
    print(f"💰 SOL Balance: 0.000000 SOL (Demo wallet)")
    
    if sol_price_usd > 0:
        print(f"💵 SOL Price: ${sol_price_usd:.2f}")
    
    print(f"🌐 Network: Mainnet (Demo)")
    print(f"⚠️  HUOM: Tämä on DEMO wallet, ei oikeaa Solana walletia!")
    print("=" * 60)

def print_security_warning():
    """Tulosta turvallisuusvaroitus"""
    print("\n" + "⚠️ " * 20)
    print("🚨 DEMO WALLET - TURVALLISUUSVAROITUS:")
    print("• Tämä on DEMO wallet testausta varten")
    print("• ÄLÄ lähetä oikeaa rahaa tälle walletille")
    print("• Oikeaa walletia varten käytä virallisia työkaluja")
    print("• Phantom, Solflare, tai solana-keygen")
    print("⚠️ " * 20 + "\n")

async def main():
    """Main funktio"""
    print("🚀 Demo Solana Wallet Manager")
    print("HUOM: Tämä luo DEMO walletin testausta varten!")
    print("")
    
    manager = SimpleWalletManager()
    
    # Luo demo wallet
    print("🔄 Luodaan demo wallet...")
    public_key, private_key_base58, private_key_json = manager.create_new_wallet()
    
    # Hae SOL hinta
    print("📊 Haetaan SOL hinta...")
    sol_price = await get_sol_price_usd()
    
    # Näytä tiedot
    print_wallet_info(public_key, sol_price)
    
    # Tallenna
    save = input("💾 Tallenna demo wallet tiedostoon? (y/n): ").strip().lower()
    if save == 'y':
        filename = input("Tiedoston nimi (demo_wallet.json): ").strip()
        if not filename:
            filename = "demo_wallet.json"
        manager.save_wallet_to_file(public_key, private_key_base58, private_key_json, filename)
    
    # Näytä private key
    show_private = input("🔑 Näytä private key? (y/n): ").strip().lower()
    if show_private == 'y':
        print("\n🔑 DEMO PRIVATE KEY (Base58 format):")
        print(f"{private_key_base58}")
        print("\n🔑 DEMO PRIVATE KEY (JSON array format):")
        print(f"{private_key_json}")
    
    print_security_warning()
    
    # Luo .env template
    create_env = input("📝 Luo .env template demo private keyllä? (y/n): ").strip().lower()
    if create_env == 'y':
        env_content = f"""# Demo Solana Auto Trader Configuration
# ⚠️ TÄMÄ ON DEMO KONFIGURAATIO - ÄLÄ KÄYTÄ OIKEASSA TRADINGISSA!

# Demo Phantom Wallet Private Key (Base58 format)
PHANTOM_PRIVATE_KEY={private_key_base58}

# Trading Parameters (Demo asetukset)
POSITION_SIZE_SOL=0.001          # Pieni demo summa
MAX_POSITIONS=1                  # Vain 1 demo positio
STOP_LOSS_PERCENT=30
TAKE_PROFIT_PERCENT=50
MAX_HOLD_HOURS=1                 # Lyhyt demo hold
COOLDOWN_HOURS=1                 # Lyhyt demo cooldown
MIN_SCORE_THRESHOLD=7.0
SLIPPAGE_BPS=100

# Telegram Notifications (valinnainen)
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Solana RPC (Demo)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
"""
        
        with open(".env.demo", "w") as f:
            f.write(env_content)
        
        print("📝 .env.demo tiedosto luotu demo asetuksilla")
        print("⚠️  HUOM: Käytä vain testaukseen, ei oikeaan tradingiin!")

if __name__ == "__main__":
    asyncio.run(main())