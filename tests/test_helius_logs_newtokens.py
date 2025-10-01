from decimal import Decimal

import pytest

from sources.helius_logs_newtokens import HeliusTransactionsNewTokensSource

MINT_ADDRESS = "8N6gdCwChuYVEFLThQQFtJFVMvcffEyRtrpABvv9FQDW"
OWNER_ADDRESS = "8W7t3TfzFuaK7kN2YBbP54V8Mi3QFbbgqXqUsMYQRsM2"
AUTHORITY = "8Xiv8h7sGGpSGg51dcmMnoV4j3M3pCwT7w8xYzuFg8Dv"


def _make_source() -> HeliusTransactionsNewTokensSource:
    return HeliusTransactionsNewTokensSource(
        "wss://example",
        ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"],
    )


def _transaction_value(amount: str = "1000000000", *, include_initialize: bool = True) -> dict:
    initialize_instruction = {
        "program": "spl-token",
        "parsed": {
            "type": "initializeMint",
            "info": {
                "mint": MINT_ADDRESS,
                "decimals": 6,
                "mintAuthority": AUTHORITY,
                "freezeAuthority": AUTHORITY,
            },
        },
    }
    mint_to_instruction = {
        "program": "spl-token",
        "parsed": {
            "type": "mintTo",
            "info": {
                "mint": MINT_ADDRESS,
                "destination": OWNER_ADDRESS,
                "authority": AUTHORITY,
                "amount": amount,
            },
        },
    }
    instructions = [mint_to_instruction]
    if include_initialize:
        instructions.insert(0, initialize_instruction)

    return {
        "meta": {
            "preTokenBalances": [],
            "postTokenBalances": [
                {
                    "mint": MINT_ADDRESS,
                    "owner": OWNER_ADDRESS,
                    "uiTokenAmount": {
                        "amount": amount,
                        "decimals": 6,
                        "uiAmount": float(Decimal(amount) / Decimal(10**6)),
                        "uiAmountString": str(Decimal(amount) / Decimal(10**6)),
                    },
                }
            ],
        },
        "transaction": {
            "message": {
                "instructions": instructions,
            }
        },
    }


def test_extract_candidates_with_initialize_mint():
    source = _make_source()
    value = _transaction_value()

    candidates = list(source._extract_candidates(value))
    assert len(candidates) == 1

    cand = candidates[0]
    assert cand.mint == MINT_ADDRESS
    assert cand.owner == OWNER_ADDRESS
    assert cand.initialize_seen is True
    assert cand.decimals == 6
    assert pytest.approx(cand.minted_ui, rel=1e-6) == 1000.0
    assert cand.minted_raw == Decimal("1000000000")


def test_extract_candidates_without_initialize_uses_seen_guard():
    source = _make_source()
    value = _transaction_value(include_initialize=False)

    # First occurrence should still yield a candidate
    first = list(source._extract_candidates(value))
    assert len(first) == 1

    # Mark mint as seen and ensure subsequent extraction without initialize skips it
    source._seen[MINT_ADDRESS] = 0.0
    second = list(source._extract_candidates(value))
    assert second == []


def test_derive_metadata_prefers_token_info():
    source = _make_source()
    candidate = list(source._extract_candidates(_transaction_value()))[0]
    metadata = {
        "tokenInfo": {
            "name": "Sample Token",
            "symbol": "SMP",
            "decimals": 4,
        }
    }

    symbol, name, decimals = source._derive_metadata(candidate, metadata)
    assert symbol == "SMP"
    assert name == "Sample Token"
    assert decimals == 4


def test_derive_metadata_fallback_builds_defaults():
    source = _make_source()
    candidate = list(source._extract_candidates(_transaction_value()))[0]

    symbol, name, decimals = source._derive_metadata(candidate, {})
    assert symbol.startswith("TOKEN_")
    assert name == symbol
    assert decimals == candidate.decimals
