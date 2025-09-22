#!/usr/bin/env python3
"""
Birdeye API Key Manager Bot
Ratkaisee Birdeye API-avainongelman turvallisella tavalla.
Hallitsee useita avaimia, kierrättää niitä ja valvoo rate limittejä.
"""

import os
import json
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from zoneinfo import ZoneInfo
import aiohttp
import yaml
import hashlib
import base64
from cryptography.fernet import Fernet

# Lokitus
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Aikavyöhyke
TZ = ZoneInfo("Europe/Helsinki")


@dataclass
class ApiKey:
    """Yksittäinen API-avain ja sen metadata"""
    key: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    request_count: int = 0
    rate_limit: int = 100  # Requests per minute
    rate_limit_reset: Optional[datetime] = None
    is_active: bool = True
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Serialisoi avain tallennusta varten"""
        return {
            'key': self.key,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'request_count': self.request_count,
            'rate_limit': self.rate_limit,
            'rate_limit_reset': self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            'is_active': self.is_active,
            'errors': self.errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ApiKey':
        """Deserialisoi avain"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        if data.get('rate_limit_reset'):
            data['rate_limit_reset'] = datetime.fromisoformat(data['rate_limit_reset'])
        return cls(**data)


class BirdeyeKeyManager:
    """
    Hallitsee Birdeye API-avaimia turvallisesti.
    - Salaa avaimet levyllä
    - Kierrättää avaimia rate limit -tilanteissa
    - Valvoo avainten käyttöä ja terveyttä
    - Tarjoaa automaattisen fallback-mekanismin
    """
    
    def __init__(self, config_path: str = "birdeye_keys.json", password: Optional[str] = None):
        self.config_path = Path(config_path)
        self.keys: List[ApiKey] = []
        self.current_key_index = 0
        self.password = password or os.getenv("BIRDEYE_KEY_PASSWORD", "default_secure_password_change_me")
        self.cipher = self._init_cipher()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'key_rotations': 0,
            'rate_limit_hits': 0
        }
        self._lock = asyncio.Lock()
        
    def _init_cipher(self) -> Fernet:
        """Alustaa salausavaimen"""
        # Yksinkertainen tapa: käytä SHA256-hashia salasanasta
        # Tuotannossa käytä parempaa key derivation -funktiota
        key_hash = hashlib.sha256(self.password.encode()).digest()
        key = base64.urlsafe_b64encode(key_hash)
        return Fernet(key)
    
    def _encrypt(self, data: str) -> str:
        """Salaa merkkijonon"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt(self, data: str) -> str:
        """Purkaa salatun merkkijonon"""
        return self.cipher.decrypt(data.encode()).decode()
    
    async def load_keys(self) -> bool:
        """Lataa avaimet tiedostosta tai ympäristömuuttujista"""
        try:
            # Yritä ladata tiedostosta
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    encrypted_data = json.load(f)
                    for item in encrypted_data.get('keys', []):
                        decrypted_key = self._decrypt(item['key'])
                        item['key'] = decrypted_key
                        self.keys.append(ApiKey.from_dict(item))
                    self.stats = encrypted_data.get('stats', self.stats)
                logger.info(f"✅ Ladattiin {len(self.keys)} API-avainta")
                return True
            
            # Jos tiedostoa ei ole, yritä ladata ympäristömuuttujista
            env_keys = self._load_from_env()
            if env_keys:
                self.keys = env_keys
                await self.save_keys()
                logger.info(f"✅ Ladattiin {len(self.keys)} API-avainta ympäristömuuttujista")
                return True
            
            # Lataa config.yaml:sta fallbackina
            config_key = self._load_from_config()
            if config_key:
                self.keys = [config_key]
                await self.save_keys()
                logger.info("✅ Ladattiin 1 API-avain config.yaml:sta")
                return True
                
            logger.warning("⚠️ Ei API-avaimia saatavilla")
            return False
            
        except Exception as e:
            logger.error(f"❌ Virhe avainten latauksessa: {e}")
            return False
    
    def _load_from_env(self) -> List[ApiKey]:
        """Lataa avaimet ympäristömuuttujista"""
        keys = []
        
        # Tarkista yksittäinen avain
        single_key = os.getenv("BIRDEYE_API_KEY")
        if single_key:
            keys.append(ApiKey(
                key=single_key,
                name="primary",
                created_at=datetime.now(TZ)
            ))
        
        # Tarkista useat avaimet (BIRDEYE_API_KEY_1, BIRDEYE_API_KEY_2, ...)
        for i in range(1, 11):  # Max 10 avainta
            key = os.getenv(f"BIRDEYE_API_KEY_{i}")
            if key:
                keys.append(ApiKey(
                    key=key,
                    name=f"key_{i}",
                    created_at=datetime.now(TZ)
                ))
        
        return keys
    
    def _load_from_config(self) -> Optional[ApiKey]:
        """Lataa avain config.yaml:sta"""
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                key = config.get('sources', {}).get('birdeye', {}).get('api_key')
                if key and key != 'null':
                    return ApiKey(
                        key=key,
                        name="config_yaml",
                        created_at=datetime.now(TZ)
                    )
        except Exception as e:
            logger.debug(f"Ei voitu ladata config.yaml: {e}")
        return None
    
    async def save_keys(self) -> bool:
        """Tallenna avaimet salatusti"""
        try:
            async with self._lock:
                # Salaa avaimet ennen tallennusta
                encrypted_keys = []
                for key in self.keys:
                    key_dict = key.to_dict()
                    key_dict['key'] = self._encrypt(key_dict['key'])
                    encrypted_keys.append(key_dict)
                
                data = {
                    'keys': encrypted_keys,
                    'stats': self.stats,
                    'updated_at': datetime.now(TZ).isoformat()
                }
                
                with open(self.config_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.debug(f"💾 Tallennettu {len(self.keys)} avainta")
                return True
                
        except Exception as e:
            logger.error(f"❌ Virhe avainten tallennuksessa: {e}")
            return False
    
    async def add_key(self, key: str, name: Optional[str] = None) -> bool:
        """Lisää uusi API-avain"""
        try:
            # Tarkista ettei avain ole jo listassa
            for existing in self.keys:
                if existing.key == key:
                    logger.warning(f"⚠️ Avain {name} on jo listassa")
                    return False
            
            # Testaa avain
            if await self._test_key(key):
                new_key = ApiKey(
                    key=key,
                    name=name or f"key_{len(self.keys) + 1}",
                    created_at=datetime.now(TZ)
                )
                self.keys.append(new_key)
                await self.save_keys()
                logger.info(f"✅ Lisätty uusi avain: {new_key.name}")
                return True
            else:
                logger.error(f"❌ Avain {name} ei toimi")
                return False
                
        except Exception as e:
            logger.error(f"❌ Virhe avaimen lisäyksessä: {e}")
            return False
    
    async def _test_key(self, key: str) -> bool:
        """Testaa API-avaimen toimivuus"""
        try:
            url = "https://public-api.birdeye.so/v1/token/list"
            headers = {"X-API-KEY": key}
            params = {"chain": "solana", "limit": 1}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        logger.info(f"✅ API-avain toimii")
                        return True
                    elif response.status == 401:
                        logger.error(f"❌ API-avain ei kelpaa")
                        return False
                    elif response.status == 429:
                        logger.warning(f"⚠️ Rate limit saavutettu testissä")
                        return True  # Avain toimii, mutta rate limit
                    else:
                        logger.error(f"❌ Tuntematon vastaus: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Virhe avaimen testauksessa: {e}")
            return False
    
    async def get_key(self) -> Optional[str]:
        """Hae käytettävissä oleva API-avain"""
        async with self._lock:
            if not self.keys:
                logger.error("❌ Ei API-avaimia saatavilla")
                return None
            
            # Etsi toimiva avain
            attempts = 0
            while attempts < len(self.keys):
                key = self.keys[self.current_key_index]
                
                # Tarkista onko avain aktiivinen
                if not key.is_active:
                    self._rotate_key()
                    attempts += 1
                    continue
                
                # Tarkista rate limit
                if key.rate_limit_reset and datetime.now(TZ) < key.rate_limit_reset:
                    logger.warning(f"⚠️ Avain {key.name} rate limitissä")
                    self._rotate_key()
                    attempts += 1
                    continue
                
                # Päivitä käyttötiedot
                key.last_used = datetime.now(TZ)
                key.request_count += 1
                self.stats['total_requests'] += 1
                
                # Tarkista pyyntömäärä
                if key.request_count >= key.rate_limit:
                    key.rate_limit_reset = datetime.now(TZ) + timedelta(minutes=1)
                    key.request_count = 0
                    logger.info(f"🔄 Avain {key.name} saavutti rate limitin, kierretään")
                    self._rotate_key()
                
                logger.debug(f"🔑 Käytetään avainta: {key.name}")
                return key.key
            
            logger.error("❌ Kaikki avaimet rate limitissä tai epäaktiivisia")
            return None
    
    def _rotate_key(self):
        """Kierrä seuraavaan avaimeen"""
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        self.stats['key_rotations'] += 1
        logger.debug(f"🔄 Kierretty avaimeen {self.current_key_index}")
    
    async def mark_key_error(self, key_str: str, error: str):
        """Merkitse virhe avaimelle"""
        async with self._lock:
            for key in self.keys:
                if key.key == key_str:
                    key.errors.append({
                        'timestamp': datetime.now(TZ).isoformat(),
                        'error': error
                    })
                    
                    # Jos liikaa virheitä, deaktivoi avain
                    recent_errors = [e for e in key.errors 
                                   if datetime.fromisoformat(e['timestamp']) > 
                                   datetime.now(TZ) - timedelta(hours=1)]
                    
                    if len(recent_errors) >= 5:
                        key.is_active = False
                        logger.error(f"❌ Avain {key.name} deaktivoitu liian monien virheiden takia")
                    
                    self.stats['failed_requests'] += 1
                    await self.save_keys()
                    break
    
    async def mark_key_success(self, key_str: str):
        """Merkitse onnistunut pyyntö avaimelle"""
        async with self._lock:
            for key in self.keys:
                if key.key == key_str:
                    self.stats['successful_requests'] += 1
                    # Tyhjennä vanhat virheet onnistuneen pyynnön jälkeen
                    if key.errors:
                        cutoff = datetime.now(TZ) - timedelta(hours=24)
                        key.errors = [e for e in key.errors 
                                    if datetime.fromisoformat(e['timestamp']) > cutoff]
                    break
    
    async def get_status(self) -> Dict:
        """Hae avainten tila"""
        async with self._lock:
            status = {
                'total_keys': len(self.keys),
                'active_keys': sum(1 for k in self.keys if k.is_active),
                'current_key': self.keys[self.current_key_index].name if self.keys else None,
                'stats': self.stats,
                'keys': []
            }
            
            for key in self.keys:
                key_status = {
                    'name': key.name,
                    'is_active': key.is_active,
                    'last_used': key.last_used.isoformat() if key.last_used else None,
                    'request_count': key.request_count,
                    'rate_limit_reset': key.rate_limit_reset.isoformat() if key.rate_limit_reset else None,
                    'error_count': len(key.errors)
                }
                status['keys'].append(key_status)
            
            return status
    
    async def cleanup_old_errors(self):
        """Siivoa vanhat virheet"""
        async with self._lock:
            cutoff = datetime.now(TZ) - timedelta(days=7)
            for key in self.keys:
                key.errors = [e for e in key.errors 
                            if datetime.fromisoformat(e['timestamp']) > cutoff]
            await self.save_keys()
    
    async def reactivate_keys(self):
        """Aktivoi uudelleen deaktivoidut avaimet jos ne toimivat"""
        async with self._lock:
            for key in self.keys:
                if not key.is_active:
                    if await self._test_key(key.key):
                        key.is_active = True
                        key.errors = []
                        logger.info(f"✅ Avain {key.name} aktivoitu uudelleen")
            await self.save_keys()


class BirdeyeKeyBot:
    """
    Botti joka valvoo ja hallitsee Birdeye API-avaimia automaattisesti
    """
    
    def __init__(self):
        self.manager = BirdeyeKeyManager()
        self.running = False
        self._tasks = []
        
    async def start(self):
        """Käynnistä botti"""
        logger.info("🚀 Birdeye Key Manager Bot käynnistyy...")
        
        # Lataa avaimet
        if not await self.manager.load_keys():
            logger.error("❌ Ei voitu ladata avaimia, lopetetaan")
            return
        
        self.running = True
        
        # Käynnistä taustatehtävät
        self._tasks = [
            asyncio.create_task(self._monitor_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._reactivation_loop()),
            asyncio.create_task(self._status_loop())
        ]
        
        logger.info("✅ Botti käynnistetty")
        
        # Odota kunnes pysäytetään
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("🛑 Botti pysäytetty")
    
    async def stop(self):
        """Pysäytä botti"""
        self.running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.manager.save_keys()
        logger.info("✅ Botti pysäytetty siististi")
    
    async def _monitor_loop(self):
        """Valvo avainten tilaa"""
        while self.running:
            try:
                status = await self.manager.get_status()
                
                # Hälytä jos kaikki avaimet epäaktiivisia
                if status['active_keys'] == 0:
                    logger.critical("🚨 KAIKKI API-AVAIMET EPÄAKTIIVISIA!")
                    # Tässä voisi lähettää Telegram-hälytyksen
                
                # Hälytä jos yli 80% avaimista rate limitissä
                rate_limited = sum(1 for k in status['keys'] 
                                 if k.get('rate_limit_reset'))
                if status['total_keys'] > 0 and rate_limited / status['total_keys'] > 0.8:
                    logger.warning(f"⚠️ {rate_limited}/{status['total_keys']} avainta rate limitissä")
                
                await asyncio.sleep(60)  # Tarkista minuutin välein
                
            except Exception as e:
                logger.error(f"❌ Virhe monitoroinnissa: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Siivoa vanhoja virheitä säännöllisesti"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Kerran tunnissa
                await self.manager.cleanup_old_errors()
                logger.info("🧹 Vanhat virheet siivottu")
                
            except Exception as e:
                logger.error(f"❌ Virhe siivouksessa: {e}")
    
    async def _reactivation_loop(self):
        """Yritä aktivoida epäaktiivisia avaimia uudelleen"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # 30 minuutin välein
                await self.manager.reactivate_keys()
                
            except Exception as e:
                logger.error(f"❌ Virhe uudelleenaktivoinnissa: {e}")
    
    async def _status_loop(self):
        """Tulosta tila säännöllisesti"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minuutin välein
                status = await self.manager.get_status()
                
                logger.info(f"""
📊 Birdeye Key Manager Status:
- Avaimia yhteensä: {status['total_keys']}
- Aktiivisia: {status['active_keys']}
- Nykyinen avain: {status['current_key']}
- Pyyntöjä yhteensä: {status['stats']['total_requests']}
- Onnistuneita: {status['stats']['successful_requests']}
- Epäonnistuneita: {status['stats']['failed_requests']}
- Avainten kiertoja: {status['stats']['key_rotations']}
                """)
                
            except Exception as e:
                logger.error(f"❌ Virhe tilastossa: {e}")


# Integraatio muihin botteihin
class BirdeyeAPIWrapper:
    """
    Wrapper-luokka joka korvaa suorat Birdeye API-kutsut.
    Käyttää BirdeyeKeyManageria avainten hallintaan.
    """
    
    def __init__(self, manager: BirdeyeKeyManager):
        self.manager = manager
        
    async def request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Tee API-pyyntö automaattisella avaintenhallinnalla"""
        max_retries = 3
        
        for attempt in range(max_retries):
            # Hae avain
            api_key = await self.manager.get_key()
            if not api_key:
                logger.error("❌ Ei API-avainta saatavilla")
                return None
            
            # Lisää avain headereihin
            headers = kwargs.get('headers', {})
            headers['X-API-KEY'] = api_key
            kwargs['headers'] = headers
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **kwargs) as response:
                        if response.status == 200:
                            await self.manager.mark_key_success(api_key)
                            return await response.json()
                        elif response.status == 429:
                            # Rate limit
                            await self.manager.mark_key_error(api_key, "Rate limit")
                            logger.warning(f"⚠️ Rate limit, yritetään toisella avaimella")
                            await asyncio.sleep(1)
                            continue
                        elif response.status == 401:
                            # Invalid key
                            await self.manager.mark_key_error(api_key, "Invalid key")
                            logger.error(f"❌ Virheellinen API-avain")
                            continue
                        else:
                            error = f"HTTP {response.status}"
                            await self.manager.mark_key_error(api_key, error)
                            logger.error(f"❌ API-virhe: {error}")
                            return None
                            
            except Exception as e:
                await self.manager.mark_key_error(api_key, str(e))
                logger.error(f"❌ Pyyntövirhe: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
        
        logger.error(f"❌ Kaikki yritykset epäonnistuivat")
        return None


async def main():
    """Pääohjelma - käynnistä botti"""
    bot = BirdeyeKeyBot()
    
    try:
        # Käynnistä botti
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("⌨️ Keskeytetty käyttäjän toimesta")
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Tarkista onko .env-tiedosto
    env_path = Path(".env")
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Ladattu .env-tiedosto")
        
        # Tarkista onko BIRDEYE_API_KEY
        if os.getenv("BIRDEYE_API_KEY"):
            logger.info(f"✅ Löytyi BIRDEYE_API_KEY: {os.getenv('BIRDEYE_API_KEY')[:8]}...")
    else:
        logger.warning("⚠️ .env-tiedostoa ei löydy")
        logger.info("💡 Luo se ajamalla: python3 create_env.py")
    
    # Käynnistä botti
    asyncio.run(main())