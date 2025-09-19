"""
Reaaliaikainen laatupaneeli - 4 korttia nopeaan tulkintaan
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QualityPanelData:
    """Laatupaneelin data"""
    hot_candidates_5m: int
    rejected_by_reason: Dict[str, int]
    min_score_effective: float
    source_health: Dict[str, bool]
    timestamp: float

class QualityPanel:
    """Reaaliaikainen laatupaneeli"""
    
    def __init__(self):
        self.data_history: List[QualityPanelData] = []
        self.last_update = 0
        self.update_interval = 300  # 5 min
        
        # NoNewPools hälytys
        self.last_pool_detection = {
            'raydium': time.time(),
            'pumpfun': time.time()
        }
        
        logger.info("✅ Laatupaneeli alustettu")
    
    def update_data(self, 
                   hot_candidates_5m: int,
                   rejected_by_reason: Dict[str, int],
                   min_score_effective: float,
                   source_health: Dict[str, bool]):
        """Päivitä laatupaneelin data"""
        try:
            current_time = time.time()
            
            # Luo uusi data-piste
            data = QualityPanelData(
                hot_candidates_5m=hot_candidates_5m,
                rejected_by_reason=rejected_by_reason,
                min_score_effective=min_score_effective,
                source_health=source_health,
                timestamp=current_time
            )
            
            # Lisää historiaan
            self.data_history.append(data)
            
            # Pidä vain viimeisen tunnin data
            cutoff_time = current_time - 3600
            self.data_history = [d for d in self.data_history if d.timestamp > cutoff_time]
            
            self.last_update = current_time
            
            # Tarkista hälytykset
            self._check_alerts()
            
        except Exception as e:
            logger.error(f"Virhe päivittäessä laatupaneelin dataa: {e}")
    
    def _check_alerts(self):
        """Tarkista hälytykset"""
        try:
            current_time = time.time()
            
            # NoNewPools hälytys (10 min)
            for source in ['raydium', 'pumpfun']:
                time_since_last = current_time - self.last_pool_detection[source]
                if time_since_last > 600:  # 10 min
                    logger.warning(f"🚨 NoNewPools hälytys: {source} ei löytänyt uusia pool:ja {time_since_last/60:.1f} min")
            
            # Hot candidates liian vähän
            if len(self.data_history) > 0:
                recent_data = self.data_history[-1]
                if recent_data.hot_candidates_5m < 1:
                    logger.warning(f"⚠️ Laatupaneeli: Vähän hot candidates (5m): {recent_data.hot_candidates_5m}")
            
            # Min score liian korkea
            if len(self.data_history) > 0:
                recent_data = self.data_history[-1]
                if recent_data.min_score_effective > 0.8:
                    logger.warning(f"⚠️ Laatupaneeli: Min score liian korkea: {recent_data.min_score_effective:.2f}")
            
            # Source health ongelmia
            if len(self.data_history) > 0:
                recent_data = self.data_history[-1]
                unhealthy_sources = [source for source, health in recent_data.source_health.items() if not health]
                if unhealthy_sources:
                    logger.warning(f"⚠️ Laatupaneeli: Unhealthy sources: {unhealthy_sources}")
        
        except Exception as e:
            logger.error(f"Virhe tarkistettaessa hälytyksiä: {e}")
    
    def get_panel_summary(self) -> str:
        """Hae laatupaneelin yhteenveto"""
        try:
            if not self.data_history:
                return "📊 Laatupaneeli: Ei dataa"
            
            recent_data = self.data_history[-1]
            
            # Hot candidates (5m)
            hot_candidates_status = "🟢" if recent_data.hot_candidates_5m >= 2 else "🟡" if recent_data.hot_candidates_5m >= 1 else "🔴"
            
            # Rejected by reason (top 3)
            top_reasons = sorted(recent_data.rejected_by_reason.items(), key=lambda x: x[1], reverse=True)[:3]
            reasons_text = ", ".join([f"{reason}: {count}" for reason, count in top_reasons])
            
            # Min score effective
            score_status = "🟢" if recent_data.min_score_effective <= 0.7 else "🟡" if recent_data.min_score_effective <= 0.8 else "🔴"
            
            # Source health
            healthy_sources = sum(1 for health in recent_data.source_health.values() if health)
            total_sources = len(recent_data.source_health)
            health_status = "🟢" if healthy_sources == total_sources else "🟡" if healthy_sources > 0 else "🔴"
            
            summary = f"""📊 *Laatupaneeli*
            
🔥 Hot candidates (5m): {hot_candidates_status} {recent_data.hot_candidates_5m}
❌ Hylkäykset: {reasons_text}
🎯 Min score: {score_status} {recent_data.min_score_effective:.2f}
🔗 Sources: {health_status} {healthy_sources}/{total_sources} OK"""
            
            return summary
            
        except Exception as e:
            logger.error(f"Virhe luodessa laatupaneelin yhteenvetoa: {e}")
            return "📊 Laatupaneeli: Virhe"
    
    def update_pool_detection(self, source: str):
        """Päivitä pool detection timestamp"""
        try:
            self.last_pool_detection[source] = time.time()
        except Exception as e:
            logger.error(f"Virhe päivittäessä pool detection: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Hae metriikkayhteenveto"""
        try:
            if not self.data_history:
                return {}
            
            recent_data = self.data_history[-1]
            
            return {
                'hot_candidates_5m': recent_data.hot_candidates_5m,
                'rejected_by_reason': recent_data.rejected_by_reason,
                'min_score_effective': recent_data.min_score_effective,
                'source_health': recent_data.source_health,
                'last_update': recent_data.timestamp,
                'data_points': len(self.data_history)
            }
            
        except Exception as e:
            logger.error(f"Virhe luodessa metriikkayhteenvetoa: {e}")
            return {}

# Global instance
quality_panel = QualityPanel()
