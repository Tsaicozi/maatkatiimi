#!/usr/bin/env python3
"""
Telegram Chat ID hakija
Käytä tätä ohjelmaa selvittääksesi Telegram chat ID:n
"""

import asyncio
import aiohttp
import json
from dotenv import load_dotenv
import os

load_dotenv()

async def get_chat_id():
    """Hae Telegram chat ID"""
    
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        token = input("Anna Telegram bot token: ").strip()
    
    if not token:
        print("❌ Token vaaditaan")
        return
    
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        
        print("🔍 Haetaan viimeisimmät viestit...")
        print("💬 Lähetä viesti botille Telegramissa nyt!")
        print("⏳ Odotetaan 10 sekuntia...")
        
        await asyncio.sleep(10)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("ok") and data.get("result"):
                        updates = data["result"]
                        
                        if not updates:
                            print("❌ Ei viestejä löytynyt")
                            print("💡 Varmista että lähetit viestin botille")
                            return
                        
                        print(f"✅ Löydettiin {len(updates)} viestiä")
                        print("\n📋 Chat ID:t:")
                        
                        chat_ids = set()
                        for update in updates:
                            if "message" in update:
                                chat = update["message"]["chat"]
                                chat_id = chat["id"]
                                chat_type = chat["type"]
                                
                                if chat_type == "private":
                                    first_name = chat.get("first_name", "")
                                    last_name = chat.get("last_name", "")
                                    username = chat.get("username", "")
                                    name = f"{first_name} {last_name}".strip()
                                    if username:
                                        name += f" (@{username})"
                                    print(f"  👤 Private: {chat_id} - {name}")
                                else:
                                    title = chat.get("title", "Unknown")
                                    print(f"  👥 Group: {chat_id} - {title}")
                                
                                chat_ids.add(chat_id)
                        
                        if len(chat_ids) == 1:
                            chat_id = list(chat_ids)[0]
                            print(f"\n✅ Käytä tätä chat ID:ta: {chat_id}")
                            print(f"📝 Lisää .env tiedostoon: TELEGRAM_CHAT_ID={chat_id}")
                        else:
                            print(f"\n💡 Valitse sopiva chat ID yllä olevasta listasta")
                    
                    else:
                        print("❌ Ei viestejä löytynyt")
                        print("💡 Varmista että:")
                        print("  - Bot token on oikein")
                        print("  - Lähetit viestin botille")
                        print("  - Bot on käynnissä")
                
                else:
                    error_text = await response.text()
                    print(f"❌ API virhe: {response.status}")
                    print(f"📄 Vastaus: {error_text}")
                    
                    if response.status == 401:
                        print("💡 Tarkista bot token")
                    elif response.status == 404:
                        print("💡 Bot ei löytynyt - tarkista token")
    
    except Exception as e:
        print(f"❌ Virhe: {e}")

def print_instructions():
    """Tulosta ohjeet"""
    print("🤖 Telegram Chat ID Hakija")
    print("=" * 40)
    print("📋 Ohjeet:")
    print("1. Luo Telegram bot @BotFather:lla")
    print("2. Kopioi bot token")
    print("3. Aja tämä ohjelma")
    print("4. Lähetä viesti botille kun ohjelma pyytää")
    print("5. Kopioi chat ID .env tiedostoon")
    print("=" * 40)

async def main():
    """Main funktio"""
    print_instructions()
    await get_chat_id()

if __name__ == "__main__":
    asyncio.run(main())