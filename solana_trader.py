import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import base64
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import transfer, TransferParams
from solana.publickey import PublicKey
import os
from dotenv import load_dotenv

load_dotenv()

class SolanaTrader:
    """Jupiter DEX swap-integraatio Solana tradingiin"""
    
    def __init__(self, private_key: str, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.logger = logging.getLogger(__name__)
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
        # Luo keypair private keyst\u00e4
        try:
            # Private key voi olla base58 tai bytes
            if isinstance(private_key, str):
                if len(private_key) == 88:  # Base58
                    import base58
                    private_key_bytes = base58.b58decode(private_key)
                else:  # JSON array string
                    private_key_bytes = bytes(json.loads(private_key))
            else:
                private_key_bytes = private_key
                
            self.keypair = Keypair.from_secret_key(private_key_bytes)
            self.wallet_address = str(self.keypair.public_key)
            
        except Exception as e:
            self.logger.error(f"Virhe keypair luonnissa: {e}")
            raise
            
        # Jupiter API
        self.jupiter_url = "https://quote-api.jup.ag/v6"
        self.session = None
        
        self.logger.info(f"✅ SolanaTrader alustettu wallet: {self.wallet_address}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self.client.close()

    async def get_sol_balance(self) -> float:
        """Hae SOL balance"""
        try:
            response = await self.client.get_balance(self.keypair.public_key, commitment=Confirmed)
            balance_lamports = response.value
            balance_sol = balance_lamports / 1_000_000_000  # Lamports to SOL
            return balance_sol
        except Exception as e:
            self.logger.error(f"Virhe SOL balancen haussa: {e}")
            return 0.0

    async def get_token_balance(self, token_address: str) -> float:
        """Hae token balance"""
        try:
            # Hae token accounts
            token_accounts = await self.client.get_token_accounts_by_owner(
                self.keypair.public_key,
                {"mint": PublicKey(token_address)},
                commitment=Confirmed
            )
            
            if not token_accounts.value:
                return 0.0
                
            # Laske yhteenlaskettu balance
            total_balance = 0.0
            for account in token_accounts.value:
                account_info = await self.client.get_account_info(
                    PublicKey(account.pubkey),
                    commitment=Confirmed
                )
                if account_info.value:
                    # Parse token account data (yksinkertaistettu)
                    data = account_info.value.data
                    if len(data) >= 64:
                        # Token amount on bytes 64-72
                        amount_bytes = data[64:72]
                        amount = int.from_bytes(amount_bytes, 'little')
                        total_balance += amount
                        
            return total_balance / 1_000_000  # Assuming 6 decimals
            
        except Exception as e:
            self.logger.error(f"Virhe token balancen haussa: {e}")
            return 0.0

    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Optional[Dict]:
        """Hae Jupiter quote"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": str(slippage_bps),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            async with self.session.get(f"{self.jupiter_url}/quote", params=params) as response:
                if response.status == 200:
                    quote = await response.json()
                    return quote
                else:
                    self.logger.error(f"Jupiter quote virhe: {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Virhe Jupiter quotessa: {e}")
            return None

    async def execute_jupiter_swap(self, quote: Dict) -> Optional[str]:
        """Suorita Jupiter swap"""
        try:
            # Luo swap transaction
            swap_data = {
                "quoteResponse": quote,
                "userPublicKey": self.wallet_address,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": True,
                "feeAccount": None,
                "trackingAccount": None,
                "asLegacyTransaction": False
            }
            
            async with self.session.post(f"{self.jupiter_url}/swap", json=swap_data) as response:
                if response.status == 200:
                    swap_response = await response.json()
                    
                    # Hae transaction
                    swap_transaction = swap_response.get("swapTransaction")
                    if not swap_transaction:
                        self.logger.error("Ei swap transactionia vastauksessa")
                        return None
                        
                    # Decode transaction
                    transaction_bytes = base64.b64decode(swap_transaction)
                    transaction = Transaction.deserialize(transaction_bytes)
                    
                    # Allekirjoita transaction
                    transaction.sign(self.keypair)
                    
                    # L\u00e4het\u00e4 transaction
                    result = await self.client.send_transaction(
                        transaction,
                        self.keypair,
                        opts={"skip_preflight": False, "preflight_commitment": Confirmed}
                    )
                    
                    if result.value:
                        tx_hash = str(result.value)
                        self.logger.info(f"✅ Swap onnistui: {tx_hash}")
                        return tx_hash
                    else:
                        self.logger.error("Transaction l\u00e4hetys ep\u00e4onnistui")
                        return None
                        
                else:
                    error_text = await response.text()
                    self.logger.error(f"Jupiter swap virhe: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Virhe Jupiter swapissa: {e}")
            return None

    async def buy_token(self, token_address: str, sol_amount: float, slippage_bps: int = 50) -> Optional[Tuple[str, float]]:
        """Osta token SOL:lla"""
        try:
            self.logger.info(f"🔄 Ostetaan {token_address} {sol_amount} SOL:lla...")
            
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Muunna SOL lamports
            amount_lamports = int(sol_amount * 1_000_000_000)
            
            # Hae quote
            quote = await self.get_jupiter_quote(sol_mint, token_address, amount_lamports, slippage_bps)
            if not quote:
                self.logger.error("Ei saatu quotea")
                return None
                
            # Laske expected output
            expected_output = float(quote.get("outAmount", 0)) / 1_000_000  # Assuming 6 decimals
            
            # Suorita swap
            tx_hash = await self.execute_jupiter_swap(quote)
            if tx_hash:
                self.logger.info(f"✅ Osto onnistui: {expected_output:.2f} tokenia")
                return tx_hash, expected_output
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Virhe token ostossa: {e}")
            return None

    async def sell_token(self, token_address: str, token_amount: float, slippage_bps: int = 50) -> Optional[Tuple[str, float]]:
        """Myy token SOL:ksi"""
        try:
            self.logger.info(f"🔄 Myyd\u00e4\u00e4n {token_amount} {token_address}...")
            
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Muunna token amount (assuming 6 decimals)
            amount_raw = int(token_amount * 1_000_000)
            
            # Hae quote
            quote = await self.get_jupiter_quote(token_address, sol_mint, amount_raw, slippage_bps)
            if not quote:
                self.logger.error("Ei saatu quotea")
                return None
                
            # Laske expected output SOL
            expected_sol = float(quote.get("outAmount", 0)) / 1_000_000_000
            
            # Suorita swap
            tx_hash = await self.execute_jupiter_swap(quote)
            if tx_hash:
                self.logger.info(f"✅ Myynti onnistui: {expected_sol:.6f} SOL")
                return tx_hash, expected_sol
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Virhe token myynniss\u00e4: {e}")
            return None

    async def get_token_price_sol(self, token_address: str) -> Optional[float]:
        """Hae token hinta SOL:ssa"""
        try:
            # Hae quote pienell\u00e4 m\u00e4\u00e4r\u00e4ll\u00e4 hinnan selvitt\u00e4miseksi
            sol_mint = "So11111111111111111111111111111111111111112"
            test_amount = 1_000_000  # 1 token (6 decimals)
            
            quote = await self.get_jupiter_quote(token_address, sol_mint, test_amount, 50)
            if quote:
                output_amount = float(quote.get("outAmount", 0))
                price_sol = output_amount / 1_000_000_000  # Lamports to SOL
                return price_sol
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Virhe hinnan haussa: {e}")
            return None

    async def estimate_gas_fee(self) -> float:
        """Arvioi gas fee SOL:ssa"""
        try:
            # Hae recent blockhash ja fee
            recent_blockhash = await self.client.get_recent_blockhash(commitment=Confirmed)
            if recent_blockhash.value:
                # Arvio: 0.000005 SOL per transaction
                return 0.000005
            else:
                return 0.00001  # Fallback
                
        except Exception as e:
            self.logger.error(f"Virhe gas fee arviossa: {e}")
            return 0.00001

# Test funktio
async def test_trader():
    """Testaa trader"""
    # Test private key (\u00c4L\u00c4 K\u00c4YT\u00c4 OIKEAA!)
    test_private_key = os.getenv("PHANTOM_PRIVATE_KEY", "")
    
    if not test_private_key:
        print("❌ Aseta PHANTOM_PRIVATE_KEY .env tiedostoon")
        return
        
    async with SolanaTrader(test_private_key) as trader:
        # Hae balance
        balance = await trader.get_sol_balance()
        print(f"💰 SOL Balance: {balance:.6f}")
        
        # Hae gas fee arvio
        gas_fee = await trader.estimate_gas_fee()
        print(f"⛽ Arvioitu gas fee: {gas_fee:.6f} SOL")
        
        # Test quote (ei suorita)
        bonk_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        quote = await trader.get_jupiter_quote(
            "So11111111111111111111111111111111111111112",  # SOL
            bonk_address,  # BONK
            50_000_000,  # 0.05 SOL
            50  # 0.5% slippage
        )
        
        if quote:
            expected_tokens = float(quote.get("outAmount", 0)) / 1_000_000
            print(f"📊 0.05 SOL ostaa ~{expected_tokens:.0f} BONK")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_trader())