import requests
import pandas as pd


def fetch_altcoin_data():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100, 'page': 1, 'sparkline': False}
    response = requests.get(url, params=params)
    return response.json()  


def select_altcoins(data):
    potential_altcoins = []
    for altcoin in data:
        # Tarkista että market_cap on olemassa ja riittävä
        if altcoin.get('market_cap', 0) >= 10_000_000:
            # CoinGecko API ei palauta 'age' kenttää, joten ohitetaan se
            # if altcoin.get('age', 0) >= 6:  # Minimum age in months
            
            # CoinGecko API ei palauta 'sector' kenttää, joten ohitetaan se
            # if 'DeFi' in altcoin.get('sector', ''):  # DeFi sector check
            
            # CoinGecko API ei palauta 'active_development' kenttää, joten ohitetaan se
            # if altcoin.get('active_development', False):
            
            # Lisätään altcoin jos se täyttää market_cap kriteerin
            potential_altcoins.append(altcoin)
    return potential_altcoins


def diversify_investments(potential_altcoins):
    investments = {}
    # Sort altcoins by market cap
    largest = sorted(potential_altcoins, key=lambda x: x['market_cap'], reverse=True)[:20]
    medium = [x for x in potential_altcoins if 10_000_000 <= x['market_cap'] < 50_000_000]
    newest = [x for x in potential_altcoins if x['market_cap'] < 10_000_000]

    investments['largest'] = min(0.2 * 0.5 / len(largest), 0.05) if largest else 0
    investments['medium'] = min(0.2 * 0.3 / len(medium), 0.05) if medium else 0
    investments['newest'] = min(0.2 * 0.2 / len(newest), 0.05) if newest else 0

    return investments


def evaluate_project(altcoin):
    criteria = ['development', 'team', 'community']
    success = sum(1 for k in criteria if altcoin[k] >= 4)  # 4 out of 5 criteria must succeed
    return success >= 4


def portfolio_review():
    """Arvioi salkun tilaa markkinoiden romahduksen aikana"""
    print("Portfolio review triggered - market crash detected!")
    # Tässä voit lisätä salkun arviointilogiikan
    return True


def perform_security_audit(altcoin):
    """Suorittaa turvallisuusauditoinnin altcoinille"""
    print(f"Performing security audit for {altcoin.get('name', 'Unknown')}")
    # Tässä voit lisätä turvallisuusauditoinnin logiikan
    return True


def detect_vulnerability(altcoin):
    """Tunnistaa haavoittuvuuksia altcoinissa"""
    print(f"Checking for vulnerabilities in {altcoin.get('name', 'Unknown')}")
    # Tässä voit lisätä haavoittuvuuksien tunnistuslogiikan
    return False  # Oletetaan että haavoittuvuuksia ei löytynyt


def notify_investors(altcoin):
    """Ilmoittaa sijoittajille haavoittuvuuksista"""
    print(f"Notifying investors about {altcoin.get('name', 'Unknown')} vulnerability")
    # Tässä voit lisätä sijoittajien ilmoituslogiikan
    return True


def check_market_crash(market):
    if market['value'] < market['value'] * 0.8:  # 20% drop
        portfolio_review()  


def assess_technological_risks(altcoin):
    perform_security_audit(altcoin)
    if detect_vulnerability(altcoin):  
        notify_investors(altcoin)


def main():
    altcoin_data = fetch_altcoin_data()
    potential_altcoins = select_altcoins(altcoin_data)
    investments = diversify_investments(potential_altcoins)
    print('Top Investments:', investments)


if __name__ == '__main__':
    main()