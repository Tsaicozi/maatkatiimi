#!/usr/bin/env python3
"""
Demo Solana Trader - Simuloi trading toiminnot ilman oikeita transaktioita
Käyttää mock dataa ja simuloi Jupiter swap:eja
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import random
import os
from dotenv import load_dotenv

load_dotenv()

class DemoSolanaTrader:
    """Demo Solana Trader - simuloi trading toiminnot"""
    
    def __init__(self, private_key: str = "demo_key"):
        self.logger = logging.getLogger(__name__)
        self.private_key = private_key
        self.wallet_address = "DemoWallet123456789"
        
        # Mock balance
        self.mock_sol_balance = 1.0  # 1 SOL demo balance
        self.mock_token_balances = {}  # token_address -> amount
        
        self.session = None
        
        self.logger.info(f"✅ Demo SolanaTrader alustettu wallet: {self.wallet_address}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_sol_balance(self) -> float:
        """Hae mock SOL balance"""
        return self.mock_sol_balance

    async def get_token_balance(self, token_address: str) -> float:
        """Hae mock token balance"""
        return self.mock_token_balances.get(token_address, 0.0)

    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Optional[Dict]:
        """Simuloi Jupiter quote"""
        try:
            # Simuloi quote delay
            await asyncio.sleep(0.5)
            
            # Mock quote data
            if input_mint == "So11111111111111111111111111111111111111112":  # SOL
                # SOL -> Token
                input_amount_sol = amount / 1_000_000_000
                # Mock exchange rate: 1 SOL = 1M tokens
                output_amount = int(input_amount_sol * 1_000_000 * 1_000_000)
                
                quote = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "inAmount": str(amount),
                    "outAmount": str(output_amount),
                    "priceImpactPct": "0.1",
                    "routePlan": [{"swapInfo": {"ammKey": "DemoAMM"}}]
                }
            else:
                # Token -> SOL
                input_amount_tokens = amount / 1_000_000
                # Mock exchange rate: 1M tokens = 1 SOL
                output_amount = int((input_amount_tokens / 1_000_000) * 1_000_000_000)
                
                quote = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "inAmount": str(amount),
                    "outAmount": str(output_amount),
                    "priceImpactPct": "0.1",
                    "routePlan": [{"swapInfo": {"ammKey": "DemoAMM"}}]
                }
            
            self.logger.info(f"📊 Mock quote: {amount} -> {quote['outAmount']}")
            return quote
            
        except Exception as e:
            self.logger.error(f"Virhe mock quotessa: {e}")
            return None

    async def execute_jupiter_swap(self, quote: Dict) -> Optional[str]:
        """Simuloi Jupiter swap"""
        try:
            # Simuloi transaction delay
            await asyncio.sleep(1.0)
            
            # Mock transaction hash
            tx_hash = f"demo_tx_{random.randint(100000, 999999)}"
            
            # Päivitä mock balancet
            input_mint = quote["inputMint"]
            output_mint = quote["outputMint"]
            in_amount = int(quote["inAmount"])
            out_amount = int(quote["outAmount"])
            
            if input_mint == "So11111111111111111111111111111111111111112":
                # SOL -> Token
                sol_amount = in_amount / 1_000_000_000
                token_amount = out_amount / 1_000_000
                
                self.mock_sol_balance -= sol_amount
                self.mock_token_balances[output_mint] = self.mock_token_balances.get(output_mint, 0) + token_amount
                
            else:
                # Token -> SOL
                token_amount = in_amount / 1_000_000
                sol_amount = out_amount / 1_000_000_000
                
                self.mock_token_balances[input_mint] = self.mock_token_balances.get(input_mint, 0) - token_amount
                self.mock_sol_balance += sol_amount
            
            self.logger.info(f"✅ Mock swap onnistui: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            self.logger.error(f"Virhe mock swapissa: {e}")
            return None

    async def buy_token(self, token_address: str, sol_amount: float, slippage_bps: int = 50) -> Optional[Tuple[str, float]]:
        """Simuloi token osto"""
        try:
            self.logger.info(f"🔄 Mock osto: {token_address} {sol_amount} SOL:lla...")
            
            if self.mock_sol_balance < sol_amount:
                self.logger.error("❌ Ei riittävästi mock SOL:ia")
                return None
            
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Muunna SOL lamports
            amount_lamports = int(sol_amount * 1_000_000_000)
            
            # Hae mock quote
            quote = await self.get_jupiter_quote(sol_mint, token_address, amount_lamports, slippage_bps)
            if not quote:
                return None
                
            # Laske expected output
            expected_output = float(quote.get("outAmount", 0)) / 1_000_000
            
            # Suorita mock swap
            tx_hash = await self.execute_jupiter_swap(quote)
            if tx_hash:
                self.logger.info(f"✅ Mock osto onnistui: {expected_output:.0f} tokenia")
                return tx_hash, expected_output
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Virhe mock ostossa: {e}")
            return None

    async def sell_token(self, token_address: str, token_amount: float, slippage_bps: int = 50) -> Optional[Tuple[str, float]]:
        """Simuloi token myynti"""
        try:
            self.logger.info(f"🔄 Mock myynti: {token_amount} {token_address}...")
            
            current_balance = self.mock_token_balances.get(token_address, 0)
            if current_balance < token_amount:
                self.logger.error("❌ Ei riittävästi mock tokeneita")
                return None
            
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Muunna token amount
            amount_raw = int(token_amount * 1_000_000)
            
            # Hae mock quote
            quote = await self.get_jupiter_quote(token_address, sol_mint, amount_raw, slippage_bps)
            if not quote:
                return None
                
            # Laske expected output SOL
            expected_sol = float(quote.get("outAmount", 0)) / 1_000_000_000
            
            # Suorita mock swap
            tx_hash = await self.execute_jupiter_swap(quote)
            if tx_hash:
                self.logger.info(f"✅ Mock myynti onnistui: {expected_sol:.6f} SOL")
                return tx_hash, expected_sol
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Virhe mock myynnissä: {e}")
            return None

    async def get_token_price_sol(self, token_address: str) -> Optional[float]:
        """Simuloi token hinnan haku"""
        try:
            # Mock hinta: random välillä 0.000001 - 0.0001 SOL
            price = random.uniform(0.000001, 0.0001)
            return price
                
        except Exception as e:
            self.logger.error(f"Virhe mock hinnan haussa: {e}")
            return None

    async def estimate_gas_fee(self) -> float:
        """Mock gas fee"""
        return 0.000005  # 0.000005 SOL

    def print_mock_balances(self):
        """Tulosta mock balancet"""
        print("\n💰 MOCK BALANCET:")
        print(f"  SOL: {self.mock_sol_balance:.6f}")
        for token_addr, amount in self.mock_token_balances.items():
            print(f"  {token_addr[:8]}...: {amount:.0f}")

# Test funktio
async def test_demo_trader():
    """Testaa demo trader"""
    print("🚀 Demo Solana Trader Test")
    
    async with DemoSolanaTrader() as trader:
        # Hae mock balance
        balance = await trader.get_sol_balance()
        print(f"💰 Mock SOL Balance: {balance:.6f}")
        
        # Test mock quote
        bonk_address = "DemoToken123456789"
        quote = await trader.get_jupiter_quote(
            "So11111111111111111111111111111111111111112",  # SOL
            bonk_address,  # Demo token
            50_000_000,  # 0.05 SOL
            50  # 0.5% slippage
        )
        
        if quote:
            expected_tokens = float(quote.get("outAmount", 0)) / 1_000_000
            print(f"📊 Mock quote: 0.05 SOL -> {expected_tokens:.0f} tokens")
        
        # Test mock buy
        print("\n🔄 Testaa mock osto...")
        result = await trader.buy_token(bonk_address, 0.05, 50)
        if result:
            tx_hash, token_amount = result
            print(f"✅ Mock osto: {tx_hash}, {token_amount:.0f} tokenia")
        
        # Näytä balancet
        trader.print_mock_balances()
        
        # Test mock sell
        print("\n🔄 Testaa mock myynti...")
        if result:
            sell_result = await trader.sell_token(bonk_address, token_amount * 0.5, 50)
            if sell_result:
                sell_tx, sol_received = sell_result
                print(f"✅ Mock myynti: {sell_tx}, {sol_received:.6f} SOL")
        
        # Lopulliset balancet
        trader.print_mock_balances()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_demo_trader())