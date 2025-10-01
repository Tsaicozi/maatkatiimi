#!/usr/bin/env python3
"""
Demo Trading Configuration
Kokeellinen demo tili 1000$ kassalla
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

class DemoTradingConfig:
    """Demo trading configuration with $1000 starting capital"""
    
    def __init__(self):
        self.config_file = "demo_trading_config.json"
        self.load_config()
    
    def load_config(self):
        """Load or create demo trading configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ Loaded existing demo config: ${self.config['portfolio_value']:.2f} capital")
            except Exception as e:
                print(f"❌ Error loading config: {e}")
                self.create_default_config()
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """Create default demo trading configuration"""
        self.config = {
            "demo_mode": True,
            "portfolio_value": 1000.0,  # $1000 starting capital
            "max_positions": 3,  # Max 3 positions for demo
            "risk_per_trade": 0.05,  # 5% risk per trade (higher for demo)
            "max_allocation_pct": 0.10,  # 10% max allocation per trade
            "stop_loss_pct": 0.20,  # 20% stop loss
            "take_profit_1_pct": 0.50,  # 50% take profit 1
            "take_profit_2_pct": 1.00,  # 100% take profit 2
            "trailing_stop_pct": 0.15,  # 15% trailing stop
            "dry_run": True,  # Always dry run for demo
            "created_at": datetime.now(timezone.utc).isoformat(),
            "trading_enabled": True,
            "demo_account_id": f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "initial_balance": 1000.0,
            "current_balance": 1000.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0
        }
        self.save_config()
        print(f"🎯 Created new demo account: {self.config['demo_account_id']}")
        print(f"💰 Starting capital: ${self.config['portfolio_value']:.2f}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for demo trading"""
        return {
            "TRADING_ENABLED": "true",
            "TRADING_DRY_RUN": "true",
            "TRADING_PORTFOLIO_VALUE": str(self.config["portfolio_value"]),
            "TRADING_MAX_POSITIONS": str(self.config["max_positions"]),
            "TRADING_RISK_PER_TRADE": str(self.config["risk_per_trade"]),
            "TRADING_MAX_ALLOCATION_PCT": str(self.config["max_allocation_pct"]),
            "TRADING_STOP_LOSS_PCT": str(self.config["stop_loss_pct"]),
            "TRADING_TAKE_PROFIT_1_PCT": str(self.config["take_profit_1_pct"]),
            "TRADING_TAKE_PROFIT_2_PCT": str(self.config["take_profit_2_pct"]),
            "TRADING_TRAILING_STOP_PCT": str(self.config["trailing_stop_pct"]),
            "DEMO_MODE": "true",
            "DEMO_ACCOUNT_ID": self.config["demo_account_id"]
        }
    
    def update_stats(self, trade_result: Dict[str, Any]):
        """Update demo trading statistics"""
        self.config["total_trades"] += 1
        self.config["total_pnl"] += trade_result.get("pnl", 0.0)
        self.config["current_balance"] = self.config["initial_balance"] + self.config["total_pnl"]
        
        if trade_result.get("pnl", 0) > 0:
            self.config["winning_trades"] += 1
        else:
            self.config["losing_trades"] += 1
        
        # Calculate win rate
        if self.config["total_trades"] > 0:
            self.config["win_rate"] = self.config["winning_trades"] / self.config["total_trades"]
        
        # Update max drawdown
        current_drawdown = max(0, self.config["initial_balance"] - self.config["current_balance"])
        self.config["max_drawdown"] = max(self.config["max_drawdown"], current_drawdown)
        
        self.save_config()
    
    def get_stats_summary(self) -> str:
        """Get demo trading statistics summary"""
        return f"""
📊 DEMO TRADING STATISTICS

Account ID: {self.config['demo_account_id']}
Initial Balance: ${self.config['initial_balance']:.2f}
Current Balance: ${self.config['current_balance']:.2f}
Total PnL: ${self.config['total_pnl']:.2f} ({self.config['total_pnl']/self.config['initial_balance']*100:.1f}%)

Trades: {self.config['total_trades']}
Winning: {self.config['winning_trades']}
Losing: {self.config['losing_trades']}
Win Rate: {self.config['win_rate']*100:.1f}%

Max Drawdown: ${self.config['max_drawdown']:.2f}
Risk per Trade: {self.config['risk_per_trade']*100:.1f}%
Max Positions: {self.config['max_positions']}
"""

def setup_demo_trading():
    """Setup demo trading configuration"""
    config = DemoTradingConfig()
    
    # Set environment variables
    env_vars = config.get_env_vars()
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("🎯 Demo Trading Setup Complete!")
    print(config.get_stats_summary())
    
    return config

if __name__ == "__main__":
    setup_demo_trading()
