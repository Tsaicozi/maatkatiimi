#!/usr/bin/env python3
"""
Helius Token Analysis Bot - CLI käynnistys skripti
Käytä tätä skriptiä botin käynnistämiseen ja raporttien luomiseen.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from helius_token_analysis_bot import HeliusTokenAnalysisBot

async def run_analysis():
    """Suorita analyysi ja luo raportti"""
    print("🚀 Käynnistetään Helius Token Analysis Bot...")
    
    bot = HeliusTokenAnalysisBot()
    
    try:
        # Käynnistä botti
        await bot.start()
        
        # Luo raportti
        print("📊 Luodaan analyysi raportti...")
        report = await bot.generate_daily_report()
        
        print(f"✅ Raportti luotu: {report.report_id}")
        print(f"📈 Analysoituja tokeneita: {report.total_tokens_analyzed}")
        print(f"⚠️ Korkean riskin tokeneita: {report.high_risk_tokens}")
        print(f"🌟 Lupaavia tokeneita: {report.promising_tokens}")
        
        # Näytä lyhyt yhteenveto
        if report.most_promising:
            print("\n🏆 TOP 3 LUPAAVINTA TOKENIA:")
            for i, token in enumerate(report.most_promising[:3], 1):
                print(f"{i}. {token.symbol} - Score: {token.overall_score:.2f} - {token.recommendation}")
        
        if report.highest_risk:
            print("\n⚠️ TOP 3 RISKIALTTEINTA TOKENIA:")
            for i, token in enumerate(report.highest_risk[:3], 1):
                print(f"{i}. {token.symbol} - Risk: {token.rug_risk_score:.2f} - {token.risk_level}")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")
        return 1
    finally:
        await bot.stop()
    
    return 0

async def run_daemon():
    """Suorita botti daemon-tilassa"""
    print("🔄 Käynnistetään Helius Token Analysis Bot daemon-tilassa...")
    print("📅 Päivittäiset raportit luodaan automaattisesti klo 12:00")
    print("⏹️ Pysäytä Ctrl+C:llä")
    
    bot = HeliusTokenAnalysisBot()
    
    try:
        await bot.start()
        
        # Pysy käynnissä
        while bot.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⌨️ Keyboard interrupt - pysäytetään...")
    except Exception as e:
        print(f"❌ Virhe: {e}")
        return 1
    finally:
        await bot.stop()
    
    return 0

def main():
    """Pääfunktio CLI:lle"""
    parser = argparse.ArgumentParser(
        description="Helius Token Analysis Bot - Solana token analyysi ja raportointi"
    )
    
    parser.add_argument(
        "command",
        choices=["analyze", "daemon", "help"],
        help="Komento: analyze (luo raportti), daemon (jatkuva seuranta), help (ohje)"
    )
    
    args = parser.parse_args()
    
    if args.command == "help":
        print("""
🔍 HELIUS TOKEN ANALYSIS BOT

KOMENNOT:
  analyze  - Luo välittömästi analyysi raportti
  daemon   - Käynnistä jatkuva seuranta (päivittäiset raportit klo 12:00)
  help     - Näytä tämä ohje

ESIMERKIT:
  python run_helius_analysis.py analyze    # Luo raportti heti
  python run_helius_analysis.py daemon     # Käynnistä daemon

KONFIGURAATIO:
  Varmista että config.yaml sisältää Helius API-avaimen:
  
  io:
    rpc:
      api_key: "your-helius-api-key"
      url: "https://mainnet.helius-rpc.com/?api-key=your-key"
      ws_url: "wss://mainnet.helius-rpc.com/?api-key=your-key"

RAPORTIT:
  Raportit tallennetaan reports/ kansioon JSON ja TXT muodoissa.
  
LOGIT:
  Lokitiedosto: helius_analysis_bot.log (rotaatio 5MB, 3 varmuuskopiota)
""")
        return 0
    
    elif args.command == "analyze":
        return asyncio.run(run_analysis())
    
    elif args.command == "daemon":
        return asyncio.run(run_daemon())
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())