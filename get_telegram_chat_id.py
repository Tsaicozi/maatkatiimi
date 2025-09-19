"""
Telegram Chat ID Haku - Yksinkertainen tapa hakea chat ID
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Ladataan API-avaimet
load_dotenv()

async def get_chat_id():
    """Hae chat ID Telegram bot:lta"""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN puuttuu .env tiedostosta!")
        print("\nLuo .env tiedosto ja lisää:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        return
    
    print("🔍 Haetaan chat ID...")
    print("📱 Lähetä ensin viesti botillesi Telegramissa!")
    print("⏳ Odota 10 sekuntia...")
    
    # Odota 10 sekuntia
    await asyncio.sleep(10)
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('ok') and data.get('result'):
                        updates = data['result']
                        
                        if updates:
                            # Hae viimeisin chat ID
                            latest_update = updates[-1]
                            chat_id = latest_update.get('message', {}).get('chat', {}).get('id')
                            
                            if chat_id:
                                print(f"✅ Chat ID löytyi: {chat_id}")
                                print(f"\n📝 Lisää tämä .env tiedostoon:")
                                print(f"TELEGRAM_CHAT_ID={chat_id}")
                                
                                # Tallenna .env tiedostoon
                                save_to_env_file(bot_token, chat_id)
                                
                            else:
                                print("❌ Chat ID ei löytynyt viesteistä")
                                print("📱 Varmista että lähetit viestin botille!")
                        else:
                            print("❌ Ei viestejä löytynyt")
                            print("📱 Lähetä viesti botillesi ja yritä uudelleen!")
                    else:
                        print("❌ Virhe API vastauksessa")
                        print(f"Vastaus: {data}")
                else:
                    print(f"❌ HTTP virhe: {response.status}")
                    error_text = await response.text()
                    print(f"Virhe: {error_text}")
                    
    except Exception as e:
        print(f"❌ Virhe: {e}")

def save_to_env_file(bot_token, chat_id):
    """Tallenna .env tiedostoon"""
    try:
        env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}

# Trading Bot Configuration
INITIAL_CAPITAL=10000.0
SCAN_INTERVAL=300
REPORT_INTERVAL=3600
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("💾 .env tiedosto päivitetty!")
        
    except Exception as e:
        print(f"❌ Virhe .env tiedoston tallentamisessa: {e}")

async def test_telegram_connection():
    """Testaa Telegram yhteys"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id:
        print("❌ API avaimet puuttuvat!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": "🧪 Testi viesti NextGen Trading Bot:lta!"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    print("✅ Telegram yhteys toimii!")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Telegram virhe: {response.status}")
                    print(f"Virhe: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Virhe: {e}")
        return False

async def main():
    """Pääfunktio"""
    print("🚀 Telegram Chat ID Haku")
    print("=" * 50)
    
    # Tarkista onko .env tiedosto olemassa
    if not os.path.exists('.env'):
        print("📝 .env tiedosto puuttuu, luodaan...")
        
        bot_token = input("Anna Telegram bot token: ").strip()
        if not bot_token:
            print("❌ Bot token vaaditaan!")
            return
        
        # Tallenna .env tiedosto
        with open('.env', 'w') as f:
            f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
        
        print("✅ .env tiedosto luotu!")
    
    # Lataa uudet arvot
    load_dotenv()
    
    # Tarkista onko chat ID jo olemassa
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if chat_id:
        print(f"📱 Chat ID löytyi: {chat_id}")
        
        # Testaa yhteys
        print("\n🧪 Testataan Telegram yhteys...")
        if await test_telegram_connection():
            print("🎉 Telegram on valmis käyttöön!")
        else:
            print("❌ Telegram yhteys ei toimi, haetaan uusi chat ID...")
            await get_chat_id()
    else:
        print("📱 Chat ID puuttuu, haetaan...")
        await get_chat_id()

if __name__ == "__main__":
    asyncio.run(main())
