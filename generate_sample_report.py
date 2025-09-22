#!/usr/bin/env python3
"""
Luo esimerkkiraportti Helius Token Analysis Botista
Käyttää mock-dataa todellisten API-kutsujen sijaan
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from helius_token_analysis_bot import TokenAnalysis, AnalysisReport, ReportGenerator

HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

def create_sample_analyses():
    """Luo esimerkkianalyysejä demonstraatiota varten"""
    now = datetime.now(HELSINKI_TZ)
    
    analyses = [
        # Lupaava uusi token
        TokenAnalysis(
            mint="7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
            symbol="MOONSHOT",
            name="Moonshot Token",
            decimals=9,
            price_usd=0.000123,
            market_cap_usd=123000,
            volume_24h_usd=45000,
            price_change_24h_percent=156.7,
            liquidity_usd=87500,
            total_supply=1000000000,
            holder_count=450,
            top10_holder_share=0.35,
            concentration_risk="Matala",
            mint_authority_renounced=True,
            freeze_authority_renounced=True,
            lp_locked=True,
            lp_burned=False,
            rug_risk_score=0.15,
            security_score="Hyvä",
            unique_buyers_24h=89,
            unique_sellers_24h=23,
            trades_24h=112,
            buy_sell_ratio=3.87,
            description="Lupaava uusi DeFi token joka keskittyy yield farmingiin",
            website="https://moonshot.example.com",
            twitter="@moonshottoken",
            overall_score=0.87,
            risk_level="Matala",
            recommendation="Ostaa",
            first_seen=now - timedelta(hours=2),
            last_updated=now
        ),
        
        # Riskialtis token
        TokenAnalysis(
            mint="DangerousTokenMintAddress1234567890123456789",
            symbol="DANGER",
            name="Dangerous Token",
            decimals=6,
            price_usd=0.0001,
            market_cap_usd=10000,
            volume_24h_usd=500,
            price_change_24h_percent=-67.3,
            liquidity_usd=2500,
            total_supply=100000000000,
            holder_count=12,
            top10_holder_share=0.95,
            concentration_risk="Korkea",
            mint_authority_renounced=False,
            freeze_authority_renounced=False,
            lp_locked=False,
            lp_burned=False,
            rug_risk_score=0.85,
            security_score="Heikko",
            unique_buyers_24h=3,
            unique_sellers_24h=15,
            trades_24h=18,
            buy_sell_ratio=0.2,
            description="Epäilyttävä token - vältä!",
            overall_score=0.12,
            risk_level="Korkea",
            recommendation="Vältä",
            first_seen=now - timedelta(hours=6),
            last_updated=now
        ),
        
        # Vakaa established token
        TokenAnalysis(
            mint="So11111111111111111111111111111111111111112",
            symbol="WSOL",
            name="Wrapped SOL",
            decimals=9,
            price_usd=142.50,
            market_cap_usd=67500000000,
            volume_24h_usd=850000000,
            price_change_24h_percent=2.3,
            liquidity_usd=125000000,
            total_supply=473684210,
            holder_count=125000,
            top10_holder_share=0.25,
            concentration_risk="Matala",
            mint_authority_renounced=True,
            freeze_authority_renounced=True,
            lp_locked=True,
            lp_burned=True,
            rug_risk_score=0.05,
            security_score="Hyvä",
            unique_buyers_24h=2500,
            unique_sellers_24h=2300,
            trades_24h=4800,
            buy_sell_ratio=1.09,
            description="Solanan natiivin SOL tokenin wrapped versio",
            website="https://solana.com",
            overall_score=0.92,
            risk_level="Matala",
            recommendation="Hold",
            first_seen=now - timedelta(days=365),
            last_updated=now
        ),
        
        # Keskitason token
        TokenAnalysis(
            mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            symbol="USDC",
            name="USD Coin",
            decimals=6,
            price_usd=1.0002,
            market_cap_usd=32000000000,
            volume_24h_usd=1200000000,
            price_change_24h_percent=0.02,
            liquidity_usd=89000000,
            total_supply=32000000000,
            holder_count=89000,
            top10_holder_share=0.45,
            concentration_risk="Keskitaso",
            mint_authority_renounced=False,
            freeze_authority_renounced=False,
            lp_locked=True,
            lp_burned=False,
            rug_risk_score=0.25,
            security_score="Kohtalainen",
            unique_buyers_24h=1800,
            unique_sellers_24h=1750,
            trades_24h=3550,
            buy_sell_ratio=1.03,
            description="USD-sidottu stablecoin",
            website="https://centre.io",
            overall_score=0.78,
            risk_level="Matala",
            recommendation="Hold",
            first_seen=now - timedelta(days=200),
            last_updated=now
        ),
        
        # Uusi potentiaalinen gem
        TokenAnalysis(
            mint="NewGemTokenAddress123456789012345678901234567",
            symbol="GEM",
            name="Hidden Gem Token",
            decimals=9,
            price_usd=0.00234,
            market_cap_usd=234000,
            volume_24h_usd=15600,
            price_change_24h_percent=45.2,
            liquidity_usd=12500,
            total_supply=100000000,
            holder_count=156,
            top10_holder_share=0.55,
            concentration_risk="Keskitaso",
            mint_authority_renounced=True,
            freeze_authority_renounced=True,
            lp_locked=True,
            lp_burned=False,
            rug_risk_score=0.35,
            security_score="Kohtalainen",
            unique_buyers_24h=34,
            unique_sellers_24h=12,
            trades_24h=46,
            buy_sell_ratio=2.83,
            description="Pieni mutta kasvava gaming token",
            website="https://hiddengem.game",
            twitter="@hiddengemtoken",
            overall_score=0.68,
            risk_level="Keskitaso",
            recommendation="Harkitse",
            first_seen=now - timedelta(hours=8),
            last_updated=now
        )
    ]
    
    return analyses

async def main():
    """Luo esimerkkiraportti"""
    print("📊 Luodaan esimerkkiraportti Helius Token Analysis Botista...")
    
    # Luo esimerkkianalyysejä
    analyses = create_sample_analyses()
    
    # Luo raporttigeneroija
    class MockConfig:
        pass
    
    report_generator = ReportGenerator(MockConfig())
    
    # Luo raportti
    report = report_generator.generate_report(analyses)
    
    # Tallenna JSON-muodossa
    timestamp = datetime.now(HELSINKI_TZ).strftime('%Y%m%d_%H%M%S')
    json_path = f"reports/helius_analysis_sample_{timestamp}.json"
    text_path = f"reports/helius_analysis_sample_{timestamp}.txt"
    
    # Tallenna JSON
    report_generator.save_report_json(report, json_path)
    
    # Tallenna teksti
    report_text = report_generator.format_report_text(report)
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"✅ Esimerkkiraportti luotu:")
    print(f"   JSON: {json_path}")
    print(f"   Teksti: {text_path}")
    
    # Näytä lyhyt yhteenveto konsolissa
    print("\n" + "="*60)
    print("📋 RAPORTIN YHTEENVETO")
    print("="*60)
    print(f"🔍 Analysoituja tokeneita: {report.total_tokens_analyzed}")
    print(f"⚠️ Korkean riskin tokeneita: {report.high_risk_tokens}")
    print(f"🌟 Lupaavia tokeneita: {report.promising_tokens}")
    
    print(f"\n💹 Markkinatilanne:")
    print(f"   Keskimääräinen hinnanmuutos: {report.market_summary.get('average_price_change', 0):.1f}%")
    print(f"   Kokonaisvolyymi: ${report.market_summary.get('total_volume', 0):,.0f}")
    print(f"   Keskimääräinen likviditeetti: ${report.market_summary.get('average_liquidity', 0):,.0f}")
    
    print(f"\n🏆 Top 3 Lupaavinta:")
    for i, token in enumerate(report.most_promising[:3], 1):
        print(f"   {i}. {token.symbol} - Score: {token.overall_score:.2f} - {token.recommendation}")
    
    print(f"\n⚠️ Top 3 Riskialtteinta:")
    for i, token in enumerate(report.highest_risk[:3], 1):
        print(f"   {i}. {token.symbol} - Risk: {token.rug_risk_score:.2f} - {token.risk_level}")
    
    print(f"\n🎯 Suositukset:")
    for rec in report.recommendations:
        print(f"   - {rec}")
    
    print("\n" + "="*60)
    print("✅ Esimerkkiraportti valmis!")
    print("="*60)
    
    return report

if __name__ == "__main__":
    asyncio.run(main())