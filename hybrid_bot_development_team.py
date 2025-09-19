#!/usr/bin/env python3
"""
Hybrid Trading Bot KehitysTiimi
Vain hybrid trading botin kehittäminen - ei muita koodeja
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from integrated_development_system import IntegratedDevelopmentSystem

# Lataa .env tiedosto
load_dotenv()

class HybridBotDevelopmentTeam:
    """Kehitystiimi joka kehittää VAIN hybrid trading botia"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Alusta hybrid bot kehitystiimi"""
        self.system = IntegratedDevelopmentSystem(api_key=api_key, model=model)
        
        # VAIN hybrid trading bot tiedostot
        self.hybrid_bot_files = [
            'hybrid_trading_bot.py',
            'real_solana_token_scanner.py', 
            'automatic_hybrid_bot.py',
            'telegram_bot_integration.py'  # Vain botin ilmoitukset
        ]
        
        # TIUKAT SÄÄNNÖT - EI TESTI TOKENIEN KÄYTTÖÄ
        self.strict_rules = {
            "NO_TEST_TOKENS": {
                "description": "KIELLETTY: Testi tokenien käyttö missään tilanteessa",
                "examples": [
                    "TEST_TOKEN", "test_token", "TestToken",
                    "DUMMY_TOKEN", "dummy_token", "DummyToken", 
                    "FAKE_TOKEN", "fake_token", "FakeToken",
                    "MOCK_TOKEN", "mock_token", "MockToken",
                    "SAMPLE_TOKEN", "sample_token", "SampleToken",
                    "DEMO_TOKEN", "demo_token", "DemoToken",
                    "UNKNOWN_TOKEN", "unknown_token", "UnknownToken",
                    "PLACEHOLDER_TOKEN", "placeholder_token", "PlaceholderToken"
                ],
                "enforcement": "Hylkää koodin jos löytyy testi tokenit"
            }
        }
        
        self.development_cycle_count = 0
        self.last_improvements = {}
        self.bot_performance_history = []
        
        print("🤖 Hybrid Trading Bot KehitysTiimi alustettu")
        print("📋 Valtuudet: VAIN hybrid trading bot kehitys")
        print("🚫 TIUKAT SÄÄNNÖT: EI TESTI TOKENIEN KÄYTTÖÄ")
        print(f"📁 Seurataan tiedostoja: {len(self.hybrid_bot_files)}")
    
    def check_forbidden_test_tokens(self, file_path):
        """Tarkista kiellettyjä testi tokeneita tiedostossa"""
        try:
            if not Path(file_path).exists():
                return True, "Tiedosto ei löydy"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().upper()  # Muutetaan isoksi kirjaimiksi
            
            # Tarkista kiellettyjä testi tokeneita
            forbidden_tokens = self.strict_rules["NO_TEST_TOKENS"]["examples"]
            found_violations = []
            
            for forbidden_token in forbidden_tokens:
                if forbidden_token.upper() in content:
                    found_violations.append(forbidden_token)
            
            if found_violations:
                print(f"🚫 KIELLETTY TESTI TOKEN LÖYTYI tiedostosta {file_path}:")
                for violation in found_violations:
                    print(f"   ❌ {violation}")
                return False, f"Kielletty testi token löytyi: {found_violations}"
            
            return True, "Ei kiellettyjä testi tokeneita"
            
        except Exception as e:
            print(f"❌ Virhe testi tokenien tarkistuksessa {file_path}: {e}")
            return False, f"Tarkistusvirhe: {e}"
    
    async def analyze_bot_performance(self):
        """Analysoi botin suorituskykyä"""
        try:
            print("📊 Analysoidaan botin suorituskykyä...")
            
            # Tarkista botin logitiedostot
            log_files = list(Path('.').glob('*hybrid*.log'))
            
            if log_files:
                latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                print(f"📝 Käytetään lokitiedostoa: {latest_log.name}")
                
                # Analysoi viimeisimmät 100 riviä
                with open(latest_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                
                # Analysoi suorituskyky
                performance_analysis = {
                    "timestamp": datetime.now().isoformat(),
                    "log_file": latest_log.name,
                    "analyzed_lines": len(recent_lines),
                    "recent_activity": recent_lines[-10:] if recent_lines else []
                }
                
                self.bot_performance_history.append(performance_analysis)
                print("✅ Botin suorituskyky analysoitu")
                
                return performance_analysis
            else:
                print("⚠️ Ei löytynyt hybrid bot lokitiedostoja")
                return None
                
        except Exception as e:
            print(f"❌ Virhe botin suorituskykyn analyysissä: {e}")
            return None
    
    async def run_hybrid_bot_development_cycle(self):
        """Suorita hybrid bot kehityssykli"""
        try:
            self.development_cycle_count += 1
            print(f"\n{'='*60}")
            print(f"🤖 HYBRID BOT KEHITYSSYKLI #{self.development_cycle_count}")
            print(f"⏰ Aloitettu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # 1. Analysoi botin suorituskykyä
            await self.analyze_bot_performance()
            
            # 2. Tarkista hybrid bot tiedostojen muutokset
            print("🔍 Vaihe 1: Tarkista hybrid bot tiedostojen muutokset...")
            changed_files = self.detect_hybrid_bot_changes()
            
            if not changed_files:
                print("📝 Ei muutoksia hybrid bot tiedostoissa, suoritetaan säännöllinen analyysi...")
                changed_files = self.hybrid_bot_files
            
            print(f"📁 Käsitellään {len(changed_files)} hybrid bot tiedostoa...")
            
            # 3. Analysoi ja paranna VAIN hybrid bot tiedostoja
            for file_path in changed_files:
                if file_path in self.hybrid_bot_files and Path(file_path).exists():
                    print(f"\n🔧 Käsitellään hybrid bot tiedosto: {file_path}")
                    
                    # ENSIN: Tarkista kiellettyjä testi tokeneita
                    print(f"🔍 Tarkistetaan kiellettyjä testi tokeneita...")
                    is_clean, check_message = self.check_forbidden_test_tokens(file_path)
                    
                    if not is_clean:
                        print(f"🚫 HYBRID BOT TIEDOSTO HYLÄTTY: {file_path}")
                        print(f"❌ Syy: {check_message}")
                        print(f"🛑 TIUKAT SÄÄNNÖT: Ei käsitellä tiedostoja joissa on testi tokeneita!")
                        continue
                    
                    print(f"✅ Testi tokenien tarkistus läpäisty: {file_path}")
                    
                    # Analysoi ja paranna hybrid bot tiedosto
                    result = await self.system.analyze_and_improve(
                        file_path,
                        improvement_focus="Hybrid trading bot optimointi ja parannus - EI TESTI TOKENIEN KÄYTTÖÄ"
                    )
                    
                    if result and not result.get('error'):
                        print(f"✅ Hybrid bot tiedosto {file_path} käsitelty onnistuneesti")
                        self.last_improvements[file_path] = datetime.now()
                    else:
                        print(f"⚠️ Hybrid bot tiedosto {file_path} käsittelyssä ongelmia")
                else:
                    print(f"🚫 Tiedosto {file_path} ei ole hybrid bot tiedosto - OHITETAAN")
            
            # 4. Tallenna hybrid bot kehityssessiot
            self.save_hybrid_bot_sessions()
            
            # 5. Tulosta hybrid bot yhteenveto
            self.print_hybrid_bot_summary()
            
        except Exception as e:
            print(f"❌ Virhe hybrid bot kehityssyklissä: {e}")
    
    def detect_hybrid_bot_changes(self):
        """Havaitse VAIN hybrid bot tiedostojen muutokset"""
        changed_files = []
        
        for file_path in self.hybrid_bot_files:
            if Path(file_path).exists():
                # Tarkista onko tiedosto muuttunut viimeisen 24 tunnin aikana
                file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                last_improvement = self.last_improvements.get(file_path, datetime.min)
                
                # Jos tiedosto on muuttunut viimeisen parannuksen jälkeen
                if file_mtime > last_improvement:
                    changed_files.append(file_path)
                    print(f"📝 Hybrid bot muutoksia havaittu: {file_path}")
        
        return changed_files
    
    def save_hybrid_bot_sessions(self):
        """Tallenna VAIN hybrid bot kehityssessiot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"hybrid_bot_development_sessions_{timestamp}.json"
            
            hybrid_sessions = []
            for session in self.system.development_sessions:
                # Tallenna vain hybrid bot liittyvät sessiot
                file_path = session.get('file_path', '')
                if any(bot_file in file_path for bot_file in self.hybrid_bot_files):
                    hybrid_sessions.append(session)
            
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(hybrid_sessions, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Hybrid bot kehityssessiot tallennettu: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Virhe hybrid bot sessioiden tallentamisessa: {e}")
    
    def print_hybrid_bot_summary(self):
        """Tulosta hybrid bot yhteenveto"""
        print(f"\n🤖 HYBRID BOT KEHITYSSYKLI #{self.development_cycle_count} - YHTEENVETO")
        print("="*60)
        
        print(f"📁 Hybrid bot tiedostoja seurattu: {len(self.hybrid_bot_files)}")
        print(f"🔧 Hybrid bot tiedostoja käsitelty: {len(self.last_improvements)}")
        
        # Tarkista kaikkien hybrid bot tiedostojen testi tokenien puhtaus
        print(f"\n🔍 Testi tokenien tarkistus:")
        all_files_clean = True
        for file_path in self.hybrid_bot_files:
            if Path(file_path).exists():
                is_clean, check_message = self.check_forbidden_test_tokens(file_path)
                status = "✅ Puhdas" if is_clean else "🚫 KIELETTY"
                print(f"   {status} {file_path}")
                if not is_clean:
                    all_files_clean = False
            else:
                print(f"   ⚠️ Ei löydy {file_path}")
        
        if all_files_clean:
            print("✅ KAIKKI HYBRID BOT TIEDOSTOT PUHTAITA - EI TESTI TOKENIEN KÄYTTÖÄ")
        else:
            print("🚫 JOITAIN HYBRID BOT TIEDOSTOJA HYLÄTTY - TESTI TOKENIEN KÄYTTÖ KIELLETTY")
        
        print(f"\n📈 Hybrid bot kehityshistoria:")
        for file_path, last_time in self.last_improvements.items():
            time_ago = datetime.now() - last_time
            hours_ago = time_ago.total_seconds() / 3600
            print(f"   ✅ {file_path}: {hours_ago:.1f}h sitten")
        
        print(f"\n💾 Hybrid bot tallennetut sessiot: {len(self.system.development_sessions)}")
        
        # Tallenna hybrid bot syklin raportti
        hybrid_cycle_report = {
            "cycle_number": self.development_cycle_count,
            "timestamp": datetime.now().isoformat(),
            "authorized_files": self.hybrid_bot_files,
            "last_improvements": {k: v.isoformat() for k, v in self.last_improvements.items()},
            "total_sessions": len(self.system.development_sessions),
            "performance_analysis": self.bot_performance_history[-1] if self.bot_performance_history else None
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"hybrid_bot_development_cycle_{timestamp}.json"
        
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(hybrid_cycle_report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Hybrid bot syklin raportti tallennettu: {report_file}")
    
    async def start_hybrid_bot_monitoring(self, cycle_interval_hours: int = 24):
        """Käynnistä hybrid bot automaattinen seuranta"""
        print("🚀 Käynnistetään Hybrid Trading Bot Automaattinen Seuranta...")
        print(f"⏰ Kehityssykli: {cycle_interval_hours} tunti")
        print(f"📋 Valtuudet: VAIN hybrid trading bot kehitys")
        print(f"📁 Seurataan tiedostoja: {len(self.hybrid_bot_files)}")
        
        while True:
            try:
                await self.run_hybrid_bot_development_cycle()
                
                # Odota seuraavaa sykliä
                next_cycle = datetime.now() + timedelta(hours=cycle_interval_hours)
                print(f"\n⏰ Seuraava hybrid bot kehityssykli: {next_cycle.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"😴 Lepää {cycle_interval_hours} tuntia...")
                
                await asyncio.sleep(cycle_interval_hours * 3600)
                
            except KeyboardInterrupt:
                print("\n🛑 Hybrid bot automaattinen seuranta pysäytetty käyttäjän toimesta")
                break
            except Exception as e:
                print(f"❌ Virhe hybrid bot seurannassa: {e}")
                print("⏰ Odotetaan 1 tunti ennen uutta yritystä...")
                await asyncio.sleep(3600)
    
    async def run_continuous_hybrid_bot_monitoring(self, check_interval_minutes: int = 60):
        """Käynnistä jatkuva hybrid bot seuranta"""
        print(f"👁️ Käynnistetään jatkuva hybrid bot seuranta ({check_interval_minutes} min välein)...")
        print("📋 Valtuudet: VAIN hybrid trading bot tiedostot")
        
        while True:
            try:
                print(f"\n🔍 Tarkistetaan hybrid bot tiedostojen muutokset... ({datetime.now().strftime('%H:%M:%S')})")
                
                changed_files = self.detect_hybrid_bot_changes()
                
                if changed_files:
                    print(f"📝 Löydettiin {len(changed_files)} muuttunutta hybrid bot tiedostoa")
                    await self.run_hybrid_bot_development_cycle()
                else:
                    print("📝 Ei muutoksia hybrid bot tiedostoissa")
                
                # Odota seuraavaa tarkistusta
                print(f"😴 Odotetaan {check_interval_minutes} minuuttia...")
                await asyncio.sleep(check_interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n🛑 Hybrid bot jatkuva seuranta pysäytetty")
                break
            except Exception as e:
                print(f"❌ Virhe hybrid bot seurannassa: {e}")
                await asyncio.sleep(300)  # 5 minuuttia

async def main():
    """Pääfunktio"""
    print("🤖 Hybrid Trading Bot KehitysTiimi")
    print("="*50)
    print("📋 VALTUUDET: VAIN hybrid trading bot kehitys")
    print("🚫 KIELETTY: Muut koodit")
    print()
    print("Valitse toiminto:")
    print("1. Suorita yksi hybrid bot kehityssykli")
    print("2. Käynnistä automaattinen hybrid bot kehitys (24h välein)")
    print("3. Käynnistä jatkuva hybrid bot seuranta (1h välein)")
    print("4. Käynnistä aktiivinen hybrid bot seuranta (15min välein)")
    
    try:
        choice = input("\nSyötä valinta (1-4): ").strip()
        
        team = HybridBotDevelopmentTeam()
        
        if choice == "1":
            await team.run_hybrid_bot_development_cycle()
        elif choice == "2":
            await team.start_hybrid_bot_monitoring(24)
        elif choice == "3":
            await team.run_continuous_hybrid_bot_monitoring(60)
        elif choice == "4":
            await team.run_continuous_hybrid_bot_monitoring(15)
        else:
            print("❌ Virheellinen valinta")
            
    except KeyboardInterrupt:
        print("\n👋 Hybrid bot kehitystiimi lopetettu!")
    except Exception as e:
        print(f"❌ Virhe: {e}")

if __name__ == "__main__":
    asyncio.run(main())
