#!/usr/bin/env python3
"""
Integroitu KehitysSysteemi
Yhdistää GPT-5 koodin analysoijan ja keittäjän yhdeksi systeemiksi
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from code_analyzer_agent import CodeAnalyzerAgent
from code_chef_agent import CodeChefAgent

# Lataa .env tiedosto
load_dotenv()

class IntegratedDevelopmentSystem:
    """Integroitu kehityssysteemi joka yhdistää analysoijan ja keittäjän"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Alusta integroitu systeemi"""
        self.analyzer = CodeAnalyzerAgent(api_key=api_key, model=model)
        self.chef = CodeChefAgent(api_key=api_key, model=model)
        self.development_sessions = []
        
    async def analyze_and_improve(self, file_path: str, improvement_focus: str = None) -> dict:
        """Analysoi koodin ja paranna sitä automaattisesti"""
        try:
            print(f"🔍 Aloitetaan analyysi ja parannus: {file_path}")
            
            # 1. Analysoi nykyinen koodi
            print("📊 Vaihe 1: Analysoidaan nykyinen koodi...")
            analysis = self.analyzer.analyze_code_file(file_path, "comprehensive")
            
            if not analysis or not analysis.get('analysis'):
                return {
                    "error": "Analyysi epäonnistui",
                    "file_path": file_path,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 2. Luo parannusehdotukset analyysin perusteella
            print("💡 Vaihe 2: Luodaan parannusehdotukset...")
            improvement_suggestions = self._extract_improvement_suggestions(analysis['analysis'], improvement_focus)
            
            # 3. Paranna koodia
            print("🔧 Vaihe 3: Parannetaan koodia...")
            improvement_result = await self.chef.improve_code(file_path, improvement_suggestions)
            
            # 4. Tallenna sessio
            session = {
                "timestamp": datetime.now().isoformat(),
                "file_path": file_path,
                "improvement_focus": improvement_focus,
                "original_analysis": analysis,
                "improvement_suggestions": improvement_suggestions,
                "improvement_result": improvement_result
            }
            self.development_sessions.append(session)
            
            print("✅ Analyysi ja parannus valmis!")
            return session
            
        except Exception as e:
            print(f"❌ Virhe analyysissä ja parannuksessa: {e}")
            return {
                "error": str(e),
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_improvement_suggestions(self, analysis_text: str, focus: str = None) -> str:
        """Poimi parannusehdotukset analyysistä"""
        suggestions = []
        
        # Etsi parannusehdotuksia analyysistä
        if "KEHITYSEHDOTUKSET" in analysis_text:
            start = analysis_text.find("KEHITYSEHDOTUKSET")
            end = analysis_text.find("\n\n", start)
            if end == -1:
                end = len(analysis_text)
            suggestions.append(analysis_text[start:end])
        
        if "Parannusehdotukset" in analysis_text:
            start = analysis_text.find("Parannusehdotukset")
            end = analysis_text.find("\n\n", start)
            if end == -1:
                end = len(analysis_text)
            suggestions.append(analysis_text[start:end])
        
        # Jos ei löytynyt, käytä koko analyysiä
        if not suggestions:
            suggestions.append(analysis_text)
        
        # Lisää fokus jos annettu
        if focus:
            suggestions.append(f"\nKESKITY ERITYISESTI: {focus}")
        
        return "\n\n".join(suggestions)
    
    async def create_feature_with_analysis(self, feature_description: str, target_file: str = None) -> dict:
        """Luo uusi feature ja analysoi sen"""
        try:
            print(f"🆕 Luodaan feature ja analysoidaan: {feature_description}")
            
            # 1. Luo feature
            print("🍳 Vaihe 1: Luodaan feature...")
            feature_result = await self.chef.create_feature(feature_description, target_file)
            
            if not feature_result or feature_result.get('error'):
                return feature_result
            
            # 2. Tallenna feature väliaikaisesti
            temp_file = f"temp_feature_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            if feature_result.get('generated_code'):
                # Poimi koodi markdownista
                code_content = self._extract_code_from_markdown(feature_result['generated_code'])
                if code_content:
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    
                    # 3. Analysoi luotu feature
                    print("📊 Vaihe 2: Analysoidaan luotu feature...")
                    analysis = self.analyzer.analyze_code_file(temp_file, "comprehensive")
                    
                    # 4. Poista väliaikainen tiedosto
                    Path(temp_file).unlink()
                    
                    # 5. Tallenna sessio
                    session = {
                        "timestamp": datetime.now().isoformat(),
                        "feature_description": feature_description,
                        "target_file": target_file,
                        "feature_result": feature_result,
                        "analysis": analysis
                    }
                    self.development_sessions.append(session)
                    
                    print("✅ Feature luotu ja analysoitu!")
                    return session
            
            return feature_result
            
        except Exception as e:
            print(f"❌ Virhe feature luomisessa ja analysoinnissa: {e}")
            return {
                "error": str(e),
                "feature_description": feature_description,
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_code_from_markdown(self, markdown_content: str) -> str:
        """Poimi Python koodi markdownista"""
        lines = markdown_content.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```python'):
                in_code_block = True
                continue
            elif line.strip().startswith('```') and in_code_block:
                break
            elif in_code_block:
                code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    async def full_project_analysis_and_improvement(self, project_files: list = None) -> dict:
        """Analysoi ja paranna koko projektin"""
        try:
            print("🚀 Aloitetaan koko projektin analyysi ja parannus...")
            
            if not project_files:
                project_files = [
                    'telegram_bot_integration.py',
                    'hybrid_trading_bot.py',
                    'real_solana_token_scanner.py',
                    'automatic_hybrid_bot.py'
                ]
            
            results = []
            
            for file_path in project_files:
                if Path(file_path).exists():
                    print(f"\n📁 Käsitellään: {file_path}")
                    result = await self.analyze_and_improve(file_path)
                    results.append(result)
                else:
                    print(f"⚠️ Tiedosto ei löytynyt: {file_path}")
            
            # Tallenna projektiraportti
            project_report = {
                "timestamp": datetime.now().isoformat(),
                "project_files": project_files,
                "results": results,
                "summary": self._create_project_summary(results)
            }
            
            # Tallenna raportti
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"project_analysis_improvement_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(project_report, f, indent=2, ensure_ascii=False)
            
            print(f"\n📊 Projektiraportti tallennettu: {report_file}")
            print("✅ Koko projektin analyysi ja parannus valmis!")
            
            return project_report
            
        except Exception as e:
            print(f"❌ Virhe projektin analyysissä ja parannuksessa: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_project_summary(self, results: list) -> dict:
        """Luo projektin yhteenveto"""
        total_files = len(results)
        successful_improvements = len([r for r in results if not r.get('error')])
        errors = [r for r in results if r.get('error')]
        
        return {
            "total_files": total_files,
            "successful_improvements": successful_improvements,
            "error_count": len(errors),
            "success_rate": (successful_improvements / total_files * 100) if total_files > 0 else 0,
            "errors": errors
        }
    
    def save_development_sessions(self, output_file: str = None) -> str:
        """Tallenna kehityssessiot"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"development_sessions_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.development_sessions, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Kehityssessiot tallennettu: {output_file}")
        return output_file
    
    def print_system_summary(self):
        """Tulosta systeemin yhteenveto"""
        print("\n" + "="*80)
        print("🤖 INTEGROITU KEHITYSSYSTEEMI - YHTEENVETO")
        print("="*80)
        
        print(f"📈 Yhteensä sessioita: {len(self.development_sessions)}")
        
        for i, session in enumerate(self.development_sessions, 1):
            print(f"\n✅ Sessio {i}:")
            print(f"   Aikaleima: {session['timestamp']}")
            
            if 'file_path' in session:
                print(f"   Tiedosto: {session['file_path']}")
                print(f"   Fokus: {session.get('improvement_focus', 'Ei määritelty')}")
            elif 'feature_description' in session:
                print(f"   Feature: {session['feature_description'][:100]}...")
        
        print("\n" + "="*80)

async def main():
    """Pääfunktio"""
    print("🚀 Käynnistetään Integroitu KehitysSysteemi...")
    
    try:
        system = IntegratedDevelopmentSystem()
        
        # Esimerkki 1: Analysoi ja paranna yhtä tiedostoa
        print("\n" + "="*50)
        print("📋 ESIMERKKI 1: Analysoi ja paranna Telegram bot")
        print("="*50)
        
        result1 = await system.analyze_and_improve(
            "telegram_bot_integration.py",
            "Turvallisuus ja suorituskyky"
        )
        
        if result1 and not result1.get('error'):
            print("✅ Telegram bot analysoitu ja parannettu!")
        
        # Esimerkki 2: Luo uusi feature
        print("\n" + "="*50)
        print("📋 ESIMERKKI 2: Luo uusi feature")
        print("="*50)
        
        result2 = await system.create_feature_with_analysis(
            "Luo risk management engine joka laskee position sizing ja stop loss tasot",
            "risk_management_engine_v2.py"
        )
        
        if result2 and not result2.get('error'):
            print("✅ Risk management engine luotu ja analysoitu!")
        
        # Tallenna sessiot
        system.save_development_sessions()
        system.print_system_summary()
        
        print("\n✅ Integroitu kehityssysteemi valmis!")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")

if __name__ == "__main__":
    asyncio.run(main())
