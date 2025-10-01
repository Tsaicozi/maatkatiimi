#!/usr/bin/env python3
"""
Testaa Telegram-botin toimivuutta
"""
import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def test_telegram():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN tai TELEGRAM_CHAT_ID puuttuu .env tiedostosta")
        return False
    
    print(f"✅ Bot Token löydetty: {bot_token[:15]}...")
    print(f"✅ Chat ID löydetty: {chat_id}")
    
    # Testaa Telegram API:n kautta
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    test_message = f"""🧪 **Telegram Botti Testi**

📅 Aika: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Botti: Helius Token Scanner
✅ Yhteys toimii!

Tämä on automaattinen testiviesti."""

    payload = {
        "chat_id": chat_id,
        "text": test_message,
        "parse_mode": "Markdown"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"📡 Lähetetään testiviesti...")
            async with session.post(url, json=payload) as response:
                print(f"📊 HTTP Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Viesti lähetetty onnistuneesti!")
                    print(f"📨 Message ID: {result.get('result', {}).get('message_id')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Telegram API virhe: {response.status}")
                    print(f"Virhe: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Yhteyden testaus epäonnistui: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testataan Telegram-botin toimivuutta...")
    print("=" * 50)
    
    result = asyncio.run(test_telegram())
    
    if result:
        print("\n🎉 Telegram-botti toimii täydellisesti!")
        print("💡 Voit nyt käyttää sitä token-ilmoituksiin.")
    else:
        print("\n❌ Telegram-botti ei toimi. Tarkista asetukset.")

