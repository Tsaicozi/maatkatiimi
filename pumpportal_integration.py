"""
PumpPortal WebSocket Integration
Reaaliaikainen kryptovaluutta-data PumpPortal:sta
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
import pandas as pd

# Konfiguroi logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TokenCreationEvent:
    """Token creation event data"""
    timestamp: datetime
    token_address: str
    creator: str
    initial_supply: float
    initial_price: float
    metadata: Dict[str, Any]

@dataclass
class TokenTradeEvent:
    """Token trade event data"""
    timestamp: datetime
    token_address: str
    trader: str
    trade_type: str  # 'buy' or 'sell'
    amount: float
    price: float
    volume_usd: float

@dataclass
class AccountTradeEvent:
    """Account trade event data"""
    timestamp: datetime
    account: str
    token_address: str
    trade_type: str
    amount: float
    price: float
    volume_usd: float

@dataclass
class MigrationEvent:
    """Token migration event data"""
    timestamp: datetime
    token_address: str
    from_platform: str
    to_platform: str
    migration_data: Dict[str, Any]

class PumpPortalClient:
    """PumpPortal WebSocket client reaaliaikaiselle datalle"""
    
    def __init__(self):
        self.websocket = None
        self.uri = "wss://pumpportal.fun/api/data"
        self.subscriptions = {
            'new_tokens': False,
            'token_trades': set(),
            'account_trades': set(),
            'migrations': False
        }
        self.callbacks = {
            'on_token_creation': [],
            'on_token_trade': [],
            'on_account_trade': [],
            'on_migration': []
        }
        self.is_connected = False
        self.running = False
        
    def add_callback(self, event_type: str, callback: Callable):
        """Lisää callback-funktio tapahtumalle"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Tuntematon event_type: {event_type}")
    
    async def connect(self):
        """Yhdistä PumpPortal WebSocket:iin"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            logger.info("✅ Yhdistetty PumpPortal WebSocket:iin")
            return True
        except Exception as e:
            logger.error(f"❌ Virhe WebSocket-yhteydessä: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Katkaise WebSocket-yhteys"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("🔌 WebSocket-yhteys katkaistu")
    
    async def subscribe_new_tokens(self):
        """Tilaa uusien tokenien luomistapahtumat"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return False
        
        payload = {"method": "subscribeNewToken"}
        await self.websocket.send(json.dumps(payload))
        self.subscriptions['new_tokens'] = True
        logger.info("📝 Tilattu uusien tokenien luomistapahtumat")
        return True
    
    async def subscribe_token_trades(self, token_addresses: List[str]):
        """Tilaa token-kauppatapahtumat"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return False
        
        payload = {
            "method": "subscribeTokenTrade",
            "keys": token_addresses
        }
        await self.websocket.send(json.dumps(payload))
        
        for addr in token_addresses:
            self.subscriptions['token_trades'].add(addr)
        
        logger.info(f"📈 Tilattu token-kauppatapahtumat: {len(token_addresses)} tokenille")
        return True
    
    async def subscribe_account_trades(self, account_addresses: List[str]):
        """Tilaa tili-kauppatapahtumat"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return False
        
        payload = {
            "method": "subscribeAccountTrade",
            "keys": account_addresses
        }
        await self.websocket.send(json.dumps(payload))
        
        for addr in account_addresses:
            self.subscriptions['account_trades'].add(addr)
        
        logger.info(f"👤 Tilattu tili-kauppatapahtumat: {len(account_addresses)} tilille")
        return True
    
    async def subscribe_migrations(self):
        """Tilaa token-migraatiotapahtumat"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return False
        
        payload = {"method": "subscribeMigration"}
        await self.websocket.send(json.dumps(payload))
        self.subscriptions['migrations'] = True
        logger.info("🔄 Tilattu token-migraatiotapahtumat")
        return True
    
    async def unsubscribe_token_trades(self, token_addresses: List[str]):
        """Peruuta token-kauppatapahtumien tilaaminen"""
        if not self.is_connected:
            return False
        
        payload = {
            "method": "unsubscribeTokenTrade",
            "keys": token_addresses
        }
        await self.websocket.send(json.dumps(payload))
        
        for addr in token_addresses:
            self.subscriptions['token_trades'].discard(addr)
        
        logger.info(f"❌ Peruutettu token-kauppatapahtumien tilaaminen: {len(token_addresses)} tokenille")
        return True
    
    def _parse_token_creation(self, data: Dict) -> Optional[TokenCreationEvent]:
        """Jäsennä token creation event"""
        try:
            return TokenCreationEvent(
                timestamp=datetime.now(),
                token_address=data.get('token_address', ''),
                creator=data.get('creator', ''),
                initial_supply=float(data.get('initial_supply', 0)),
                initial_price=float(data.get('initial_price', 0)),
                metadata=data.get('metadata', {})
            )
        except Exception as e:
            logger.error(f"Virhe token creation -parsinnassa: {e}")
            return None
    
    def _parse_token_trade(self, data: Dict) -> Optional[TokenTradeEvent]:
        """Jäsennä token trade event"""
        try:
            return TokenTradeEvent(
                timestamp=datetime.now(),
                token_address=data.get('token_address', ''),
                trader=data.get('trader', ''),
                trade_type=data.get('trade_type', ''),
                amount=float(data.get('amount', 0)),
                price=float(data.get('price', 0)),
                volume_usd=float(data.get('volume_usd', 0))
            )
        except Exception as e:
            logger.error(f"Virhe token trade -parsinnassa: {e}")
            return None
    
    def _parse_account_trade(self, data: Dict) -> Optional[AccountTradeEvent]:
        """Jäsennä account trade event"""
        try:
            return AccountTradeEvent(
                timestamp=datetime.now(),
                account=data.get('account', ''),
                token_address=data.get('token_address', ''),
                trade_type=data.get('trade_type', ''),
                amount=float(data.get('amount', 0)),
                price=float(data.get('price', 0)),
                volume_usd=float(data.get('volume_usd', 0))
            )
        except Exception as e:
            logger.error(f"Virhe account trade -parsinnassa: {e}")
            return None
    
    def _parse_migration(self, data: Dict) -> Optional[MigrationEvent]:
        """Jäsennä migration event"""
        try:
            return MigrationEvent(
                timestamp=datetime.now(),
                token_address=data.get('token_address', ''),
                from_platform=data.get('from_platform', ''),
                to_platform=data.get('to_platform', ''),
                migration_data=data.get('migration_data', {})
            )
        except Exception as e:
            logger.error(f"Virhe migration -parsinnassa: {e}")
            return None
    
    async def _handle_message(self, message: str):
        """Käsittele saapunut viesti"""
        try:
            data = json.loads(message)
            event_type = data.get('type', '')
            
            if event_type == 'new_token':
                event = self._parse_token_creation(data)
                if event:
                    for callback in self.callbacks['on_token_creation']:
                        await callback(event)
            
            elif event_type == 'token_trade':
                event = self._parse_token_trade(data)
                if event:
                    for callback in self.callbacks['on_token_trade']:
                        await callback(event)
            
            elif event_type == 'account_trade':
                event = self._parse_account_trade(data)
                if event:
                    for callback in self.callbacks['on_account_trade']:
                        await callback(event)
            
            elif event_type == 'migration':
                event = self._parse_migration(data)
                if event:
                    for callback in self.callbacks['on_migration']:
                        await callback(event)
            
            else:
                logger.debug(f"Tuntematon event_type: {event_type}")
                
        except Exception as e:
            logger.error(f"Virhe viestin käsittelyssä: {e}")
    
    async def listen(self):
        """Kuuntele WebSocket-viestejä"""
        if not self.is_connected:
            logger.error("Ei yhteyttä WebSocket:iin")
            return
        
        self.running = True
        logger.info("🎧 Aloitetaan WebSocket-viestien kuuntelu...")
        
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket-yhteys suljettu")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Virhe WebSocket-kuuntelussa: {e}")
        finally:
            self.running = False
    
    def stop(self):
        """Pysäytä kuuntelu"""
        self.running = False
        logger.info("⏹️ WebSocket-kuuntelu pysäytetty")

class PumpPortalAnalyzer:
    """Analysoi PumpPortal-dataa sijoitusstrategioita varten"""
    
    def __init__(self):
        self.client = PumpPortalClient()
        self.token_data = {}
        self.trade_data = []
        self.volume_data = {}
        
        # Lisää callbackit
        self.client.add_callback('on_token_creation', self._on_token_creation)
        self.client.add_callback('on_token_trade', self._on_token_trade)
        self.client.add_callback('on_account_trade', self._on_account_trade)
        self.client.add_callback('on_migration', self._on_migration)
    
    async def _on_token_creation(self, event: TokenCreationEvent):
        """Käsittele uuden tokenin luominen"""
        logger.info(f"🆕 Uusi token luotu: {event.token_address[:8]}...")
        
        self.token_data[event.token_address] = {
            'creation_time': event.timestamp,
            'creator': event.creator,
            'initial_supply': event.initial_supply,
            'initial_price': event.initial_price,
            'metadata': event.metadata
        }
    
    async def _on_token_trade(self, event: TokenTradeEvent):
        """Käsittele token-kauppa"""
        logger.info(f"💰 Token-kauppa: {event.trade_type} {event.amount} @ ${event.price}")
        
        self.trade_data.append({
            'timestamp': event.timestamp,
            'token_address': event.token_address,
            'trader': event.trader,
            'trade_type': event.trade_type,
            'amount': event.amount,
            'price': event.price,
            'volume_usd': event.volume_usd
        })
        
        # Päivitä volyymidata
        if event.token_address not in self.volume_data:
            self.volume_data[event.token_address] = {'buy': 0, 'sell': 0, 'total': 0}
        
        self.volume_data[event.token_address][event.trade_type] += event.volume_usd
        self.volume_data[event.token_address]['total'] += event.volume_usd
    
    async def _on_account_trade(self, event: AccountTradeEvent):
        """Käsittele tili-kauppa"""
        logger.info(f"👤 Tili-kauppa: {event.account[:8]}... {event.trade_type} {event.amount}")
    
    async def _on_migration(self, event: MigrationEvent):
        """Käsittele token-migraatio"""
        logger.info(f"🔄 Token-migraatio: {event.token_address[:8]}... {event.from_platform} → {event.to_platform}")
    
    def get_hot_tokens(self, limit: int = 10) -> List[Dict]:
        """Hae kuumimmat tokenit volyymin perusteella"""
        sorted_tokens = sorted(
            self.volume_data.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )
        
        return [
            {
                'token_address': addr,
                'volume_24h': data['total'],
                'buy_volume': data['buy'],
                'sell_volume': data['sell'],
                'buy_sell_ratio': data['buy'] / max(data['sell'], 1)
            }
            for addr, data in sorted_tokens[:limit]
        ]
    
    def get_trading_activity(self, hours: int = 24) -> Dict:
        """Hae kaupankäyntiaktiviteetti"""
        cutoff_time = datetime.now() - pd.Timedelta(hours=hours)
        recent_trades = [
            trade for trade in self.trade_data
            if trade['timestamp'] > cutoff_time
        ]
        
        if not recent_trades:
            return {'total_trades': 0, 'total_volume': 0, 'unique_tokens': 0}
        
        total_volume = sum(trade['volume_usd'] for trade in recent_trades)
        unique_tokens = len(set(trade['token_address'] for trade in recent_trades))
        
        return {
            'total_trades': len(recent_trades),
            'total_volume': total_volume,
            'unique_tokens': unique_tokens,
            'avg_trade_size': total_volume / len(recent_trades) if recent_trades else 0
        }
    
    async def start_monitoring(self, tokens_to_watch: List[str] = None, accounts_to_watch: List[str] = None):
        """Aloita seuranta"""
        logger.info("🚀 Käynnistetään PumpPortal-seuranta...")
        
        # Yhdistä WebSocket:iin
        if not await self.client.connect():
            return False
        
        # Tilaa tapahtumat
        await self.client.subscribe_new_tokens()
        await self.client.subscribe_migrations()
        
        if tokens_to_watch:
            await self.client.subscribe_token_trades(tokens_to_watch)
        
        if accounts_to_watch:
            await self.client.subscribe_account_trades(accounts_to_watch)
        
        # Aloita kuuntelu
        await self.client.listen()
        
        return True
    
    def stop_monitoring(self):
        """Pysäytä seuranta"""
        self.client.stop()
        logger.info("⏹️ PumpPortal-seuranta pysäytetty")

# Esimerkki käytöstä
async def example_usage():
    """Esimerkki PumpPortal-integraation käytöstä"""
    analyzer = PumpPortalAnalyzer()
    
    # Seuraa tiettyjä tokeneita
    tokens_to_watch = [
        "91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p",
        "Bwc4EBE65qXVzZ9ZiieBraj9GZL4Y2d7NN7B9pXENWR2"
    ]
    
    # Seuraa tiettyjä tilejä
    accounts_to_watch = [
        "AArPXm8JatJiuyEffuC1un2Sc835SULa4uQqDcaGpAjV"
    ]
    
    try:
        # Aloita seuranta
        await analyzer.start_monitoring(tokens_to_watch, accounts_to_watch)
    except KeyboardInterrupt:
        logger.info("Seuranta pysäytetty käyttäjän toimesta")
    finally:
        analyzer.stop_monitoring()

if __name__ == "__main__":
    # Käynnistä esimerkki
    asyncio.run(example_usage())
