#!/usr/bin/env python3
"""
Portfolio Reset Script - Nollaa trading botin portfolio testausta varten
"""

import json
import os
from datetime import datetime

def reset_portfolio():
    """Nollaa portfolio ja poista vanhat analyysi tiedostot"""
    
    print("🔄 Nollataan trading botin portfolio...")
    
    # Poista vanhat analyysi tiedostot
    analysis_files = [
        f for f in os.listdir('.') 
        if f.startswith(('real_trading_analysis_', 'demo_trading_analysis_', 'final_stats_'))
    ]
    
    for file in analysis_files:
        try:
            os.remove(file)
            print(f"✅ Poistettu: {file}")
        except Exception as e:
            print(f"❌ Virhe poistettaessa {file}: {e}")
    
    # Luo uusi tyhjä portfolio
    portfolio = {
        "timestamp": datetime.now().isoformat(),
        "positions": {},
        "portfolio_value": 10000.0,
        "available_cash": 10000.0,
        "total_trades": 0,
        "successful_trades": 0,
        "total_pnl": 0.0,
        "reset_reason": "Manual reset for testing"
    }
    
    # Tallenna portfolio
    with open('portfolio_reset.json', 'w') as f:
        json.dump(portfolio, f, indent=2)
    
    print("✅ Portfolio nollattu onnistuneesti!")
    print(f"💰 Alkuperäinen portfolio: $10,000")
    print(f"💵 Käteinen: $10,000")
    print(f"📊 Positiot: 0")
    print(f"📈 PnL: $0.00")
    
    return True

if __name__ == "__main__":
    reset_portfolio()
