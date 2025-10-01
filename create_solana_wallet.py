#!/usr/bin/env python3
"""
Solana wallet luonti ja hallinta
Luo uuden Phantom-yhteensopivan walletin tai tuo olemassa olevan
"""

import json
import base58
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.publickey import PublicKey
import os
from typing import Optional, Dict, Tuple
import asyncio
import aiohttp

class SolanaWalletManager:
    """Solana wallet hallinta"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = Client(rpc_url)
    
    def create_new_wallet(self) -> Tuple[str, str, str]:
        """
        Luo uusi wallet
        Returns: (public_key, private_key_base58, private_key_json)
        """
        # Luo uusi keypair
        keypair = Keypair()
        
        # Public key
        public_key = str(keypair.public_key)
        
        # Private key Base58 (Phantom format)
        private_key_bytes = keypair.secret_key
        private_key_base58 = base58.b58encode(private_key_bytes).decode('utf-8')
        
        # Private key JSON array (alternative format)
        private_key_json = json.dumps(list(private_key_bytes))
        
        return public_key, private_key_base58, private_key_json
    
    def import_wallet_from_private_key(self, private_key: str) -> Tuple[str, Keypair]:
        """
        Tuo wallet private keyst\u00e4
        Args:
            private_key: Base58 string tai JSON array string
        Returns: (public_key, keypair)
        """
        try:
            # Yrit\u00e4 Base58 decode
            if len(private_key) == 88:  # Base58 format
                private_key_bytes = base58.b58decode(private_key)
            else:  # JSON array format
                private_key_bytes = bytes(json.loads(private_key))
            
            # Luo keypair
            keypair = Keypair.from_secret_key(private_key_bytes)
            public_key = str(keypair.public_key)
            
            return public_key, keypair
            
        except Exception as e:
            raise ValueError(f"Virheellinen private key: {e}")
    
    def get_balance(self, public_key: str) -> float:
        """Hae SOL balance"""
        try:
            pubkey = PublicKey(public_key)
            response = self.client.get_balance(pubkey)
            balance_lamports = response.value
            balance_sol = balance_lamports / 1_000_000_000  # Lamports to SOL
            return balance_sol
        except Exception as e:
            print(f"Virhe balancen haussa: {e}")
            return 0.0
    
    def save_wallet_to_file(self, public_key: str, private_key_base58: str, 
                           private_key_json: str, filename: str = "solana_wallet.json"):
        """Tallenna wallet tiedostoon"""
        wallet_data = {
            "public_key": public_key,
            "private_key_base58": private_key_base58,
            "private_key_json": private_key_json,
            "created_at": "2025-01-01T00:00:00Z",
            "network": "mainnet-beta"
        }
        
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"💾 Wallet tallennettu: {filename}")
    
    def load_wallet_from_file(self, filename: str = "solana_wallet.json") -> Optional[Dict]:
        """Lataa wallet tiedostosta"""
        try:
            if not os.path.exists(filename):
                return None
                
            with open(filename, 'r') as f:
                wallet_data = json.load(f)
            
            return wallet_data
        except Exception as e:
            print(f"Virhe wallet latauksessa: {e}")
            return None

async def get_sol_price_usd() -> float:
    """Hae SOL hinta USD:ssa"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": "solana", "vs_currencies": "usd"}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("solana", {}).get("usd", 0.0)
                else:
                    return 0.0
    except:
        return 0.0

def print_wallet_info(public_key: str, balance_sol: float, sol_price_usd: float = 0.0):
    """Tulosta wallet info"""
    print("=" * 60)
    print("🔐 SOLANA WALLET INFO")
    print("=" * 60)
    print(f"📍 Public Key: {public_key}")
    print(f"💰 SOL Balance: {balance_sol:.6f} SOL")
    
    if sol_price_usd > 0:
        balance_usd = balance_sol * sol_price_usd
        print(f"💵 USD Value: ${balance_usd:.2f} (SOL @ ${sol_price_usd:.2f})")
    
    print(f"🌐 Network: Mainnet")
    print(f"🔗 Explorer: https://explorer.solana.com/address/{public_key}")
    print("=" * 60)

def print_security_warning():
    """Tulosta turvallisuusvaroitus"""
    print("\n" + "⚠️ " * 20)
    print("🚨 TURVALLISUUSVAROITUS:")
    print("• ÄLÄ KOSKAAN jaa private keyä kenenkään kanssa")
    print("• SÄILYTÄ private key turvallisessa paikassa")
    print("• KÄYTÄ vain luotettavia sovelluksia")
    print("• TESTAA aina pienillä summilla ensin")
    print("• VARMISTA osoitteet ennen lähettämistä")
    print("⚠️ " * 20 + "\n")

async def main():
    """Main funktio"""
    print("🚀 Solana Wallet Manager")
    print("1. Luo uusi wallet")
    print("2. Tuo olemassa oleva wallet")
    print("3. Lataa tallennettu wallet")
    print("4. Poistu")
    
    choice = input("\nValitse toiminto (1-4): ").strip()
    
    manager = SolanaWalletManager()
    
    if choice == "1":
        # Luo uusi wallet
        print("\n🔄 Luodaan uusi wallet...")
        public_key, private_key_base58, private_key_json = manager.create_new_wallet()
        
        # Hae balance ja hinta
        balance = manager.get_balance(public_key)
        sol_price = await get_sol_price_usd()
        
        # Näytä tiedot
        print_wallet_info(public_key, balance, sol_price)
        
        # Tallenna
        save = input("\n💾 Tallenna wallet tiedostoon? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("Tiedoston nimi (solana_wallet.json): ").strip()
            if not filename:
                filename = "solana_wallet.json"
            manager.save_wallet_to_file(public_key, private_key_base58, private_key_json, filename)
        
        # Näytä private key
        print("\n🔑 PRIVATE KEY (Base58 - Phantom format):")
        print(f"{private_key_base58}")
        print("\n🔑 PRIVATE KEY (JSON array format):")
        print(f"{private_key_json}")
        
        print_security_warning()
    
    elif choice == "2":
        # Tuo wallet
        print("\n🔄 Tuodaan olemassa oleva wallet...")
        private_key = input("Anna private key (Base58 tai JSON): ").strip()
        
        try:
            public_key, keypair = manager.import_wallet_from_private_key(private_key)
            
            # Hae balance ja hinta
            balance = manager.get_balance(public_key)
            sol_price = await get_sol_price_usd()
            
            # Näytä tiedot
            print_wallet_info(public_key, balance, sol_price)
            
            # Tallenna
            save = input("\n💾 Tallenna wallet tiedostoon? (y/n): ").strip().lower()
            if save == 'y':
                filename = input("Tiedoston nimi (solana_wallet.json): ").strip()
                if not filename:
                    filename = "solana_wallet.json"
                
                # Muunna private key Base58:ksi jos JSON
                if private_key.startswith('['):
                    private_key_bytes = bytes(json.loads(private_key))
                    private_key_base58 = base58.b58encode(private_key_bytes).decode('utf-8')
                    private_key_json = private_key
                else:
                    private_key_base58 = private_key
                    private_key_bytes = base58.b58decode(private_key)
                    private_key_json = json.dumps(list(private_key_bytes))
                
                manager.save_wallet_to_file(public_key, private_key_base58, private_key_json, filename)
            
        except ValueError as e:
            print(f"❌ Virhe: {e}")
    
    elif choice == "3":
        # Lataa tallennettu wallet
        filename = input("Wallet tiedoston nimi (solana_wallet.json): ").strip()
        if not filename:
            filename = "solana_wallet.json"
        
        wallet_data = manager.load_wallet_from_file(filename)
        if wallet_data:
            public_key = wallet_data["public_key"]
            
            # Hae balance ja hinta
            balance = manager.get_balance(public_key)
            sol_price = await get_sol_price_usd()
            
            # Näytä tiedot
            print_wallet_info(public_key, balance, sol_price)
            
            # Näytä private key jos halutaan
            show_private = input("\n🔑 Näytä private key? (y/n): ").strip().lower()
            if show_private == 'y':
                print(f"\n🔑 Private Key (Base58): {wallet_data['private_key_base58']}")
                print(f"🔑 Private Key (JSON): {wallet_data['private_key_json']}")
                print_security_warning()
        else:
            print(f"❌ Wallet tiedostoa ei löytynyt: {filename}")
    
    elif choice == "4":
        print("👋 Näkemiin!")
    
    else:
        print("❌ Virheellinen valinta")

def create_env_template():
    """Luo .env template"""
    env_template = """# Solana Auto Trader Configuration

# Phantom Wallet Private Key (Base58 format)
PHANTOM_PRIVATE_KEY=your_private_key_here

# Trading Parameters
POSITION_SIZE_SOL=0.05
MAX_POSITIONS=3
STOP_LOSS_PERCENT=30
TAKE_PROFIT_PERCENT=50
MAX_HOLD_HOURS=48
COOLDOWN_HOURS=24
MIN_SCORE_THRESHOLD=7.0
SLIPPAGE_BPS=100

# Telegram Notifications (optional)
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Solana RPC (optional, defaults to public RPC)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
"""
    
    with open(".env.example", "w") as f:
        f.write(env_template)
    
    print("📝 .env.example tiedosto luotu")

if __name__ == "__main__":
    # Luo .env template jos ei ole olemassa
    if not os.path.exists(".env.example"):
        create_env_template()
    
    # Aja main
    asyncio.run(main())