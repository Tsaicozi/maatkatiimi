#!/usr/bin/env python3
"""
Solana DEX Trader - Trade tokens using Jupiter aggregator
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dotenv import load_dotenv

import requests
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.instruction import Instruction
from base58 import b58decode, b58encode

# =============================
# Config & setup
# =============================
load_dotenv('.env2')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Solana RPC
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")

if HELIUS_API_KEY:
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
else:
    rpc_url = SOLANA_RPC_URL

solana_client = Client(rpc_url)

# Wallet
PHANTOM_PRIVATE_KEY = os.getenv("PHANTOM_PRIVATE_KEY", "")

# Jupiter API
JUPITER_API_URL = "https://quote-api.jup.ag/v6"

# SOL token mint
SOL_MINT = "So11111111111111111111111111111111111111112"

# Trading params
MAX_SLIPPAGE_BPS = int(os.getenv("MAX_SLIPPAGE_BPS", "300"))  # 3% slippage
POSITION_SIZE_SOL = float(os.getenv("POSITION_SIZE_SOL", "0.05"))  # 0.05 SOL per trade

# =============================
# Wallet Functions
# =============================
def load_wallet() -> Optional[Keypair]:
    """Load wallet from private key"""
    if not PHANTOM_PRIVATE_KEY:
        logger.error("PHANTOM_PRIVATE_KEY not set")
        return None
    
    try:
        private_key_bytes = b58decode(PHANTOM_PRIVATE_KEY)
        keypair = Keypair.from_bytes(private_key_bytes)
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        return keypair
    except Exception as e:
        logger.error(f"Failed to load wallet: {e}")
        return None

def get_sol_balance(wallet: Keypair) -> float:
    """Get SOL balance in wallet"""
    try:
        response = solana_client.get_balance(wallet.pubkey())
        balance_lamports = response.value
        balance_sol = balance_lamports / 1_000_000_000
        return balance_sol
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        return 0.0

def get_token_balance(wallet: Keypair, token_mint: str) -> float:
    """Get SPL token balance"""
    try:
        # Get token accounts for this wallet
        response = solana_client.get_token_accounts_by_owner(
            wallet.pubkey(),
            {"mint": Pubkey.from_string(token_mint)}
        )
        
        if response.value:
            # Parse token account data
            account_info = response.value[0]
            # Token balance is in account data (need to parse)
            # For simplicity, return 0 for now - will implement proper parsing
            return 0.0
        return 0.0
    except Exception as e:
        logger.error(f"Failed to get token balance: {e}")
        return 0.0

# =============================
# Jupiter Swap Functions
# =============================
def get_jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount_lamports: int,
    slippage_bps: int = MAX_SLIPPAGE_BPS
) -> Optional[Dict[str, Any]]:
    """
    Get swap quote from Jupiter
    
    Args:
        input_mint: Input token mint address (SOL or token)
        output_mint: Output token mint address
        amount_lamports: Amount in lamports (1 SOL = 1_000_000_000 lamports)
        slippage_bps: Slippage in basis points (300 = 3%)
    """
    try:
        url = f"{JUPITER_API_URL}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_lamports),
            "slippageBps": str(slippage_bps),
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        quote = response.json()
        logger.info(f"Jupiter quote: {amount_lamports} lamports -> {quote.get('outAmount')} tokens")
        return quote
        
    except Exception as e:
        logger.error(f"Failed to get Jupiter quote: {e}")
        return None

def execute_jupiter_swap(
    wallet: Keypair,
    quote: Dict[str, Any]
) -> Optional[str]:
    """
    Execute swap using Jupiter quote
    
    Returns:
        Transaction signature if successful, None otherwise
    """
    try:
        # Get swap transaction from Jupiter
        url = f"{JUPITER_API_URL}/swap"
        payload = {
            "quoteResponse": quote,
            "userPublicKey": str(wallet.pubkey()),
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        swap_data = response.json()
        swap_transaction_base64 = swap_data.get("swapTransaction")
        
        if not swap_transaction_base64:
            logger.error("No swap transaction returned from Jupiter")
            return None
        
        # Decode and sign transaction
        transaction_bytes = b58decode(swap_transaction_base64)
        transaction = VersionedTransaction.from_bytes(transaction_bytes)
        
        # Sign transaction
        signed_tx = wallet.sign_message(bytes(transaction.message))
        
        # Send transaction
        response = solana_client.send_raw_transaction(
            bytes(transaction),
            opts={"skip_preflight": False, "preflight_commitment": Confirmed}
        )
        
        signature = response.value
        logger.info(f"Transaction sent: {signature}")
        
        # Wait for confirmation
        for _ in range(30):  # 30 seconds timeout
            time.sleep(1)
            status = solana_client.get_signature_statuses([signature])
            if status.value and status.value[0]:
                if status.value[0].confirmation_status == "confirmed":
                    logger.info(f"Transaction confirmed: {signature}")
                    return str(signature)
        
        logger.warning(f"Transaction not confirmed within 30s: {signature}")
        return str(signature)
        
    except Exception as e:
        logger.error(f"Failed to execute swap: {e}")
        return None

# =============================
# Trading Functions
# =============================
def buy_token(
    wallet: Keypair,
    token_mint: str,
    amount_sol: float = POSITION_SIZE_SOL,
    slippage_bps: int = MAX_SLIPPAGE_BPS
) -> Optional[Dict[str, Any]]:
    """
    Buy a token with SOL
    
    Returns:
        Dict with transaction details if successful
    """
    try:
        logger.info(f"Buying {amount_sol} SOL worth of token {token_mint}")
        
        # Check SOL balance
        sol_balance = get_sol_balance(wallet)
        if sol_balance < amount_sol + 0.01:  # +0.01 for fees
            logger.error(f"Insufficient SOL balance: {sol_balance:.4f} < {amount_sol + 0.01:.4f}")
            return None
        
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        # Get quote
        quote = get_jupiter_quote(
            input_mint=SOL_MINT,
            output_mint=token_mint,
            amount_lamports=amount_lamports,
            slippage_bps=slippage_bps
        )
        
        if not quote:
            logger.error("Failed to get Jupiter quote")
            return None
        
        # Get expected output amount
        out_amount = int(quote.get("outAmount", 0))
        in_amount = int(quote.get("inAmount", 0))
        
        logger.info(f"Quote: {in_amount / 1e9:.4f} SOL -> {out_amount} tokens")
        
        # Execute swap
        signature = execute_jupiter_swap(wallet, quote)
        
        if not signature:
            logger.error("Failed to execute swap")
            return None
        
        return {
            "signature": signature,
            "token_mint": token_mint,
            "amount_sol": amount_sol,
            "expected_tokens": out_amount,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "buy"
        }
        
    except Exception as e:
        logger.error(f"Error buying token: {e}")
        return None

def sell_token(
    wallet: Keypair,
    token_mint: str,
    amount_tokens: int,
    slippage_bps: int = MAX_SLIPPAGE_BPS
) -> Optional[Dict[str, Any]]:
    """
    Sell a token for SOL
    
    Returns:
        Dict with transaction details if successful
    """
    try:
        logger.info(f"Selling {amount_tokens} of token {token_mint}")
        
        # Get quote
        quote = get_jupiter_quote(
            input_mint=token_mint,
            output_mint=SOL_MINT,
            amount_lamports=amount_tokens,
            slippage_bps=slippage_bps
        )
        
        if not quote:
            logger.error("Failed to get Jupiter quote for sell")
            return None
        
        # Get expected output SOL
        out_amount_lamports = int(quote.get("outAmount", 0))
        out_amount_sol = out_amount_lamports / 1_000_000_000
        
        logger.info(f"Quote: {amount_tokens} tokens -> {out_amount_sol:.4f} SOL")
        
        # Execute swap
        signature = execute_jupiter_swap(wallet, quote)
        
        if not signature:
            logger.error("Failed to execute sell swap")
            return None
        
        return {
            "signature": signature,
            "token_mint": token_mint,
            "amount_tokens": amount_tokens,
            "received_sol": out_amount_sol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "sell"
        }
        
    except Exception as e:
        logger.error(f"Error selling token: {e}")
        return None

# =============================
# Test Functions
# =============================
def test_trading():
    """Test trading functionality"""
    logger.info("=== Testing Solana Trader ===")
    
    # Load wallet
    wallet = load_wallet()
    if not wallet:
        logger.error("Failed to load wallet")
        return
    
    # Check balance
    balance = get_sol_balance(wallet)
    logger.info(f"Wallet: {wallet.pubkey()}")
    logger.info(f"Balance: {balance:.4f} SOL")
    
    if balance < 0.1:
        logger.error("Insufficient balance for testing")
        return
    
    logger.info("Trader ready for live trading!")

if __name__ == "__main__":
    test_trading()

