#!/usr/bin/env python3
"""
OpenAI GPT-5 Code Chef Agent
Koodin keittäjä agentti joka toimii yhdessä analysoijan kanssa
"""

import openai
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from code_analyzer_agent import CodeAnalyzerAgent

# Lataa .env tiedosto
load_dotenv()

class CodeChefAgent:
    """OpenAI GPT-5 koodin keittäjä agentti"""
    
    def __init__(self, api_key=None, model="gpt-4"):
        """Alusta koodin keittäjä agentti"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API avain puuttuu. Aseta OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
        self.model = model
        self.analyzer = CodeAnalyzerAgent(api_key=self.api_key, model=model)
        self.development_history = []
        
    async def cook_code(self, requirements: str, target_file: str = None, context: str = None) -> dict:
        """Keitä koodia annettujen vaatimusten mukaan"""
        try:
            print(f"🍳 Aloitetaan koodin keittäminen...")
            print(f"📋 Vaatimukset: {requirements}")
            
            # Analysoi nykyinen koodi jos konteksti annettu
            analysis_context = ""
            if context and Path(context).exists():
                print(f"🔍 Analysoidaan nykyinen koodi: {context}")
                analysis = self.analyzer.analyze_code_file(context, "comprehensive")
                if analysis and analysis.get('analysis'):
                    analysis_text = analysis['analysis']
                    analysis_context = f"\n\nNYKYINEN KOODI ANALYYSI:\n{analysis_text}"
            
            # Luo keittäjä prompt
            prompt = self._create_cooking_prompt(requirements, target_file, analysis_context)
            
            # Lähetä OpenAI:lle
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Olet asiantuntija Python kehittäjä ja arkkitehti. Keität korkealaatuista, turvallista ja tehokasta koodia. Noudatat best practices ja modernia Python-kehitystä."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000
            )
            
            code_result = response.choices[0].message.content
            
            # Tallenna kehityshistoria
            cooking_record = {
                "timestamp": datetime.now().isoformat(),
                "requirements": requirements,
                "target_file": target_file,
                "context": context,
                "generated_code": code_result,
                "model_used": self.model
            }
            self.development_history.append(cooking_record)
            
            print(f"✅ Koodi keitetty onnistuneesti!")
            return cooking_record
            
        except Exception as e:
            print(f"❌ Virhe koodin keittämisessä: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "requirements": requirements
            }
    
    def _create_cooking_prompt(self, requirements: str, target_file: str = None, analysis_context: str = "") -> str:
        """Luo koodin keittäjä prompt"""
        
        prompt = f"""
KEHITÄ PYTHON KOODIA seuraavien vaatimusten mukaan:

VAATIMUKSET:
{requirements}

{'TARGET FILE: ' + target_file if target_file else ''}
{analysis_context}

OHJEET:
1. Keitä korkealaatuista, tuotantovalmista Python koodia
2. Noudata best practices: typing, error handling, logging, security
3. Käytä modernia Python 3.11+ syntaksia
4. Lisää kattavat docstringit ja kommentit
5. Implementoi proper exception handling
6. Käytä async/await kun sopii
7. Lisää type hints kaikille funktioille
8. Käytä dataclass tai Pydantic malleja kun sopii
9. Lisää logging ja monitoring
10. Implementoi retry logic ja circuit breaker patterns kun tarpeen

VASTAUS MUODOSSA:
```python
# [Täydellinen Python koodi tässä]
```

KERRO MYÖS:
- Mitä koodi tekee
- Miksi valitsit tietyn arkkitehtuurin
- Mitä best practices noudatit
- Mitä optimointeja teit
"""
        return prompt
    
    async def improve_code(self, file_path: str, improvement_suggestions: str) -> dict:
        """Paranna olemassa olevaa koodia"""
        try:
            print(f"🔧 Parannetaan koodia: {file_path}")
            
            # Analysoi nykyinen koodi
            analysis = self.analyzer.analyze_code_file(file_path, "comprehensive")
            
            # Luo parannus prompt
            prompt = f"""
PARANNA SEURAAVAA PYTHON KOODIA:

NYKYINEN KOODI (tiedosto: {file_path}):
{Path(file_path).read_text(encoding='utf-8') if Path(file_path).exists() else 'Tiedosto ei löytynyt'}

PARANNUSEHDOTUKSET:
{improvement_suggestions}

{('ANALYYSI NYKYISESTÄ KOODISTA:' + chr(10) + analysis['analysis']) if analysis and analysis.get('analysis') else ''}

OHJEET:
1. Korjaa löydetyt ongelmat
2. Implementoi parannusehdotukset
3. Säilytä nykyinen toiminnallisuus
4. Lisää parempi error handling
5. Paranna suorituskykyä
6. Lisää type hints ja dokumentaatio
7. Noudata Python best practices

VASTAUS MUODOSSA:
```python
# [Parannettu Python koodi tässä]
```

KERRO MYÖS:
- Mitä parannuksia teit
- Miksi valitsit tietyn ratkaisun
- Mitä ongelmia korjasit
"""
            
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Olet asiantuntija Python koodin parantaja. Korjaat ongelmat ja implementoit parannukset säilyttäen toiminnallisuuden."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000
            )
            
            improved_code = response.choices[0].message.content
            
            improvement_record = {
                "timestamp": datetime.now().isoformat(),
                "file_path": file_path,
                "improvement_suggestions": improvement_suggestions,
                "original_analysis": analysis,
                "improved_code": improved_code,
                "model_used": self.model
            }
            self.development_history.append(improvement_record)
            
            print(f"✅ Koodi parannettu onnistuneesti!")
            return improvement_record
            
        except Exception as e:
            print(f"❌ Virhe koodin parantamisessa: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "file_path": file_path
            }
    
    async def create_feature(self, feature_description: str, target_file: str = None) -> dict:
        """Luo uusi feature annetun kuvauksen mukaan"""
        try:
            print(f"🆕 Luodaan uusi feature: {feature_description}")
            
            prompt = f"""
LUO UUSI PYTHON FEATURE:

FEATURE KUVAUS:
{feature_description}

{'TARGET FILE: ' + target_file if target_file else ''}

OHJEET:
1. Luo täydellinen, tuotantovalmis feature
2. Käytä modernia Python arkkitehtuuria
3. Lisää kattavat testit
4. Implementoi proper error handling
5. Lisää logging ja monitoring
6. Käytä async/await kun sopii
7. Lisää type hints ja dokumentaatio
8. Käytä dependency injection kun sopii
9. Implementoi retry logic kun tarpeen
10. Lisää configuration management

VASTAUS MUODOSSA:
```python
# [Täydellinen feature koodi tässä]
```

KERRO MYÖS:
- Mitä feature tekee
- Miten se integroituu muuhun koodiin
- Mitä design patterns käytit
- Mitä best practices noudatit
"""
            
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Olet asiantuntija Python feature kehittäjä. Luot korkealaatuisia, skaalautuvia ja ylläpidettäviä featureita."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000
            )
            
            feature_code = response.choices[0].message.content
            
            feature_record = {
                "timestamp": datetime.now().isoformat(),
                "feature_description": feature_description,
                "target_file": target_file,
                "generated_code": feature_code,
                "model_used": self.model
            }
            self.development_history.append(feature_record)
            
            print(f"✅ Feature luotu onnistuneesti!")
            return feature_record
            
        except Exception as e:
            print(f"❌ Virhe feature luomisessa: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "feature_description": feature_description
            }
    
    def save_development_history(self, output_file: str = None) -> str:
        """Tallenna kehityshistoria"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"code_development_history_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.development_history, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Kehityshistoria tallennettu: {output_file}")
        return output_file
    
    def print_development_summary(self):
        """Tulosta kehitysyhteenveto"""
        print("\n" + "="*80)
        print("🍳 KODIN KEITTÄJÄ KEHDITYSYHTEENVETO")
        print("="*80)
        
        print(f"📈 Yhteensä kehitetty: {len(self.development_history)} koodia")
        
        for i, record in enumerate(self.development_history, 1):
            print(f"\n✅ Kehitys {i}:")
            print(f"   Aikaleima: {record['timestamp']}")
            print(f"   Malli: {record.get('model_used', 'N/A')}")
            
            if 'requirements' in record:
                print(f"   Vaatimukset: {record['requirements'][:100]}...")
            elif 'feature_description' in record:
                print(f"   Feature: {record['feature_description'][:100]}...")
            elif 'file_path' in record:
                print(f"   Parannettu: {record['file_path']}")
        
        print("\n" + "="*80)

async def main():
    """Pääfunktio"""
    print("🚀 Käynnistetään OpenAI GPT-5 Koodin Keittäjä Agentti...")
    
    try:
        chef = CodeChefAgent()
        
        # Esimerkki: Luo uusi feature
        feature_result = await chef.create_feature(
            "Luo Telegram bot integraatio joka tukee MarkdownV2 muotoilua ja escapettaa teksti turvallisesti",
            "telegram_bot_v2.py"
        )
        
        if feature_result and not feature_result.get('error'):
            print(f"\n🍳 Luotu feature:")
            print(f"📝 Koodi pituus: {len(feature_result.get('generated_code', ''))} merkkiä")
        
        # Esimerkki: Paranna olemassa olevaa koodia
        improvement_result = await chef.improve_code(
            "telegram_bot_integration.py",
            "Lisää Markdown-escaping, viestin pituusrajan tarkistus, ja yksi ClientSession uudelleenkäyttö"
        )
        
        if improvement_result and not improvement_result.get('error'):
            print(f"\n🔧 Parannettu koodi:")
            print(f"📝 Koodi pituus: {len(improvement_result.get('improved_code', ''))} merkkiä")
        
        # Tallenna kehityshistoria
        chef.save_development_history()
        chef.print_development_summary()
        
        print("\n✅ Koodin keittäjä agentti valmis!")
        
    except Exception as e:
        print(f"❌ Virhe: {e}")

if __name__ == "__main__":
    asyncio.run(main())
