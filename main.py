import os
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from dotenv import load_dotenv

# Ladataan API-avaimet .env-tiedostosta
load_dotenv()

# Varmistetaan, että avaimet ovat saatavilla
if "OPENAI_API_KEY" not in os.environ:
    print("VIRHE: Varmista, että OPENAI_API_KEY on asetettu .env-tiedostoon.")
    exit()

# #####################################################################
# ## VAIHE 1: MÄÄRITTELE HYVÄKSYTTY STRATEGIA
# #####################################################################
hyvaksytty_strategia = """
### Innovatiivinen Strategia: Trendipohjainen Altcoin-Diversifikaatio

#### Strategian kuvaus
Diversifioimme sijoituksia lupaaviin altcoineihin, jotka hyötyvät Ethereumille suotuisasta markkinasuhteesta ja DeFi-trendeistä.

#### Perustelut (Miksi juuri nyt?)
Altcoin-markkinoilla on mahdollisuuksia, jotka yhdistävät innovatiiviset teknologiakehitykset ja muuttuvan sijoittajamielialan.

#### Potentiaaliset hyödyt (Pros)
- Mahdollisuus suurempiin tuottoihin altcoin-sijoitusten kautta
- Salkun hajauttaminen vähentää riskiä merkittävästi

#### Tunnistetut riskit (Cons)
- Heikkolaatuiset projektit: Huonosti suoriutuvat altcoin-projektit voivat aiheuttaa merkittäviä tappioita.
- Sijoittajien käyttäytyminen: Markkinat voivat romahtaa, jos sijoittajien luottamus heikkenee.
- Teknologiset riskit: Altcoinien teknologia voi sisältää haavoittuvuuksia.
"""

# #####################################################################
# ## VAIHE 2: LUO KUSTOMOIDUT TYÖKALUT (UUSI TAPA)
# #####################################################################

@tool("Tiedoston luku- ja kirjoitustyökalu")
def file_tool(file_path: str, mode: str = 'r', content: str = '') -> str:
    """Kirjoittaa, lukee tai lisää tekstiä tiedostoon. Käytä tätä koodin tallentamiseen ja lukemiseen.
    
    Args:
        file_path (str): Tiedoston polku.
        mode (str): 'w' (kirjoita), 'r' (lue), tai 'a' (lisää).
        content (str): Sisältö, joka kirjoitetaan tai lisätään.
    """
    try:
        if mode == 'w':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Kirjoitettiin onnistuneesti tiedostoon {file_path}."
        elif mode == 'a':
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return f"Lisättiin onnistuneesti sisältöä tiedostoon {file_path}."
        elif mode == 'r':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Virheellinen tila. Käytä 'r', 'w', tai 'a'."
    except Exception as e:
        return f"Tapahtui virhe: {e}"

# Työkalua ei tarvitse enää erikseen alustaa, se on nyt suoraan tämä funktio.

# #####################################################################
# ## VAIHE 3: MÄÄRITTELE KEHITYSTIIMIN AGENTIT
# #####################################################################

# Agentti 1: Sijoitusstrategisti
sijoitusstrategisti = Agent(
  role='Johtava sijoitusstrategisti',
  goal="""Muunna ylätason sijoitusidea yksityiskohtaiseksi tekniseksi suunnitelmaksi, 
  jota kvanttianalyytikko ja koodari voivat noudattaa.""",
  backstory="""Olet kokenut ammattilainen, joka toimii linkkinä sijoitusideoiden ja teknisen toteutuksen välillä. 
  Tehtäväsi on varmistaa, että kaikki liiketoiminnalliset vaatimukset ja logiikka on määritelty selkeästi ennen koodauksen aloittamista.""",
  verbose=True,
  allow_delegation=False,
)

# Agentti 2: Kvantitatiivinen Analyytikko
kvanttianalyytikko = Agent(
  role='Kvantitatiivinen analyytikko',
  goal="""Määrittele tarkat matemaattiset säännöt, indikaattorit ja riskienhallintaparametrit 
  annetun teknisen suunnitelman pohjalta.""",
  backstory="""Olet data-tieteilijä ja matemaatikko, joka elää ja hengittää algoritmeja. 
  Muunnat strategiset suunnitelmat kovaksi logiikaksi ja kaavoiksi, joita voidaan käyttää algoritmisessa kaupankäynnissä.""",
  verbose=True,
  allow_delegation=False,
)

# Agentti 3: Python-koodari
python_koodari = Agent(
  role='Senior Python-kehittäjä',
  goal="""Kirjoita puhdasta, tehokasta ja dokumentoitua Python-koodia perustuen kvanttianalyytikon antamiin sääntöihin. 
  Tallenna valmis koodi tiedostoon.""",
  backstory="""Olet erikoistunut fintech- ja algoritmiseen kaupankäyntiin. 
  Osaat rakentaa luotettavia ja nopeita botteja, jotka toivat vaativissa markkinaolosuhteissa. 
  Käytät aina parhaita koodauskäytäntöjä.""",
  verbose=True,
  allow_delegation=False,
  tools=[file_tool]
)

# Agentti 4: Koodin Tarkastaja
koodin_tarkastaja = Agent(
  role='Laadunvarmistuksen ja koodin tarkastaja',
  goal="""Tarkasta Python-koodarin tuottama koodi. Etsi bugeja, logiikkavirheitä, 
  potentiaalisia riskejä ja varmista, että koodi noudattaa alkuperäistä suunnitelmaa.""",
  backstory="""Olet äärimmäisen tarkka ja huolellinen kehittäjä, jonka silmä löytää pienimmätkin virheet. 
  Tehtäväsi on varmistaa, että tuotantoon menevä koodi on virheetöntä ja turvallista.""",
  verbose=True,
  allow_delegation=False,
  tools=[file_tool]
)

# #####################################################################
# ## VAIHE 4: MÄÄRITTELE KEHITYSTIMIN TEHTÄVÄT
# #####################################################################

task_define_specs = Task(
  description=f"""Ota tämä hyväksytty sijoitusstrategia ja muunna se yksityiskohtaiseksi tekniseksi suunnitelmaksi.
  
  HYVÄKSYTTY STRATEGIA:
  ---
  {hyvaksytty_strategia}
  ---
  
  Teknisen suunnitelman tulee sisältää:
  1. Kriteerit lupaavien altcoinien tunnistamiseksi (esim. markkina-arvo, projektin ikä, DeFi-sektori).
  2. Tarkat säännöt sijoitusten hajauttamiselle ja position koolle.
  3. Selkeä riskienhallintasuunnitelma jokaista riskiä (heikkolaatuiset projektit, markkinaromahdus, teknologiset riskit) varten.""",
  expected_output="Yksityiskohtainen tekninen dokumentti, jonka pohjalta kvanttianalyytikko voi jatkaa.",
  agent=sijoitusstrategisti
)

task_develop_logic = Task(
  description="""Ota tekninen suunnitelma ja määrittele sen pohjalta tarkka matemaattinen ja algoritminen logiikka.
  Määrittele, miten potentiaaliset altcoinit pisteytetään ja valitaan. Määrittele käytettävät kirjastot ja API-rajapinnat datan hakuun.""",
  expected_output="Dokumentti, joka sisältää pseudokoodin, tarvittavat kirjastot ja tarkat algoritmiset säännöt altcoinien valintaan ja salkunhallintaan.",
  agent=kvanttianalyytikko,
  context=[task_define_specs]
)

task_write_code = Task(
  description="""Kirjoita täydellinen, toimiva Python-skripti perustuen kvanttianalyytikon logiikkaan.
  Skriptin tulee pystyä hakemaan dataa, analysoimaan altcoineja annettujen sääntöjen mukaan ja tulostamaan top 5 -lista sijoituskohteista.
  **Tallenna lopullinen koodi tiedostoon nimeltä `trading_bot.py` käyttäen tiedostotyökalua.**""",
  expected_output="Vahvistus siitä, että täydellinen Python-skripti on tallennettu tiedostoon `trading_bot.py`.",
  agent=python_koodari,
  context=[task_develop_logic]
)

task_review_code = Task(
  description="""**Lue ja analysoi `trading_bot.py`-tiedoston sisältö.**
  Tarkasta koodi huolellisesti. Varmista, että altcoinien valintakriteerit ja riskienhallinta on toteutettu oikein.
  Etsi mahdollisia bugeja, logiikkavirheitä tai poikkeamia alkuperäisestä suunnitelmasta.
  Anna kattava palaute ja listaa kaikki löytämäsi ongelmat ja parannusehdotukset.""",
  expected_output="Kattava koodikatselmointiraportti, jossa on selkeät havainnot ja korjausehdotukset.",
  agent=koodin_tarkastaja,
  context=[task_write_code]
)

# #####################################################################
# ## VAIHE 5: KOKOA KEHITYSTIIMI JA KÄYNNISTÄ
# #####################################################################

kehitystiimi = Crew(
  agents=[sijoitusstrategisti, kvanttianalyytikko, python_koodari, koodin_tarkastaja],
  tasks=[task_define_specs, task_develop_logic, task_write_code, task_review_code],
  process=Process.sequential,
  verbose=True
)

# Käynnistetään tiimin työ!
result = kehitystiimi.kickoff()

print("\n\n########################")
print("## KEHITYSPROSESSIN LOPPUTULOS (KOODIKATSELMOINTI):")
print("########################\n")
print(result)

print("\n\n########################")
print("## MUISTA TARKISTAA LUOTU TIEDOSTO: trading_bot.py")
print("########################\n")


