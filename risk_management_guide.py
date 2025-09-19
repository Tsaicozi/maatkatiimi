"""
Riskienhallinta Käyttöohje - Suositusten Implementointi
====================================================

Tämä tiedosto sisältää käyttöohjeet ja esimerkkejä riskienhallintatyökalujen käyttöön.
"""

def print_usage_guide():
    """Tulosta käyttöohje"""
    print("""
🛡️ RISKIENHALLINTA TYÖKALUJEN KÄYTTÖOHJE
========================================

Tämä paketti sisältää 5 päätyökalua riskienhallintasuositusten toteuttamiseen:

1. 📊 POSITION SIZING -KALKULAATTORI
   - Laskee optimaalisen position koon
   - Ottaa huomioon riskin ja volatiliteetin
   - Antaa suosituksia position koosta

2. 🧪 STRESS TESTING -TYÖKALU
   - Testaa portfolioa eri kriisiskenaarioissa
   - Arvioi stress-riskiä
   - Antaa suosituksia riskienhallintaan

3. 🔗 KORRELAATIOANALYYSI
   - Analysoi osakkeiden välisiä korrelaatioita
   - Arvioi diversifikaation tehokkuutta
   - Antaa suosituksia portfolio-rakenteeseen

4. 💧 LIKVIDITEETTISEURANTA
   - Seuraa osakkeiden likviditeettiä
   - Arvioi markkinavaikutuskustannuksia
   - Antaa suosituksia toteutustapaan

5. 🤖 MALLIN ARVIOINTI
   - Arvioi mallien luotettavuutta
   - Tarkistaa overfitting-riskiä
   - Antaa suosituksia mallien parantamiseen

📋 KÄYTTÖESIMERKKEJÄ
==================

1. YKSINKERTAINEN KÄYTTÖ (Dashboard):
   ```python
   from risk_management_dashboard import RiskManagementDashboard
   
   dashboard = RiskManagementDashboard(portfolio_value=100000)
   symbols = ["AAPL", "MSFT", "GOOGL"]
   results = dashboard.run_comprehensive_analysis(symbols)
   dashboard.print_summary()
   ```

2. POSITION SIZING:
   ```python
   from risk_management_tools import PositionSizingCalculator
   
   calc = PositionSizingCalculator(portfolio_value=100000)
   result = calc.calculate_position_size("AAPL", entry_price=150, stop_loss=140)
   print(f"Position koko: {result['position_size']} osaketta")
   ```

3. STRESS TESTING:
   ```python
   from risk_management_tools import StressTestingTool
   
   stress_tool = StressTestingTool()
   symbols = ["AAPL", "MSFT", "GOOGL"]
   weights = [0.33, 0.33, 0.34]
   results = stress_tool.stress_test_portfolio(symbols, weights, 100000)
   ```

4. KORRELAATIOANALYYSI:
   ```python
   from risk_management_tools import CorrelationAnalyzer
   
   analyzer = CorrelationAnalyzer()
   results = analyzer.analyze_correlations(["AAPL", "MSFT", "GOOGL"])
   ```

5. LIKVIDITEETTISEURANTA:
   ```python
   from liquidity_monitor import LiquidityMonitor
   
   monitor = LiquidityMonitor()
   results = monitor.analyze_liquidity(["AAPL", "MSFT", "GOOGL"])
   ```

6. MALLIN ARVIOINTI:
   ```python
   from model_evaluator import ModelEvaluator
   
   evaluator = ModelEvaluator()
   results = evaluator.evaluate_model_performance("AAPL")
   ```

🎯 SUOSITUKSET KÄYTTÖÖN
======================

1. ALKUUNPÄÄSEMINEN:
   - Käytä ensin dashboardia saadaksesi yleiskuvan
   - Tarkista tulokset ja suositukset
   - Implementoi suositukset vaiheittain

2. SÄÄNNÖLLINEN KÄYTTÖ:
   - Suorita analyysi kuukausittain
   - Seuraa riskimittareita
   - Mukauta strategiaa tarpeen mukaan

3. KRIISITILANTEISSA:
   - Suorita stress testing useammin
   - Tarkista likviditeetti
   - Vähennä position kokoja tarvittaessa

4. PORTFOLIO-RAKENNAN MUUTTAMINEN:
   - Käytä korrelaatioanalyysiä
   - Tarkista likviditeetti uusille osakkeille
   - Laske uudet position koot

⚠️ TÄRKEÄT HUOMIOT
=================

1. DATAN LAATU:
   - Työkalut käyttävät yfinance-dataa
   - Tarkista datan ajantasaisuus
   - Huomioi markkinoiden sulkemisajat

2. MALLIEN RAJOITUKSET:
   - Mallit ovat yksinkertaisia esimerkkejä
   - Käytä oikeita malleja tuotantokäytössä
   - Testaa malleja ennen käyttöä

3. RISKIENHALLINTA:
   - Työkalut antavat suosituksia, eivät päätöksiä
   - Harkitse kaikkia riskejä
   - Konsultoi ammattilaisia tarvittaessa

4. SÄÄNNÖLLINEN SEURANTA:
   - Markkinat muuttuvat jatkuvasti
   - Päivitä analyysit säännöllisesti
   - Mukauta strategiaa markkinatilanteen mukaan

📞 TUKI JA KEHITYS
==================

Jos kohtaat ongelmia tai haluat kehittää työkaluja:
1. Tarkista virheilmoitukset
2. Varmista, että kaikki riippuvuudet on asennettu
3. Testaa yksinkertaisilla esimerkeillä
4. Harkitse oman datan käyttöä

🚀 SEURAAVAT ASKELEET
====================

1. Testaa työkalut omalla portfoliollasi
2. Implementoi suositukset vaiheittain
3. Seuraa tuloksia ajan myötä
4. Mukauta strategiaa tarpeen mukaan
5. Harkitse lisätyökalujen kehittämistä

Onnea riskienhallintaan! 🎯
""")

def print_quick_start():
    """Tulosta nopea aloitusohje"""
    print("""
🚀 NOPEA ALOITUS - RISKIENHALLINTA
=================================

1. KÄYNNISTÄ DASHBOARD:
   python risk_management_dashboard.py

2. TAI KÄYTÄ YKSITTÄISIÄ TYÖKALUJA:
   python risk_management_tools.py
   python liquidity_monitor.py
   python model_evaluator.py

3. TARKISTA TULOKSET:
   - Katso konsoli-tulosteet
   - Tarkista tallennetut JSON-tiedostot
   - Implementoi suositukset

4. TOISTA SÄÄNNÖLLISESTI:
   - Kuukausittain tai tarpeen mukaan
   - Seuraa riskimittareita
   - Mukauta strategiaa

💡 VINKKEJÄ:
- Aloita pienellä portfoliolla
- Testaa työkalut ennen tuotantokäyttöä
- Seuraa suosituksia vaiheittain
- Konsultoi ammattilaisia tarvittaessa
""")

if __name__ == "__main__":
    print_usage_guide()
    print("\n" + "="*60)
    print_quick_start()
