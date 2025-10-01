#!/usr/bin/env python3
"""
Solana Auto Trader - Automatic token scanner and trader
"""
import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Import our modules
from solana_token_scanner import (
    get_recent_raydium_pools,
    filter_new_tokens,
    analyze_token,
    send_telegram_message
)
from solana_trader import (
    load_wallet,
    get_sol_balance,
    buy_token,
    sell_token
)

# =============================
# Config
# =============================
load_dotenv('.env2')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("solana_auto_trader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Trading parameters
POSITION_SIZE_SOL = float(os.getenv("POSITION_SIZE_SOL", "0.05"))  # 0.05 SOL per trade
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "3"))  # Max 3 open positions
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.30"))  # 30% stop loss
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.50"))  # 50% take profit
MAX_HOLD_HOURS = int(os.getenv("MAX_HOLD_HOURS", "48"))  # Max 48h hold time

# State file
POSITIONS_FILE = "solana_positions.json"
COOLDOWN_FILE = "solana_cooldown.json"
COOLDOWN_HOURS = int(os.getenv("COOLDOWN_HOURS", "24"))  # Don't rebuy same token for 24h

# =============================
# Position Management
# =============================
def load_positions() -> Dict[str, Any]:
    """Load open positions from file"""
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
    return {"open": [], "closed": []}

def save_positions(positions: Dict[str, Any]) -> None:
    """Save positions to file"""
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving positions: {e}")

def load_cooldown() -> Dict[str, str]:
    """Load cooldown tokens (token_mint -> last_trade_time)"""
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cooldown: {e}")
    return {}

def save_cooldown(cooldown: Dict[str, str]) -> None:
    """Save cooldown to file"""
    try:
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(cooldown, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cooldown: {e}")

def is_in_cooldown(token_mint: str, cooldown: Dict[str, str]) -> bool:
    """Check if token is in cooldown period"""
    if token_mint not in cooldown:
        return False
    
    try:
        last_trade = datetime.fromisoformat(cooldown[token_mint])
        now = datetime.now(timezone.utc)
        hours_since = (now - last_trade).total_seconds() / 3600
        return hours_since < COOLDOWN_HOURS
    except:
        return False

# =============================
# Trading Logic
# =============================
def open_new_positions(
    wallet,
    tokens: List[Dict[str, Any]],
    positions: Dict[str, Any],
    cooldown: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Open new positions from token signals
    
    Returns:
        List of newly opened positions
    """
    opened = []
    open_count = len(positions.get("open", []))
    
    for token in tokens:
        if open_count >= MAX_POSITIONS:
            logger.info(f"Max positions ({MAX_POSITIONS}) reached")
            break
        
        token_mint = token.get("token_address")
        symbol = token.get("token_symbol")
        
        # Check if already in position
        if any(p.get("token_mint") == token_mint for p in positions.get("open", [])):
            logger.info(f"{symbol}: already in position")
            continue
        
        # Check cooldown
        if is_in_cooldown(token_mint, cooldown):
            logger.info(f"{symbol}: in cooldown period")
            continue
        
        # Check score threshold
        score = token.get("score", 0)
        if score < 5:  # Minimum score 5/12
            logger.info(f"{symbol}: score too low ({score}/12)")
            continue
        
        # Try to buy
        logger.info(f"Opening position: {symbol} (score {score}/12)")
        
        result = buy_token(wallet, token_mint, POSITION_SIZE_SOL)
        
        if result:
            # Create position entry
            position = {
                "token_mint": token_mint,
                "token_symbol": symbol,
                "token_name": token.get("token_name", ""),
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "entry_sol": POSITION_SIZE_SOL,
                "entry_price_usd": token.get("price_usd", 0),
                "expected_tokens": result.get("expected_tokens", 0),
                "tx_signature": result.get("signature"),
                "score": score,
                "risk_level": token.get("risk_level", "UNKNOWN"),
                "stop_loss_pct": STOP_LOSS_PCT,
                "take_profit_pct": TAKE_PROFIT_PCT,
            }
            
            positions["open"].append(position)
            opened.append(position)
            open_count += 1
            
            # Add to cooldown
            cooldown[token_mint] = datetime.now(timezone.utc).isoformat()
            
            # Send Telegram notification
            msg = format_entry_message(position, token)
            send_telegram_message(msg)
            
            logger.info(f"Position opened: {symbol}")
            time.sleep(2)  # Wait between trades
        else:
            logger.error(f"Failed to buy {symbol}")
    
    return opened

def evaluate_positions(wallet, positions: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate open positions and close if needed
    
    Returns:
        List of closed positions
    """
    closed = []
    still_open = []
    
    for pos in positions.get("open", []):
        symbol = pos.get("token_symbol")
        token_mint = pos.get("token_mint")
        
        try:
            # Get current price (from DexScreener or similar)
            # For now, simplified - in production, fetch live price
            # current_price = get_token_price(token_mint)
            
            # Check time-based exit
            entry_time = datetime.fromisoformat(pos.get("entry_time"))
            now = datetime.now(timezone.utc)
            hours_held = (now - entry_time).total_seconds() / 3600
            
            should_close = False
            exit_reason = None
            
            if hours_held >= MAX_HOLD_HOURS:
                should_close = True
                exit_reason = f"Time-based exit ({hours_held:.1f}h)"
            
            # TODO: Add price-based exits (stop-loss, take-profit)
            # This requires fetching current price and calculating PnL
            
            if should_close:
                logger.info(f"Closing position: {symbol} - {exit_reason}")
                
                # Try to sell
                expected_tokens = pos.get("expected_tokens", 0)
                result = sell_token(wallet, token_mint, expected_tokens)
                
                if result:
                    pos["exit_time"] = datetime.now(timezone.utc).isoformat()
                    pos["exit_reason"] = exit_reason
                    pos["exit_sol"] = result.get("received_sol", 0)
                    pos["exit_signature"] = result.get("signature")
                    pos["pnl_sol"] = pos["exit_sol"] - pos["entry_sol"]
                    pos["pnl_pct"] = (pos["pnl_sol"] / pos["entry_sol"]) * 100
                    
                    closed.append(pos)
                    positions["closed"].append(pos)
                    
                    # Send Telegram notification
                    msg = format_exit_message(pos)
                    send_telegram_message(msg)
                    
                    logger.info(f"Position closed: {symbol}, PnL: {pos['pnl_pct']:.1f}%")
                else:
                    logger.error(f"Failed to sell {symbol}")
                    still_open.append(pos)
            else:
                still_open.append(pos)
                
        except Exception as e:
            logger.error(f"Error evaluating position {symbol}: {e}")
            still_open.append(pos)
    
    positions["open"] = still_open
    return closed

# =============================
# Telegram Formatting
# =============================
def format_entry_message(position: Dict[str, Any], token: Dict[str, Any]) -> str:
    """Format entry notification"""
    symbol = position.get("token_symbol")
    risk = position.get("risk_level")
    score = position.get("score")
    entry_sol = position.get("entry_sol")
    
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk, "⚪")
    
    msg = f"""
🚀 <b>NEW POSITION OPENED</b>

{risk_emoji} <b>{symbol}</b> (Risk: {risk})
├ Score: {score}/12
├ Entry: {entry_sol:.4f} SOL
├ Stop Loss: -{position.get('stop_loss_pct', 0)*100:.0f}%
├ Take Profit: +{position.get('take_profit_pct', 0)*100:.0f}%
└ Liquidity: ${token.get('liquidity_usd', 0):,.0f}

<a href="https://solscan.io/token/{position.get('token_mint')}">View on Solscan</a>
"""
    return msg.strip()

def format_exit_message(position: Dict[str, Any]) -> str:
    """Format exit notification"""
    symbol = position.get("token_symbol")
    pnl_pct = position.get("pnl_pct", 0)
    pnl_sol = position.get("pnl_sol", 0)
    reason = position.get("exit_reason", "unknown")
    
    emoji = "🟢" if pnl_sol > 0 else "🔴"
    
    msg = f"""
{emoji} <b>POSITION CLOSED</b>

<b>{symbol}</b>
├ Exit: {reason}
├ Entry: {position.get('entry_sol'):.4f} SOL
├ Exit: {position.get('exit_sol'):.4f} SOL
└ PnL: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)
"""
    return msg.strip()

# =============================
# Main Trading Loop
# =============================
def run_trading_cycle():
    """Run one trading cycle: scan + trade"""
    logger.info("=== Starting trading cycle ===")
    
    # Load wallet
    wallet = load_wallet()
    if not wallet:
        logger.error("Failed to load wallet")
        return
    
    # Check balance
    balance = get_sol_balance(wallet)
    logger.info(f"Wallet balance: {balance:.4f} SOL")
    
    if balance < POSITION_SIZE_SOL + 0.01:
        logger.warning(f"Insufficient balance for trading: {balance:.4f} SOL")
        return
    
    # Load positions and cooldown
    positions = load_positions()
    cooldown = load_cooldown()
    
    # Evaluate existing positions
    logger.info(f"Evaluating {len(positions.get('open', []))} open positions")
    closed = evaluate_positions(wallet, positions)
    
    # Scan for new tokens
    logger.info("Scanning for new token opportunities...")
    pools = get_recent_raydium_pools(limit=50)
    new_tokens = filter_new_tokens(pools)
    analyzed_tokens = [analyze_token(t) for t in new_tokens]
    
    # Sort by score
    analyzed_tokens.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Open new positions
    logger.info(f"Found {len(analyzed_tokens)} potential tokens")
    opened = open_new_positions(wallet, analyzed_tokens, positions, cooldown)
    
    # Save state
    save_positions(positions)
    save_cooldown(cooldown)
    
    # Summary
    logger.info(f"Cycle complete: {len(opened)} opened, {len(closed)} closed")
    logger.info(f"Open positions: {len(positions.get('open', []))}/{MAX_POSITIONS}")
    
    # Calculate total PnL
    total_pnl_sol = sum(p.get("pnl_sol", 0) for p in positions.get("closed", []))
    logger.info(f"Total realized PnL: {total_pnl_sol:+.4f} SOL")

if __name__ == "__main__":
    try:
        run_trading_cycle()
    except KeyboardInterrupt:
        logger.info("Trading stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

