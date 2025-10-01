#!/usr/bin/env python3
"""
Crypto Screener Daemon - Pidä botti käynnissä jatkuvasti
"""
import os
import time
import subprocess
import signal
import sys
from datetime import datetime

class CryptoDaemon:
    def __init__(self, script_path="crypto_new_token_screener_v3.py", interval_minutes=30):
        self.script_path = script_path
        self.interval_seconds = interval_minutes * 60
        self.running = True
        self.process = None
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        print(f"\n[{datetime.now()}] Received signal {signum}, shutting down...")
        self.running = False
        if self.process:
            self.process.terminate()
        sys.exit(0)
    
    def run_screener(self):
        """Suorita crypto screener skripti"""
        try:
            print(f"[{datetime.now()}] Starting crypto screener...")
            result = subprocess.run(
                ["python3", self.script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            
            if result.returncode == 0:
                print(f"[{datetime.now()}] Screener completed successfully")
            else:
                print(f"[{datetime.now()}] Screener failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
            
            # Tulosta viimeiset rivit outputista
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[-3:]:  # Viimeiset 3 riviä
                    if line.strip():
                        print(f"[{datetime.now()}] {line}")
                        
        except subprocess.TimeoutExpired:
            print(f"[{datetime.now()}] Screener timed out after 5 minutes")
        except Exception as e:
            print(f"[{datetime.now()}] Error running screener: {e}")
    
    def run(self):
        """Pääsilmukka"""
        print(f"[{datetime.now()}] Crypto Screener Daemon started")
        print(f"[{datetime.now()}] Script: {self.script_path}")
        print(f"[{datetime.now()}] Interval: {self.interval_seconds // 60} minutes")
        print(f"[{datetime.now()}] Press Ctrl+C to stop")
        
        while self.running:
            try:
                self.run_screener()
                
                if self.running:
                    print(f"[{datetime.now()}] Waiting {self.interval_seconds // 60} minutes until next run...")
                    time.sleep(self.interval_seconds)
                    
            except KeyboardInterrupt:
                print(f"\n[{datetime.now()}] Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                print(f"[{datetime.now()}] Unexpected error: {e}")
                print(f"[{datetime.now()}] Continuing in 5 minutes...")
                time.sleep(300)  # 5 min error recovery
        
        print(f"[{datetime.now()}] Crypto Screener Daemon stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crypto Screener Daemon")
    parser.add_argument("--script", default="crypto_new_token_screener_v3.py", help="Script to run")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes")
    args = parser.parse_args()
    
    daemon = CryptoDaemon(args.script, args.interval)
    daemon.run()

