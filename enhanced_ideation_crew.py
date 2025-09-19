"""
Enhanced Ideation Crew - Toimiva sijoitusstrategia-analyysi
Yhdistää parhaat osat: reaaliaikainen data, ML-ennusteet, riskianalyysi
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import yfinance as yf
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

# Ladataan API-avaimet
load_dotenv()

# Varmistetaan API-avaimet
required_keys = ["OPENAI_API_KEY", "SERPER_API_KEY"]
missing_keys = [key for key in required_keys if key not in os.environ]
if missing_keys:
    print(f"VIRHE: Puuttuvat API-avaimet: {', '.join(missing_keys)}")
    exit()

# =============================================================================
# ENHANCED DATA STRUCTURES
# =============================================================================

@dataclass
class MarketData:
    """Strukturoitu markkinadata"""
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    volatility: Optional[float] = None
    sentiment_score: Optional[float] = None

@dataclass
class Strategy:
    """Sijoitusstrategia"""
    name: str
    description: str
    asset_class: str
    risk_level: str
    expected_return: float
    max_drawdown: float
    sharpe_ratio: float
    parameters: Dict[str, Any]
    backtest_results: Optional[Dict] = None
    confidence_score: float = 0.0

# =============================================================================
# ENHANCED TOOLS
# =============================================================================

def get_real_time_data(symbols: str, data_type: str = "price") -> str:
    """Hakee reaaliaikaista dataa"""
    try:
        symbols_list = [s.strip() for s in symbols.split(",")]
        data = {}
        
        for symbol in symbols_list:
            if data_type == "price":
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    data[symbol] = {
                        "current_price": float(hist['Close'].iloc[-1]),
                        "volume": int(hist['Volume'].iloc[-1]),
                        "change": float(hist['Close'].pct_change().iloc[-1] * 100)
                    }
        
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Virhe datan haussa: {str(e)}"

class RealTimeDataTool(BaseTool):
    """Reaaliaikainen markkinadata"""
    name: str = "real_time_data"
    description: str = "Hakee reaaliaikaista markkinadataa symbolille tai symboleille"
    
    def _run(self, symbols: str, data_type: str = "price") -> str:
        return get_real_time_data(symbols, data_type)

def technical_analysis(symbol: str, period: str = "1y") -> str:
    """Suorittaa teknistä analyysiä"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return f"Ei dataa symbolille {symbol}"
        
        # Laske teknisiä indikaattoreita
        hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
        hist['RSI'] = calculate_rsi(hist['Close'])
        
        # Analysoi signaalit
        signals = {
            "trend": "nouseva" if hist['SMA_20'].iloc[-1] > hist['SMA_50'].iloc[-1] else "laskeva",
            "rsi": "ylimyynti" if hist['RSI'].iloc[-1] > 70 else "ylimyynti" if hist['RSI'].iloc[-1] < 30 else "neutraali",
            "current_price": float(hist['Close'].iloc[-1])
        }
        
        return json.dumps({
            "symbol": symbol,
            "signals": signals,
            "indicators": {
                "sma_20": float(hist['SMA_20'].iloc[-1]),
                "sma_50": float(hist['SMA_50'].iloc[-1]),
                "rsi": float(hist['RSI'].iloc[-1])
            }
        }, indent=2)
        
    except Exception as e:
        return f"Virhe teknisesä analyysissä: {str(e)}"

def calculate_rsi(prices, period=14):
    """Laske RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class TechnicalAnalysisTool(BaseTool):
    """Tekninen analyysi"""
    name: str = "technical_analysis"
    description: str = "Suorittaa teknistä analyysiä markkinadatalle"
    
    def _run(self, symbol: str, period: str = "1y") -> str:
        return technical_analysis(symbol, period)

def ml_prediction(symbol: str, prediction_days: int = 30) -> str:
    """Ennusta tulevia hintoja"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2y")
        
        if len(hist) < 100:
            return f"Liian vähän dataa symbolille {symbol}"
        
        # Valmistele data
        features = create_features(hist)
        target = hist['Close'].shift(-1).dropna()
        
        # Poista NaN-arvot
        valid_idx = features.dropna().index.intersection(target.index)
        X = features.loc[valid_idx]
        y = target.loc[valid_idx]
        
        if len(X) < 50:
            return f"Liian vähän validia dataa symbolille {symbol}"
        
        # Kouluta malli
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Tee ennuste
        last_features = features.iloc[-1:].fillna(method='ffill')
        prediction = model.predict(last_features)[0]
        confidence = model.score(X, y)
        
        return json.dumps({
            "symbol": symbol,
            "current_price": float(hist['Close'].iloc[-1]),
            "predicted_price": float(prediction),
            "prediction_days": prediction_days,
            "confidence": float(confidence),
            "expected_return": float((prediction - hist['Close'].iloc[-1]) / hist['Close'].iloc[-1] * 100)
        }, indent=2)
        
    except Exception as e:
        return f"Virhe ML-ennusteessa: {str(e)}"

def create_features(hist):
    """Luo ominaisuuksia historiallisesta datasta"""
    features = pd.DataFrame(index=hist.index)
    
    # Hinta-ominaisuudet
    features['price_change'] = hist['Close'].pct_change()
    features['volume_change'] = hist['Volume'].pct_change()
    
    # Tekniset indikaattorit
    features['sma_5'] = hist['Close'].rolling(5).mean()
    features['sma_20'] = hist['Close'].rolling(20).mean()
    features['volatility'] = hist['Close'].rolling(20).std()
    
    # Lag-ominaisuudet
    for lag in [1, 2, 3, 5]:
        features[f'price_lag_{lag}'] = hist['Close'].shift(lag)
    
    return features

class MLPredictionTool(BaseTool):
    """Koneoppimispohjaiset ennusteet"""
    name: str = "ml_predictions"
    description: str = "Tekee koneoppimispohjaisia ennusteita markkinoiden liikkeistä"
    
    def _run(self, symbol: str, prediction_days: int = 30) -> str:
        return ml_prediction(symbol, prediction_days)

# =============================================================================
# ENHANCED AGENTS
# =============================================================================

# Alustetaan työkalut
search_tool = SerperDevTool()
realtime_tool = RealTimeDataTool()
technical_tool = TechnicalAnalysisTool()
ml_tool = MLPredictionTool()

# Agentti 1: Kehittynyt Markkina-analyytikko
enhanced_market_analyst = Agent(
    role='Senior Quantitative Market Analyst',
    goal="""Analysoi markkinatilannetta käyttäen reaaliaikaista dataa, teknistä analyysiä ja 
    koneoppimispohjaisia ennusteita. Tunnista makrotaloudelliset trendit, sektorikohtaiset mahdollisuudet 
    ja markkinoiden sentimentti. Tuota dataan perustuvia, kvantitatiivisia havaintoja.""",
    backstory="""Olet entinen Goldman Sachsin kvanttirahaston johtaja, joka on erikoistunut 
    big data -analyysiin ja algoritmiseen kaupankäyntiin. Vahvuutesi on yhdistää perinteistä 
    fundamentaalista analyysiä moderniin kvantitatiivisiin menetelmiin.""",
    verbose=True,
    allow_delegation=True,
    tools=[search_tool, realtime_tool, technical_tool, ml_tool],
    max_iter=3,
    max_execution_time=300
)

# Agentti 2: AI-Driven Strategy Architect
ai_strategist = Agent(
    role='AI-Driven Investment Strategy Architect',
    goal="""Kehitä innovatiivisia sijoitusstrategioita käyttäen koneoppimista, 
    kvantitatiivista analyysiä ja reaaliaikaista dataa. Strategiat voivat olla:
    - Multi-asset portfolio-optimointi
    - Pairs trading -strategiat
    - Momentum/mean reversion -yhdistelmät
    - Sentiment-pohjaiset strategiat""",
    backstory="""Olet entinen Renaissance Technologiesin kvanttirahaston kehittäjä, 
    joka on luonut miljardien dollarien arvoisia strategioita. Vahvuutesi on löytää 
    piilossa olevia markkinoiden tehokkuuden rikkomuksia ja hyödyntää niitä.""",
    verbose=True,
    allow_delegation=True,
    tools=[search_tool, realtime_tool, technical_tool, ml_tool],
    max_iter=5,
    max_execution_time=400
)

# Agentti 3: Advanced Risk Manager
advanced_risk_manager = Agent(
    role='Advanced Quantitative Risk Manager',
    goal="""Suorita syvällinen riskianalyysi käyttäen moniulotteisia riskimalleja:
    - Value at Risk (VaR) ja Expected Shortfall
    - Stress testing eri skenaarioille
    - Korrelaatioanalyysi ja portfolio-diversifikaatio
    - Tail risk -analyysi""",
    backstory="""Olet entinen JP Morganin Chief Risk Officer, joka on selviytynyt 
    useista finanssikriiseistä. Vahvuutesi on tunnistaa piilossa olevat riskit ja 
    kvantifioida niiden vaikutukset.""",
    verbose=True,
    allow_delegation=False,
    tools=[search_tool, realtime_tool, technical_tool],
    max_iter=3,
    max_execution_time=300
)

# =============================================================================
# ENHANCED TASKS
# =============================================================================

# Tehtävä 1: Comprehensive Market Analysis
task_comprehensive_analysis = Task(
    description="""Suorita kattava markkina-analyysi käyttäen kaikkia saatavilla olevia työkaluja:
    
    1. REAALIAIKAINEN DATA-ANALYYSI:
       - Hae reaaliaikaista dataa 10 suurimmasta osakkeesta (AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, NFLX, AMD, INTC)
       - Analysoi volyymit, volatiliteetti ja hinnanmuutokset
    
    2. TEKNINEN ANALYYSI:
       - Suorita teknistä analyysiä tärkeimmille indekseille (S&P 500, NASDAQ, BTC, ETH)
       - Tunnista trendit, tukitasot ja vastustasot
    
    3. ML-ENNUSTEET:
       - Tee 30 päivän ennusteet 5 tärkeimmälle osakkeelle
       - Laske luottamustasot ja odotetut tuotot
    
    4. MAKROTALOUDELLINEN KONTEKSTI:
       - Analysoi korot, inflaatio, työttömyys
       - Arvioi geopoliittisia riskejä
    
    Tuota strukturoitu raportti, joka sisältää kvantitatiivisia havaintoja ja ennusteita.
    
    KÄYTÄ SEURAAVIA FUNKTIOITA:
    - get_real_time_data("AAPL,MSFT,GOOGL,AMZN,TSLA")
    - technical_analysis("AAPL")
    - ml_prediction("AAPL", 30)""",
    expected_output="""Kattava markkina-analyysi, joka sisältää:
    - Reaaliaikainen data 10+ instrumentista
    - Tekniset signaalit ja trendit
    - ML-ennusteet luottamustasoineen
    - Makrotaloudellinen konteksti
    - Riskit ja mahdollisuudet""",
    agent=enhanced_market_analyst,
    max_execution_time=600
)

# Tehtävä 2: AI-Driven Strategy Development
task_ai_strategy_development = Task(
    description="""Kehitä 3 erilaista, dataan perustuvaa sijoitusstrategiaa:
    
    1. MOMENTUM-STRATEGIA:
       - Käytä ML-ennusteita tunnistaaksesi vahvat trendit
       - Optimoi position sizing riskin mukaan
    
    2. MEAN REVERSION -STRATEGIA:
       - Tunnista yli-/alimyytyjä instrumentteja
       - Käytä teknistä analyysiä entry/exit-pisteiden määrittämiseen
    
    3. PAIRS TRADING -STRATEGIA:
       - Löydä korreloivia instrumenttipareja
       - Kehitä statistiikkaan perustuva strategia
    
    Jokaiselle strategialle:
    - Suorita backtesting 1 vuoden datalla
    - Laske Sharpe ratio, max drawdown
    - Arvioi luottamustaso (1-10)""",
    expected_output="""3 yksityiskohtaista strategiaa, jokainen sisältää:
    - Strategian kuvaus ja logiikka
    - Backtesting-tulokset
    - Riskimittarit
    - Luottamustaso
    - Implementointiohjeet""",
    agent=ai_strategist,
    context=[task_comprehensive_analysis],
    max_execution_time=800
)

# Tehtävä 3: Advanced Risk Assessment
task_advanced_risk_assessment = Task(
    description="""Suorita syvällinen riskianalyysi kaikille kehitetyille strategioille:
    
    1. KVANTITATIIVINEN RISKIANALYYSI:
       - Laske VaR (95% ja 99% luottamustaso)
       - Laske Expected Shortfall
       - Analysoi tail risk -ominaisuudet
    
    2. STRESS TESTING:
       - Testaa strategioita 2008 finanssikriisin kaltaisissa olosuhteissa
       - Testaa COVID-19 kaltaisissa shokkeissa
    
    3. KORRELAATIOANALYYSI:
       - Analysoi strategioiden välistä korrelaatiota
       - Arvioi portfolio-diversifikaation hyötyjä""",
    expected_output="""Yksityiskohtainen riskiraportti, joka sisältää:
    - Kvantitatiiviset riskimittarit jokaiselle strategialle
    - Stress test -tulokset
    - Korrelaatioanalyysi
    - Risk-adjusted return -vertailu
    - Suositukset riskienhallintaan""",
    agent=advanced_risk_manager,
    context=[task_ai_strategy_development],
    max_execution_time=600
)

# =============================================================================
# ENHANCED CREW WITH MEMORY
# =============================================================================

class EnhancedCrew:
    """Kehittynyt CrewAI-tiimi muistijärjestelmällä"""
    
    def __init__(self):
        self.memory_file = "crew_memory.json"
        self.load_memory()
    
    def load_memory(self):
        """Lataa aiemmat analyysit ja oppimistiedot"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    self.memory = json.load(f)
            else:
                self.memory = {
                    "previous_analyses": [],
                    "successful_strategies": [],
                    "failed_strategies": [],
                    "market_patterns": []
                }
        except Exception as e:
            print(f"Virhe muistin lataamisessa: {e}")
            self.memory = {"previous_analyses": [], "successful_strategies": [], "failed_strategies": [], "market_patterns": []}
    
    def save_memory(self):
        """Tallenna oppimistiedot"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2, default=str)
        except Exception as e:
            print(f"Virhe muistin tallentamisessa: {e}")
    
    def add_analysis_result(self, result):
        """Lisää uusi analyysi muistiin"""
        self.memory["previous_analyses"].append({
            "timestamp": datetime.now().isoformat(),
            "result": str(result)[:500]  # Rajoitetaan pituus
        })
        # Säilytä vain 20 viimeisintä analyysiä
        if len(self.memory["previous_analyses"]) > 20:
            self.memory["previous_analyses"] = self.memory["previous_analyses"][-20:]
        self.save_memory()

# Luodaan kehittynyt tiimi
enhanced_crew = EnhancedCrew()

# Luodaan CrewAI-tiimi
crew = Crew(
    agents=[enhanced_market_analyst, ai_strategist, advanced_risk_manager],
    tasks=[task_comprehensive_analysis, task_ai_strategy_development, task_advanced_risk_assessment],
    process=Process.sequential,
    verbose=True,
    memory=True,
    planning=True
)

# =============================================================================
# EXECUTION
# =============================================================================

def run_enhanced_analysis():
    """Suorita kehittynyt analyysi"""
    print("🚀 Käynnistetään kehittynyt sijoitusstrategia-analyysi...")
    print("=" * 80)
    
    try:
        # Testaa työkalut ensin
        print("🔧 Testataan työkaluja...")
        test_data = get_real_time_data("AAPL,MSFT")
        print(f"✅ Reaaliaikainen data: {test_data[:100]}...")
        
        test_tech = technical_analysis("AAPL")
        print(f"✅ Tekninen analyysi: {test_tech[:100]}...")
        
        # Suorita analyysi
        print("\n🧠 Käynnistetään AI-agenttien analyysi...")
        result = crew.kickoff()
        
        # Tallenna tulos muistiin
        enhanced_crew.add_analysis_result(result)
        
        # Tallenna tulos tiedostoon
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"enhanced_analysis_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "analysis_result": str(result),
                "memory_context": enhanced_crew.memory
            }, f, indent=2, default=str)
        
        print(f"\n✅ Analyysi valmis! Tulos tallennettu: {output_file}")
        print("=" * 80)
        print("## KEHITTYNEET SIJOITUSSTRATEGIAT:")
        print("=" * 80)
        print(result)
        
        return result
        
    except Exception as e:
        print(f"❌ Virhe analyysissä: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Tarkista riippuvuudet
    try:
        import yfinance
        import sklearn
        print("✅ Kaikki riippuvuudet löytyvät")
    except ImportError as e:
        print(f"❌ Puuttuva riippuvuus: {e}")
        print("Asenna puuttuvat paketit: pip install yfinance scikit-learn")
        exit()
    
    # Suorita analyysi
    result = run_enhanced_analysis()
