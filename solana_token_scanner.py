#!/usr/bin/env python3
"""
Solana Token Scanner - Skannaa uusia tokeneita Raydium/Jupiter poolista
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

import requests
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.keypair import Keypair

# =============================
# Config & setup
# =============================
load_dotenv('.env2')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Solana RPC endpoint (käytä Heliusta tai muuta premium RPC:tä)
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")

# Phantom wallet private key (base58 encoded)
PHANTOM_PRIVATE_KEY = os.getenv("PHANTOM_PRIVATE_KEY", "")

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trading parameters
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "5000"))  # $5k min liquidity
MIN_24H_VOLUME_USD = float(os.getenv("MIN_24H_VOLUME_USD_SOLANA", "2000"))  # $2k min volume
MAX_TOKEN_AGE_HOURS = int(os.getenv("MAX_TOKEN_AGE_HOURS", "168"))  # Max 7 days old tokens

# Raydium Program ID
RAYDIUM_LIQUIDITY_POOL_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# =============================
# Solana Client Setup
# =============================
if HELIUS_API_KEY:
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
else:
    rpc_url = SOLANA_RPC_URL

solana_client = Client(rpc_url)

# =============================
# Wallet Setup
# =============================
def load_wallet() -> Optional[Keypair]:
    """Load Phantom wallet from private key"""
    if not PHANTOM_PRIVATE_KEY:
        logger.error("PHANTOM_PRIVATE_KEY not set in .env2")
        return None
    
    try:
        # Base58 decode private key
        from base58 import b58decode
        private_key_bytes = b58decode(PHANTOM_PRIVATE_KEY)
        keypair = Keypair.from_bytes(private_key_bytes)
        logger.info(f"Wallet loaded: {keypair.pubkey()}")
        return keypair
    except Exception as e:
        logger.error(f"Failed to load wallet: {e}")
        return None

# =============================
# Raydium Pool Scanner
# =============================
def get_recent_raydium_pools(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Hae viimeisimmät Raydium poolit DexScreener API:sta
    """
    pools = []
    
    try:
        # Hae Solana boosted/trending tokenit jotka EIVÄT ole SOL
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pairs = data.get("pairs", [])
            
            for pair in pairs[:100]:  # Käy läpi top 100
                # Filtteröi Solana poolit, mutta EI SOL-pareja
                if pair.get("chainId") == "solana":
                    base_symbol = pair.get("baseToken", {}).get("symbol", "")
                    quote_symbol = pair.get("quoteToken", {}).get("symbol", "")
                    
                    # Skip pure SOL/SOL pairs ja ota vain TOKEN/SOL parit
                    if base_symbol == "SOL":
                        continue
                    
                    # Hyväksy TOKEN/SOL parit
                    if quote_symbol != "SOL":
                        continue
                    
                    token_addr = pair.get("baseToken", {}).get("address")
                    
                    # Älä lisää duplikaatteja
                    if any(p.get("token_address") == token_addr for p in pools):
                        continue
                    
                    pools.append({
                        "pair_address": pair.get("pairAddress"),
                        "token_address": token_addr,
                        "token_symbol": base_symbol,
                        "token_name": pair.get("baseToken", {}).get("name"),
                        "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                        "volume_24h_usd": float(pair.get("volume", {}).get("h24", 0) or 0),
                        "price_usd": float(pair.get("priceUsd", 0) or 0),
                        "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
                        "created_at": pair.get("pairCreatedAt"),
                        "fdv": float(pair.get("fdv", 0) or 0),
                        "dex_id": pair.get("dexId", ""),
                    })
                    
                    if len(pools) >= limit:
                        break
        
        logger.info(f"Found {len(pools)} Solana token pools")
        return pools
        
    except Exception as e:
        logger.error(f"Error fetching pools: {e}")
        return []

def filter_new_tokens(pools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filtteröi uudet tokenit kriteerien mukaan
    """
    filtered = []
    now = int(time.time() * 1000)  # milliseconds
    
    for pool in pools:
        symbol = pool.get("token_symbol", "UNKNOWN")
        
        # Tarkista ikä (skip jos liian vanha TAI jos tietoa ei ole -> hyväksytään)
        created_at = pool.get("created_at")
        if created_at:
            age_ms = now - created_at
            age_hours = age_ms / (1000 * 60 * 60)
            
            if age_hours > MAX_TOKEN_AGE_HOURS:
                logger.debug(f"{symbol}: too old ({age_hours:.1f}h)")
                continue
        
        # Tarkista likviditeetti
        liq = pool.get("liquidity_usd", 0)
        if liq < MIN_LIQUIDITY_USD:
            logger.debug(f"{symbol}: low liquidity (${liq:,.0f})")
            continue
        
        # Tarkista volyymi
        vol = pool.get("volume_24h_usd", 0)
        if vol < MIN_24H_VOLUME_USD:
            logger.debug(f"{symbol}: low volume (${vol:,.0f})")
            continue
        
        # Tarkista 24h muutos (vähintään +5%)
        change = pool.get("price_change_24h", 0)
        if change < 5:
            logger.debug(f"{symbol}: low price change ({change:+.1f}%)")
            continue
        
        logger.info(f"{symbol}: PASSED - Liq ${liq:,.0f}, Vol ${vol:,.0f}, Change {change:+.1f}%")
        filtered.append(pool)
    
    logger.info(f"Filtered to {len(filtered)} promising tokens")
    return filtered

# =============================
# Token Analysis
# =============================
def analyze_token(token: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analysoi tokenin ja laske risk/reward
    """
    score = 0
    
    # Likviditeetti pisteet
    liq = token.get("liquidity_usd", 0)
    if liq > 100000:
        score += 3
    elif liq > 50000:
        score += 2
    elif liq > 20000:
        score += 1
    
    # Volyymi pisteet
    vol = token.get("volume_24h_usd", 0)
    if vol > 50000:
        score += 3
    elif vol > 20000:
        score += 2
    elif vol > 10000:
        score += 1
    
    # Hinta muutos pisteet
    change_24h = token.get("price_change_24h", 0)
    if change_24h > 50:
        score += 3
    elif change_24h > 30:
        score += 2
    elif change_24h > 15:
        score += 1
    
    # Volume/Liquidity ratio
    vol_liq_ratio = vol / liq if liq > 0 else 0
    if vol_liq_ratio > 0.5:
        score += 2
    elif vol_liq_ratio > 0.3:
        score += 1
    
    # Luokittelu
    if score >= 8:
        risk_level = "LOW"
    elif score >= 5:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    
    return {
        **token,
        "score": score,
        "risk_level": risk_level,
        "vol_liq_ratio": vol_liq_ratio
    }

# =============================
# Telegram Notifications
# =============================
def send_telegram_message(text: str) -> None:
    """Send Telegram notification"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")

def format_token_alert(tokens: List[Dict[str, Any]]) -> str:
    """Format tokens for Telegram message"""
    if not tokens:
        return "🔍 No new promising tokens found"
    
    lines = ["🚀 <b>New Solana Tokens Found!</b>\n"]
    
    for token in tokens:
        symbol = token.get("token_symbol", "UNKNOWN")
        name = token.get("token_name", "")
        price = token.get("price_usd", 0)
        change_24h = token.get("price_change_24h", 0)
        liq = token.get("liquidity_usd", 0)
        vol = token.get("volume_24h_usd", 0)
        score = token.get("score", 0)
        risk = token.get("risk_level", "UNKNOWN")
        token_addr = token.get("token_address", "")
        
        # Risk emoji
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk, "⚪")
        
        lines.append(f"{risk_emoji} <b>{symbol}</b> {name}")
        lines.append(f"├ Price: ${price:.6f} ({change_24h:+.1f}%)")
        lines.append(f"├ Liq: ${liq:,.0f} | Vol: ${vol:,.0f}")
        lines.append(f"├ Score: {score}/12 | Risk: {risk}")
        lines.append(f"└ <code>{token_addr[:8]}...{token_addr[-8:]}</code>")
        lines.append("")
    
    return "\n".join(lines)

# =============================
# Main Scanner
# =============================
def run_scan():
    """Run token scanner"""
    logger.info("Starting Solana token scanner...")
    
    # 1. Hae uudet poolit
    pools = get_recent_raydium_pools(limit=100)
    
    if not pools:
        logger.info("No pools found")
        return
    
    # 2. Filtteröi
    new_tokens = filter_new_tokens(pools)
    
    if not new_tokens:
        logger.info("No tokens passed filters")
        send_telegram_message("🔍 Skannaus suoritettu. Ei uusia lupaavia tokeneita.")
        return
    
    # 3. Analysoi
    analyzed_tokens = [analyze_token(token) for token in new_tokens]
    
    # 4. Järjestä pisteiden mukaan
    analyzed_tokens.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 5. Ota top 5
    top_tokens = analyzed_tokens[:5]
    
    # 6. Lähetä Telegram
    message = format_token_alert(top_tokens)
    send_telegram_message(message)
    
    # 7. Tulosta logiin
    logger.info(f"Found {len(top_tokens)} top tokens")
    for token in top_tokens:
        logger.info(f"  {token.get('token_symbol')}: Score {token.get('score')}, Risk {token.get('risk_level')}")

if __name__ == "__main__":
    # Test wallet loading
    wallet = load_wallet()
    if wallet:
        logger.info(f"Wallet ready: {wallet.pubkey()}")
    
    # Run scan
    run_scan()
    
    logger.info("Scanner completed")

