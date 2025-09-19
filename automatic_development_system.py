#!/usr/bin/env python3
"""
Automaattinen KehitysSysteemi
Täysin automaattinen GPT-5 kehitysympäristö
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from integrated_development_system import IntegratedDevelopmentSystem

# Lataa .env tiedosto
load_dotenv()

class AutomaticDevelopmentSystem:
    """Täysin automaattinen kehityssysteemi"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Alusta automaattinen systeemi"""
        self.system = IntegratedDevelopmentSystem(api_key=api_key, model=model)
        self.monitored_files = [
            'telegram_bot_integration.py',
            'hybrid_trading_bot.py',
            'real_solana_token_scanner.py',
            'automatic_hybrid_bot.py'
        ]
        self.development_cycle_count = 0
        self.last_improvements = {}
        
    async def start_automatic_development(self, cycle_interval_hours: int = 24):
        """Käynnistä automaattinen kehityssykli"""
        print("🚀 Käynnistetään Automaattinen KehitysSysteemi...")
        print(f"⏰ Kehityssykli: {cycle_interval_hours} tunti")
        print(f"📁 Seurataan tiedostoja: {len(self.monitored_files)}")
        
        while True:
            try:
                self.development_cycle_count += 1
                print(f"\n{'='*60}")
                print(f"🔄 KEHITYSSYKLI #{self.development_cycle_count}")
                print(f"⏰ Aloitettu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Suorita automaattinen analyysi ja parannus
                await self.run_development_cycle()
                
                # Odota seuraavaa sykliä
                next_cycle = datetime.now() + timedelta(hours=cycle_interval_hours)
                print(f"\n⏰ Seuraava kehityssykli: {next_cycle.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"😴 Lepää {cycle_interval_hours} tuntia...")
                
                await asyncio.sleep(cycle_interval_hours * 3600)  # Muunna tunneiksi sekunneiksi
                
            except KeyboardInterrupt:
                print("\n🛑 Automaattinen kehityssysteemi pysäytetty käyttäjän toimesta")
                break
            except Exception as e:
                print(f"❌ Virhe kehityssyklissä: {e}")
                print("⏰ Odotetaan 1 tunti ennen uutta yritystä...")
                await asyncio.sleep(3600)  # 1 tunti
    
    async def run_development_cycle(self):
        """Suorita yksi kehityssykli"""
        try:
            print("🔍 Vaihe 1: Tarkista tiedostojen muutokset...")
            changed_files = self.detect_file_changes()
            
            if not changed_files:
                print("📝 Ei muutoksia tiedostoissa, suoritetaan säännöllinen analyysi...")
                changed_files = self.monitored_files
            
            print(f"📁 Käsitellään {len(changed_files)} tiedostoa...")
            
            for file_path in changed_files:
                if Path(file_path).exists():
                    print(f"\n🔧 Käsitellään: {file_path}")
                    
                    # Analysoi ja paranna tiedosto
                    result = await self.system.analyze_and_improve(
                        file_path,
                        improvement_focus="Automaattinen säännöllinen parannus"
                    )
                    
                    if result and not result.get('error'):
                        print(f"✅ {file_path} käsitelty onnistuneesti")
                        self.last_improvements[file_path] = datetime.now()
                    else:
                        print(f"⚠️ {file_path} käsittelyssä ongelmia")
                else:
                    print(f"⚠️ Tiedosto ei löytynyt: {file_path}")
            
            # Tallenna kehityssessiot
            self.system.save_development_sessions()
            
            # Tulosta yhteenveto
            self.print_cycle_summary()
            
        except Exception as e:
            print(f"❌ Virhe kehityssyklissä: {e}")
    
    def detect_file_changes(self):
        """Havaitse tiedostojen muutokset"""
        changed_files = []
        
        for file_path in self.monitored_files:
            if Path(file_path).exists():
                # Tarkista onko tiedosto muuttunut viimeisen 24 tunnin aikana
                file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                last_improvement = self.last_improvements.get(file_path, datetime.min)
                
                # Jos tiedosto on muuttunut viimeisen parannuksen jälkeen
                if file_mtime > last_improvement:
                    changed_files.append(file_path)
                    print(f"📝 Muutoksia havaittu: {file_path}")
        
        return changed_files
    
    def print_cycle_summary(self):
        """Tulosta syklin yhteenveto"""
        print(f"\n📊 KEHITYSSYKLI #{self.development_cycle_count} - YHTEENVETO")
        print("="*50)
        
        print(f"📁 Seurattu tiedostoja: {len(self.monitored_files)}")
        print(f"🔧 Käsitelty tiedostoja: {len(self.last_improvements)}")
        
        print(f"\n📈 Kehityshistoria:")
        for file_path, last_time in self.last_improvements.items():
            time_ago = datetime.now() - last_time
            hours_ago = time_ago.total_seconds() / 3600
            print(f"   ✅ {file_path}: {hours_ago:.1f}h sitten")
        
        print(f"\n💾 Tallennetut sessiot: {len(self.system.development_sessions)}")
        
        # Tallenna syklin raportti
        cycle_report = {
            "cycle_number": self.development_cycle_count,
            "timestamp": datetime.now().isoformat(),
            "monitored_files": self.monitored_files,
            "last_improvements": {k: v.isoformat() for k, v in self.last_improvements.items()},
            "total_sessions": len(self.system.development_sessions)
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"automatic_development_cycle_{timestamp}.json"
        
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(cycle_report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Syklin raportti tallennettu: {report_file}")
    
    async def run_single_cycle(self):
        """Suorita yksi kehityssykli ilman automaattista toistoa"""
        print("🚀 Suoritetaan yksi automaattinen kehityssykli...")
        
        self.development_cycle_count += 1
        print(f"\n{'='*60}")
        print(f"🔄 KEHITYSSYKLI #{self.development_cycle_count}")
        print(f"⏰ Aloitettu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        await self.run_development_cycle()
        
        print("\n✅ Automaattinen kehityssykli valmis!")
    
    async def run_continuous_monitoring(self, check_interval_minutes: int = 60):
        """Käynnistä jatkuva tiedostojen seuranta"""
        print(f"👁️ Käynnistetään jatkuva seuranta ({check_interval_minutes} min välein)...")
        
        while True:
            try:
                print(f"\n🔍 Tarkistetaan tiedostojen muutokset... ({datetime.now().strftime('%H:%M:%S')})")
                
                changed_files = self.detect_file_changes()
                
                if changed_files:
                    print(f"📝 Löydettiin {len(changed_files)} muuttunutta tiedostoa")
                    
                    # Käynnistä kehityssykli
                    await self.run_single_cycle()
                else:
                    print("📝 Ei muutoksia tiedostoissa")
                
                # Odota seuraavaa tarkistusta
                print(f"😴 Odotetaan {check_interval_minutes} minuuttia...")
                await asyncio.sleep(check_interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n🛑 Jatkuva seuranta pysäytetty")
                break
            except Exception as e:
                print(f"❌ Virhe seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia

async def main():
    """Pääfunktio"""
    print("🤖 Automaattinen KehitysSysteemi")
    print("="*40)
    print("Valitse toiminto:")
    print("1. Suorita yksi kehityssykli")
    print("2. Käynnistä automaattinen kehitys (24h välein)")
    print("3. Käynnistä jatkuva seuranta (1h välein)")
    print("4. Käynnistä jatkuva seuranta (15min välein)")
    
    try:
        choice = input("\nSyötä valinta (1-4): ").strip()
        
        system = AutomaticDevelopmentSystem()
        
        if choice == "1":
            await system.run_single_cycle()
        elif choice == "2":
            await system.start_automatic_development(24)
        elif choice == "3":
            await system.run_continuous_monitoring(60)
        elif choice == "4":
            await system.run_continuous_monitoring(15)
        else:
            print("❌ Virheellinen valinta")
            
    except KeyboardInterrupt:
        print("\n👋 Hei!")
    except Exception as e:
        print(f"❌ Virhe: {e}")

if __name__ == "__main__":
    asyncio.run(main())
