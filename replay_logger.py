"""
Replay Logger - tallentaa 5-10 min replay-logi regressiotestejä varten
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ReplayEvent:
    """Replay event tietue"""
    timestamp: float
    source: str
    event_type: str  # 'new_pool', 'new_token', 'price_update', 'error'
    data: Dict[str, Any]
    raw_response: Optional[str] = None

class ReplayLogger:
    """Replay logger regressiotestejä varten"""
    
    def __init__(self, log_dir: str = "replay_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.events: List[ReplayEvent] = []
        self.max_events = 10000  # Max 10k events
        self.log_duration = 600  # 10 min default
        
        self.current_session = None
        self.session_start = None
        
        logger.info(f"✅ Replay logger alustettu: {self.log_dir}")
    
    def start_session(self, session_name: str = None):
        """Aloita uusi replay sessio"""
        try:
            if session_name is None:
                session_name = f"replay_{int(time.time())}"
            
            self.current_session = session_name
            self.session_start = time.time()
            self.events = []
            
            logger.info(f"🎬 Replay sessio aloitettu: {session_name}")
            
        except Exception as e:
            logger.error(f"Virhe aloittaessa replay sessiota: {e}")
    
    def log_event(self, source: str, event_type: str, data: Dict[str, Any], raw_response: str = None):
        """Kirjaa replay event"""
        try:
            if not self.current_session:
                return  # Ei aktiivista sessiota
            
            # Tarkista onko sessio vanhentunut
            if time.time() - self.session_start > self.log_duration:
                self.stop_session()
                return
            
            # Luo event
            event = ReplayEvent(
                timestamp=time.time(),
                source=source,
                event_type=event_type,
                data=data,
                raw_response=raw_response
            )
            
            # Lisää eventtiin
            self.events.append(event)
            
            # Pidä vain viimeiset max_events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
            
            logger.debug(f"📝 Replay event: {source} {event_type}")
            
        except Exception as e:
            logger.error(f"Virhe kirjattaessa replay event: {e}")
    
    def stop_session(self) -> Optional[str]:
        """Lopeta replay sessio ja tallenna"""
        try:
            if not self.current_session or not self.events:
                return None
            
            # Tallenna sessio
            session_file = self.log_dir / f"{self.current_session}.json"
            
            session_data = {
                'session_name': self.current_session,
                'start_time': self.session_start,
                'end_time': time.time(),
                'duration_seconds': time.time() - self.session_start,
                'event_count': len(self.events),
                'events': [asdict(event) for event in self.events]
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Replay sessio tallennettu: {session_file} ({len(self.events)} events)")
            
            # Resetoi
            session_name = self.current_session
            self.current_session = None
            self.session_start = None
            self.events = []
            
            return str(session_file)
            
        except Exception as e:
            logger.error(f"Virhe lopettaessa replay sessiota: {e}")
            return None
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Hae session tilastot"""
        try:
            if not self.current_session:
                return {}
            
            current_time = time.time()
            duration = current_time - self.session_start if self.session_start else 0
            
            # Event tyypit
            event_types = {}
            sources = {}
            
            for event in self.events:
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
                sources[event.source] = sources.get(event.source, 0) + 1
            
            return {
                'session_name': self.current_session,
                'duration_seconds': duration,
                'event_count': len(self.events),
                'event_types': event_types,
                'sources': sources,
                'is_active': True
            }
            
        except Exception as e:
            logger.error(f"Virhe haettaessa session tilastoja: {e}")
            return {}
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Listaa tallennetut sessionit"""
        try:
            sessions = []
            
            for session_file in self.log_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sessions.append({
                        'file': str(session_file),
                        'session_name': data.get('session_name', 'unknown'),
                        'start_time': data.get('start_time', 0),
                        'duration_seconds': data.get('duration_seconds', 0),
                        'event_count': data.get('event_count', 0)
                    })
                except Exception as e:
                    logger.warning(f"Virhe lukemassa session tiedostoa {session_file}: {e}")
            
            # Järjestä uusimmat ensin
            sessions.sort(key=lambda x: x['start_time'], reverse=True)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Virhe listatessa sessioneita: {e}")
            return []

class ReplayPlayer:
    """Replay player regressiotestejä varten"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.session_data = None
        
        logger.info(f"🎮 Replay player alustettu: {log_file}")
    
    def load_session(self) -> bool:
        """Lataa replay sessio"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.session_data = json.load(f)
            
            logger.info(f"✅ Replay sessio ladattu: {self.session_data['event_count']} events")
            return True
            
        except Exception as e:
            logger.error(f"Virhe lataessa replay sessiota: {e}")
            return False
    
    def replay_events(self, callback_func) -> bool:
        """Toista events callback funktiolla"""
        try:
            if not self.session_data:
                logger.error("Ei session dataa ladattuna")
                return False
            
            events = self.session_data.get('events', [])
            logger.info(f"🎬 Aloitetaan replay: {len(events)} events")
            
            for i, event_data in enumerate(events):
                try:
                    # Kutsu callback funktiota
                    callback_func(event_data)
                    
                    # Simuloi aikaviivettä (jos halutaan)
                    # await asyncio.sleep(0.001)  # 1ms viive
                    
                except Exception as e:
                    logger.error(f"Virhe toistettaessa event {i}: {e}")
            
            logger.info(f"✅ Replay valmis: {len(events)} events toistettu")
            return True
            
        except Exception as e:
            logger.error(f"Virhe toistettaessa events: {e}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """Hae session tiedot"""
        if not self.session_data:
            return {}
        
        return {
            'session_name': self.session_data.get('session_name', 'unknown'),
            'start_time': self.session_data.get('start_time', 0),
            'duration_seconds': self.session_data.get('duration_seconds', 0),
            'event_count': self.session_data.get('event_count', 0)
        }

# Global instance
replay_logger = ReplayLogger()
