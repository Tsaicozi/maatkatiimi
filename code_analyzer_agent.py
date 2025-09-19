#!/usr/bin/env python3
"""
OpenAI GPT-5 Code Analysis Agent
Analysoi hybrid trading botin koodin OpenAI GPT-5:llä
"""

import openai
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Lataa .env tiedosto
load_dotenv()

class CodeAnalyzerAgent:
    """OpenAI GPT-5 koodianalyysi agentti"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Alusta analyysi agentti"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API avain puuttuu. Aseta OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
        self.model = model
        self.analysis_results = []
        
    def analyze_code_file(self, file_path: str, analysis_type: str = "comprehensive") -> dict:
        """Analysoi yhden kooditiedoston"""
        try:
            # Lue kooditiedosto
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # Luo analyysi prompt
            prompt = self._create_analysis_prompt(code_content, analysis_type, file_path)
            
            # Lähetä OpenAI:lle
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Olet asiantuntija Python koodianalyytikko ja turvallisuusauditor."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=4000
            )
            
            analysis = response.choices[0].message.content
            print(f"    📝 Analyysi vastaus saatu: {len(analysis)} merkkiä")
            
            result = {
                "file_path": file_path,
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "model_used": self.model
            }
            
            self.analysis_results.append(result)
            return result
            
        except Exception as e:
            print(f"    ❌ Virhe analyysissä {file_path}: {e}")
            return {
                "file_path": file_path,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_analysis_prompt(self, code_content: str, analysis_type: str, file_path: str) -> str:
        """Luo analyysi prompt OpenAI:lle"""
        
        base_prompt = f"""
Analysoi seuraava Python koodi tiedostosta '{file_path}':

```python
{code_content}
```

Analysoi koodia seuraavista näkökulmista:
"""
        
        if analysis_type == "security":
            prompt = base_prompt + """
1. TURVALLISUUSONGELMAT:
   - API avaimet kova koodattuina
   - SQL injection mahdollisuudet
   - Input validointi
   - Sensitiivisten tietojen käsittely
   - Authentication/Authorization puutteet

2. VULNERABILITEETIT:
   - Koodin turvallisuusriskit
   - Mahdolliset hyökkäysvektorit
   - Parannusehdotukset

Vastaa JSON muodossa:
{
  "security_issues": ["ongelma1", "ongelma2"],
  "vulnerabilities": ["vulnerability1", "vulnerability2"],
  "recommendations": ["suositus1", "suositus2"],
  "risk_level": "HIGH/MEDIUM/LOW"
}
"""
        
        elif analysis_type == "performance":
            prompt = base_prompt + """
1. SUORITUSKYKYONGELMAT:
   - Tehottomat algoritmit
   - Muistin käyttö
   - I/O operaatiot
   - Async/await käyttö

2. OPTIMOINTIMAHDOLLISUUDET:
   - Bottlenecks
   - Parannusehdotukset
   - Best practices

Vastaa JSON muodossa:
{
  "performance_issues": ["ongelma1", "ongelma2"],
  "optimization_opportunities": ["mahdollisuus1", "mahdollisuus2"],
  "recommendations": ["suositus1", "suositus2"],
  "performance_score": "1-10"
}
"""
        
        elif analysis_type == "architecture":
            prompt = base_prompt + """
1. ARKKITEHTUURIANALYYSI:
   - Koodin rakenne
   - Design patterns
   - Separation of concerns
   - Modularity

2. KEHITYSEHDOTUKSET:
   - Refactoring mahdollisuudet
   - Best practices
   - Maintainability

Vastaa JSON muodossa:
{
  "architecture_strengths": ["vahvuus1", "vahvuus2"],
  "architecture_weaknesses": ["heikkous1", "heikkous2"],
  "refactoring_opportunities": ["mahdollisuus1", "mahdollisuus2"],
  "maintainability_score": "1-10"
}
"""
        
        else:  # comprehensive
            prompt = base_prompt + """
1. KOKONAISARVIOINTI:
   - Koodin laatu
   - Toiminnallisuus
   - Best practices

2. TURVALLISUUS:
   - API avaimet
   - Input validointi
   - Virheenkäsittely

3. SUORITUSKYKY:
   - Tehokkuus
   - Muistin käyttö
   - Optimointimahdollisuudet

4. ARKKITEHTUURI:
   - Koodin rakenne
   - Design patterns
   - Modularity

5. KEHITYSEHDOTUKSET:
   - Parannusehdotukset
   - Refactoring
   - Best practices

Vastaa strukturoidusti kunkin kategorian alle.
"""
        
        return prompt
    
    def analyze_entire_project(self, project_path: str = ".") -> dict:
        """Analysoi koko projektin"""
        project_path = Path(project_path)
        python_files = list(project_path.glob("*.py"))
        
        project_analysis = {
            "project_path": str(project_path),
            "files_analyzed": [],
            "overall_assessment": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Analysoi vain pääasialliset tiedostot
        priority_files = ['hybrid_trading_bot.py', 'real_solana_token_scanner.py', 'automatic_hybrid_bot.py', 'telegram_bot_integration.py']
        
        for py_file in python_files:
            if py_file.name.startswith('.') or py_file.name not in priority_files:
                continue
                
            print(f"🔍 Analysoidaan: {py_file.name}")
            
            # Analysoi jokainen tiedosto
            print(f"  📝 Aloitetaan analyysi tiedostolle: {py_file.name}")
            file_analysis = self.analyze_code_file(str(py_file), "comprehensive")
            print(f"  ✅ Analyysi valmis tiedostolle: {py_file.name}")
            if file_analysis:
                project_analysis["files_analyzed"].append(file_analysis)
                self.analysis_results.append(file_analysis)  # Lisää analyysi myös self.analysis_results
                print(f"  📊 Analyysi lisätty raporttiin")
            else:
                print(f"  ❌ Analyysi epäonnistui tiedostolle: {py_file.name}")
        
        # Luo kokonaisraportti
        project_analysis["overall_assessment"] = self._create_project_summary()
        
        return project_analysis
    
    def _create_project_summary(self) -> dict:
        """Luo projektin kokonaisraportti"""
        summary_prompt = f"""
Analysoi seuraavat koodianalyysi tulokset ja luo kokonaisraportti:

{json.dumps(self.analysis_results, indent=2)}

Luo yhteenveto joka sisältää:
1. KOKONAISARVIOINTI (1-10)
2. PÄÄONGELMAT (top 5)
3. SUOSITUKSET (top 5)
4. TURVALLISUUSRISKIT
5. SUORITUSKYKYONGELMAT
6. ARKKITEHTUURIONGELMAT

Vastaa JSON muodossa.
"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Olet senior software architect ja code reviewer."},
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=3000,
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {"error": f"Kokonaisraportin luonti epäonnistui: {e}"}
    
    def save_analysis_report(self, output_file: str = None) -> str:
        """Tallenna analyysi raportti"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"code_analysis_report_{timestamp}.json"
        
        report = {
            "analysis_metadata": {
                "model_used": self.model,
                "timestamp": datetime.now().isoformat(),
                "files_analyzed": len(self.analysis_results)
            },
            "detailed_analysis": self.analysis_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Analyysi raportti tallennettu: {output_file}")
        return output_file
    
    def print_summary(self):
        """Tulosta analyysi yhteenveto"""
        print("\n" + "="*80)
        print("🤖 OPENAI GPT-5 KODIANALYYSI RAPORTTI")
        print("="*80)
        
        for i, result in enumerate(self.analysis_results, 1):
            if "error" in result:
                print(f"\n❌ Tiedosto {i}: {result['file_path']}")
                print(f"   Virhe: {result['error']}")
            else:
                print(f"\n✅ Tiedosto {i}: {result['file_path']}")
                print(f"   Analyysi tyyppi: {result['analysis_type']}")
                print(f"   Malli: {result['model_used']}")
                print(f"   Aikaleima: {result['timestamp']}")
        
        print(f"\n📈 Yhteensä analysoitu: {len(self.analysis_results)} tiedostoa")
        print("="*80)


def main():
    """Pääfunktio"""
    print("🚀 Käynnistetään OpenAI GPT-5 Koodianalyysi Agentti...")
    
    try:
        # Alusta agentti
        analyzer = CodeAnalyzerAgent(model="gpt-5")
        
        # Analysoi koko projekti
        print("🔍 Analysoidaan hybrid trading bot projekti...")
        project_analysis = analyzer.analyze_entire_project()
        
        # Tallenna raportti
        report_file = analyzer.save_analysis_report()
        
        # Tulosta yhteenveto
        analyzer.print_summary()
        
        print(f"\n✅ Analyysi valmis! Raportti: {report_file}")
        
    except Exception as e:
        print(f"❌ Virhe analyysissä: {e}")
        print("\n💡 Varmista että:")
        print("   1. OPENAI_API_KEY on asetettu")
        print("   2. Sinulla on pääsy GPT-5:een")
        print("   3. Internet yhteys toimii")


if __name__ == "__main__":
    main()
