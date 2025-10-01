#!/usr/bin/env python3
"""
Test script for improved HeliusLogsNewTokensSource parser
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sources.helius_logs_newtokens import HeliusLogsNewTokensSource

def test_parser():
    """Test the improved parser with sample log data"""
    source = HeliusLogsNewTokensSource("wss://test", ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"])
    
    # Test 1: InitializeMint log with actual mint address
    logs1 = [
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]",
        "Program log: Instruction: InitializeMint",
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA consumed 1234 of 200000 compute units"
    ]
    
    mint1 = source._extract_mint_from_logs(logs1)
    print(f"Test 1 - InitializeMint (no mint in log): {mint1}")
    
    # Test 2: TransferChecked log with mint address
    logs2 = [
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]",
        "Program log: Instruction: TransferChecked",
        "Program log: Transfer 1000000 tokens",
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA consumed 5678 of 200000 compute units"
    ]
    
    mint2 = source._extract_mint_from_logs(logs2)
    print(f"Test 2 - TransferChecked (no mint in log): {mint2}")
    
    # Test 3: Log with actual mint address
    logs3 = [
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]",
        "Program log: Instruction: InitializeMint",
        "Program log: Mint: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA consumed 1234 of 200000 compute units"
    ]
    
    mint3 = source._extract_mint_from_logs(logs3)
    print(f"Test 3 - InitializeMint with mint: {mint3}")
    
    # Test 4: Accounts extraction
    log_value = {
        "accounts": ["So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"],
        "mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
        "logs": logs1
    }
    
    mint4 = source._extract_mint_from_accounts(log_value)
    print(f"Test 4 - Accounts extraction: {mint4}")
    
    # Test 5: Address validation
    valid_addr = "So11111111111111111111111111111111111111112"
    invalid_addr = "invalid_address"
    
    print(f"Test 5a - Valid address: {source._is_valid_solana_address(valid_addr)}")
    print(f"Test 5b - Invalid address: {source._is_valid_solana_address(invalid_addr)}")

if __name__ == "__main__":
    test_parser()
