#!/usr/bin/env python3
"""
Create a new Solana wallet and save keys
"""
from solders.keypair import Keypair
import base58

# Generate new keypair
keypair = Keypair()

# Get public key (wallet address)
public_key = str(keypair.pubkey())

# Get private key in base58 format (for Phantom/env)
private_key_bytes = bytes(keypair)
private_key_base58 = base58.b58encode(private_key_bytes).decode('ascii')

print("=" * 60)
print("🔐 NEW SOLANA WALLET CREATED")
print("=" * 60)
print()
print(f"Public Key (Wallet Address):")
print(f"  {public_key}")
print()
print(f"Private Key (Base58 - KEEP SECRET!):")
print(f"  {private_key_base58}")
print()
print("=" * 60)
print("⚠️  IMPORTANT INSTRUCTIONS:")
print("=" * 60)
print()
print("1. Copy the Private Key above")
print("2. Add it to .env2 file:")
print(f"   PHANTOM_PRIVATE_KEY={private_key_base58}")
print()
print("3. Fund this wallet with SOL:")
print(f"   - Send SOL to: {public_key}")
print("   - Recommended: 0.5-1 SOL for trading + fees")
print()
print("4. NEVER share your private key with anyone!")
print("5. This wallet is NOT recoverable with seed phrase")
print("   (save the private key securely)")
print()
print("=" * 60)

