#!/usr/bin/env python3
"""
Luo yksinkertainen esimerkkiraportti ilman ulkoisia riippuvuuksia
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Helsinki timezone (simplified)
def helsinki_now():
    return datetime.now()

@dataclass
class SimpleTokenAnalysis:
    """Yksinkertainen token-analyysi"""
    mint: str
    symbol: str
    name: str
    price_usd: float
    market_cap_usd: float
    volume_24h_usd: float
    price_change_24h_percent: float
    liquidity_usd: float
    overall_score: float
    rug_risk_score: float
    risk_level: str
    recommendation: str
    unique_buyers_24h: int
    trades_24h: int
    security_score: str
    first_seen: str
    description: str = ""

@dataclass
class SimpleReport:
    """Yksinkertainen raportti"""
    report_id: str
    generated_at: str
    total_tokens_analyzed: int
    high_risk_tokens: int
    promising_tokens: int
    top_gainers: List[SimpleTokenAnalysis]
    top_losers: List[SimpleTokenAnalysis]
    newest_tokens: List[SimpleTokenAnalysis]
    highest_risk: List[SimpleTokenAnalysis]
    most_promising: List[SimpleTokenAnalysis]
    market_summary: Dict[str, float]
    recommendations: List[str]

def create_sample_tokens():
    """Luo esimerkkitokeneita"""
    now = helsinki_now()
    
    tokens = [
        SimpleTokenAnalysis(
            mint="7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
            symbol="MOONSHOT",
            name="Moonshot Token",
            price_usd=0.000123,
            market_cap_usd=123000,
            volume_24h_usd=45000,
            price_change_24h_percent=156.7,
            liquidity_usd=87500,
            overall_score=0.87,
            rug_risk_score=0.15,
            risk_level="Matala",
            recommendation="Ostaa",
            unique_buyers_24h=89,
            trades_24h=112,
            security_score="Hyvä",
            first_seen=(now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            description="Lupaava uusi DeFi token joka keskittyy yield farmingiin"
        ),
        
        SimpleTokenAnalysis(
            mint="DangerousTokenMintAddress1234567890123456789",
            symbol="DANGER",
            name="Dangerous Token",
            price_usd=0.0001,
            market_cap_usd=10000,
            volume_24h_usd=500,
            price_change_24h_percent=-67.3,
            liquidity_usd=2500,
            overall_score=0.12,
            rug_risk_score=0.85,
            risk_level="Korkea",
            recommendation="Vältä",
            unique_buyers_24h=3,
            trades_24h=18,
            security_score="Heikko",
            first_seen=(now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            description="Epäilyttävä token - vältä!"
        ),
        
        SimpleTokenAnalysis(
            mint="So11111111111111111111111111111111111111112",
            symbol="WSOL",
            name="Wrapped SOL",
            price_usd=142.50,
            market_cap_usd=67500000000,
            volume_24h_usd=850000000,
            price_change_24h_percent=2.3,
            liquidity_usd=125000000,
            overall_score=0.92,
            rug_risk_score=0.05,
            risk_level="Matala",
            recommendation="Hold",
            unique_buyers_24h=2500,
            trades_24h=4800,
            security_score="Hyvä",
            first_seen=(now - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S"),
            description="Solanan natiivin SOL tokenin wrapped versio"
        ),
        
        SimpleTokenAnalysis(
            mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            symbol="USDC",
            name="USD Coin",
            price_usd=1.0002,
            market_cap_usd=32000000000,
            volume_24h_usd=1200000000,
            price_change_24h_percent=0.02,
            liquidity_usd=89000000,
            overall_score=0.78,
            rug_risk_score=0.25,
            risk_level="Matala",
            recommendation="Hold",
            unique_buyers_24h=1800,
            trades_24h=3550,
            security_score="Kohtalainen",
            first_seen=(now - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S"),
            description="USD-sidottu stablecoin"
        ),
        
        SimpleTokenAnalysis(
            mint="NewGemTokenAddress123456789012345678901234567",
            symbol="GEM",
            name="Hidden Gem Token",
            price_usd=0.00234,
            market_cap_usd=234000,
            volume_24h_usd=15600,
            price_change_24h_percent=45.2,
            liquidity_usd=12500,
            overall_score=0.68,
            rug_risk_score=0.35,
            risk_level="Keskitaso",
            recommendation="Harkitse",
            unique_buyers_24h=34,
            trades_24h=46,
            security_score="Kohtalainen",
            first_seen=(now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            description="Pieni mutta kasvava gaming token"
        )
    ]
    
    return tokens

def generate_report(tokens: List[SimpleTokenAnalysis]) -> SimpleReport:
    """Luo raportti tokeneista"""
    now = helsinki_now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    # Tilastot
    total_tokens = len(tokens)
    high_risk = len([t for t in tokens if t.rug_risk_score > 0.7])
    promising = len([t for t in tokens if t.overall_score > 0.7])
    
    # Lajittelu
    by_price_change = sorted(tokens, key=lambda x: x.price_change_24h_percent, reverse=True)
    by_age = sorted(tokens, key=lambda x: x.first_seen, reverse=True)
    by_risk = sorted(tokens, key=lambda x: x.rug_risk_score, reverse=True)
    by_score = sorted(tokens, key=lambda x: x.overall_score, reverse=True)
    
    # Markkinayhteenveto
    market_summary = {
        "average_price_change": sum(t.price_change_24h_percent for t in tokens) / len(tokens),
        "total_volume": sum(t.volume_24h_usd for t in tokens),
        "total_market_cap": sum(t.market_cap_usd for t in tokens),
        "average_liquidity": sum(t.liquidity_usd for t in tokens) / len(tokens)
    }
    
    # Suositukset
    recommendations = []
    if high_risk > total_tokens * 0.3:
        recommendations.append("⚠️ Korkea osuus riskialttiita tokeneita markkinoilla")
    if promising > 2:
        recommendations.append(f"✅ {promising} lupaavaa tokenia löydetty")
    if market_summary["average_price_change"] > 10:
        recommendations.append("📈 Markkinat ovat nousussa")
    elif market_summary["average_price_change"] < -10:
        recommendations.append("📉 Markkinat ovat laskussa")
    
    report = SimpleReport(
        report_id=f"helius_sample_{timestamp}",
        generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        total_tokens_analyzed=total_tokens,
        high_risk_tokens=high_risk,
        promising_tokens=promising,
        top_gainers=by_price_change[:3],
        top_losers=by_price_change[-3:],
        newest_tokens=by_age[:3],
        highest_risk=by_risk[:3],
        most_promising=by_score[:3],
        market_summary=market_summary,
        recommendations=recommendations
    )
    
    return report

def format_report_text(report: SimpleReport) -> str:
    """Muotoile raportti tekstimuotoon"""
    text = f"""
# 🔍 HELIUS TOKEN ANALYYSI RAPORTTI (ESIMERKKI)

**Raportti ID:** {report.report_id}
**Luotu:** {report.generated_at} (Helsinki)
**Analyysijakso:** 24h

## 📊 YHTEENVETO
- **Analysoituja tokeneita:** {report.total_tokens_analyzed}
- **Korkean riskin tokeneita:** {report.high_risk_tokens}
- **Lupaavia tokeneita:** {report.promising_tokens}

## 💹 MARKKINATILANNE
- **Keskimääräinen hinnanmuutos:** {report.market_summary['average_price_change']:.1f}%
- **Kokonaisvolyymi:** ${report.market_summary['total_volume']:,.0f}
- **Kokonaismarkkina-arvo:** ${report.market_summary['total_market_cap']:,.0f}
- **Keskimääräinen likviditeetti:** ${report.market_summary['average_liquidity']:,.0f}

## 🏆 TOP VOITTAJAT (24h)
"""
    
    for i, token in enumerate(report.top_gainers, 1):
        text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
        text += f"+{token.price_change_24h_percent:.1f}% "
        text += f"(${token.price_usd:.6f}) "
        text += f"Score: {token.overall_score:.2f}\n"
    
    text += f"""
## 📉 TOP HÄVIÄJÄT (24h)
"""
    
    for i, token in enumerate(report.top_losers, 1):
        text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
        text += f"{token.price_change_24h_percent:.1f}% "
        text += f"(${token.price_usd:.6f}) "
        text += f"Score: {token.overall_score:.2f}\n"
    
    text += f"""
## 🆕 UUSIMMAT TOKENIT
"""
    
    for i, token in enumerate(report.newest_tokens, 1):
        text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
        text += f"Score: {token.overall_score:.2f} "
        text += f"Risk: {token.risk_level}\n"
        text += f"   {token.description}\n"
    
    text += f"""
## ⚠️ KORKEAN RISKIN TOKENIT
"""
    
    for i, token in enumerate(report.highest_risk, 1):
        text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
        text += f"Rug Risk: {token.rug_risk_score:.2f} "
        text += f"Security: {token.security_score} "
        text += f"Rec: {token.recommendation}\n"
    
    text += f"""
## 🌟 LUPAAVIMMAT TOKENIT
"""
    
    for i, token in enumerate(report.most_promising, 1):
        text += f"{i}. **{token.symbol}** ({token.mint[:8]}...) "
        text += f"Score: {token.overall_score:.2f} "
        text += f"Liq: ${token.liquidity_usd:,.0f} "
        text += f"Rec: {token.recommendation}\n"
        text += f"   {token.description}\n"
    
    text += f"""
## 🎯 SUOSITUKSET
"""
    
    for rec in report.recommendations:
        text += f"- {rec}\n"
    
    text += f"""
## 📈 YKSITYISKOHTAINEN ANALYYSI

### Token-kohtainen yhteenveto:
"""
    
    for token in sorted(report.most_promising + report.highest_risk, key=lambda x: x.overall_score, reverse=True):
        text += f"""
**{token.symbol}** - {token.name}
- Mint: {token.mint}
- Hinta: ${token.price_usd:.6f}
- Markkina-arvo: ${token.market_cap_usd:,.0f}
- 24h Volyymi: ${token.volume_24h_usd:,.0f}
- 24h Muutos: {token.price_change_24h_percent:.1f}%
- Likviditeetti: ${token.liquidity_usd:,.0f}
- Ostajia 24h: {token.unique_buyers_24h}
- Kauppoja 24h: {token.trades_24h}
- Overall Score: {token.overall_score:.2f}/1.00
- Rug Risk: {token.rug_risk_score:.2f}/1.00
- Turvallisuus: {token.security_score}
- Suositus: {token.recommendation}
- Kuvaus: {token.description}
"""

    text += f"""
---
*Esimerkkiraportti luotu Helius Token Analysis Botilla*
*Tiedot ovat kuvitteellisia - tee oma tutkimus ennen sijoituspäätöksiä*

## 🔧 Botin Ominaisuudet

### Real-time Seuranta
- Helius WebSocket API integraatio
- Automaattinen uusien tokenien löytäminen
- Multi-source data yhdistäminen

### Kattava Analyysi
- Token metadata ja hintatiedot
- Likviditeettianalyysi ja poolien seuranta
- Holder-jakelu ja konsentraatioriski
- Turvallisuusanalyysi (authority, LP-lukitus)
- Aktiviteettimetriikat (ostajat, myyjät, kaupat)

### Automaattinen Raportointi
- Päivittäiset raportit klo 12:00 (Helsinki)
- Pyydettävät raportit milloin tahansa
- JSON ja tekstimuotoinen tallentaminen
- Top-listat ja markkinayhteenveto

### Integraatiot
- DiscoveryEngine yhteensopivuus
- Prometheus metriikat
- Telegram-ilmoitukset (tulossa)
- Systemd-palvelutuki

### Käyttöönotto
```bash
# Luo raportti heti
python run_helius_analysis.py analyze

# Käynnistä daemon-tila
python run_helius_analysis.py daemon

# Aseta cron-ajastus
./setup_cron.sh
```
"""
    
    return text

def main():
    """Luo esimerkkiraportti"""
    print("📊 Luodaan Helius Token Analysis Bot esimerkkiraportti...")
    
    # Luo esimerkkitokeneita
    tokens = create_sample_tokens()
    
    # Luo raportti
    report = generate_report(tokens)
    
    # Tallenna tiedostot
    timestamp = helsinki_now().strftime('%Y%m%d_%H%M%S')
    json_path = f"reports/helius_analysis_sample_{timestamp}.json"
    text_path = f"reports/helius_analysis_sample_{timestamp}.txt"
    
    # Varmista että reports-kansio on olemassa
    Path("reports").mkdir(exist_ok=True)
    
    # Tallenna JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    
    # Tallenna teksti
    report_text = format_report_text(report)
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"✅ Esimerkkiraportti luotu:")
    print(f"   📄 JSON: {json_path}")
    print(f"   📄 Teksti: {text_path}")
    
    # Näytä yhteenveto
    print("\n" + "="*60)
    print("📋 RAPORTIN YHTEENVETO")
    print("="*60)
    print(f"🔍 Analysoituja tokeneita: {report.total_tokens_analyzed}")
    print(f"⚠️ Korkean riskin tokeneita: {report.high_risk_tokens}")
    print(f"🌟 Lupaavia tokeneita: {report.promising_tokens}")
    
    print(f"\n💹 Markkinatilanne:")
    print(f"   Keskimääräinen hinnanmuutos: {report.market_summary['average_price_change']:.1f}%")
    print(f"   Kokonaisvolyymi: ${report.market_summary['total_volume']:,.0f}")
    
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
    print("✅ HELIUS TOKEN ANALYSIS BOT ESIMERKKIRAPORTTI VALMIS!")
    print("="*60)
    print("\n📚 Lisätietoja:")
    print("   - README: HELIUS_ANALYSIS_BOT_README.md")
    print("   - Konfiguraatio: config.yaml")
    print("   - CLI-käyttö: python run_helius_analysis.py help")
    
    return report

if __name__ == "__main__":
    main()