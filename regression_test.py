"""
Regressiotesti uusille lähteille - CI integraatio
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class RegressionTester:
    """Regressiotesti uusille lähteille"""
    
    def __init__(self):
        self.test_results = {}
        self.baseline_results = {}
        
        logger.info("✅ Regression tester alustettu")
    
    def run_regression_test(self, replay_file: str, test_name: str = "default") -> Dict[str, Any]:
        """Aja regressiotesti replay tiedostolla"""
        try:
            from replay_logger import ReplayPlayer
            
            # Lataa replay
            player = ReplayPlayer(replay_file)
            if not player.load_session():
                return {'success': False, 'error': 'Failed to load replay session'}
            
            # Aja testi
            start_time = time.time()
            results = self._run_test_scenario(player, test_name)
            duration = time.time() - start_time
            
            # Vertaa baseline:een
            baseline_comparison = self._compare_with_baseline(test_name, results)
            
            test_result = {
                'success': True,
                'test_name': test_name,
                'duration_seconds': duration,
                'results': results,
                'baseline_comparison': baseline_comparison,
                'timestamp': time.time()
            }
            
            self.test_results[test_name] = test_result
            
            logger.info(f"✅ Regression test valmis: {test_name} ({duration:.2f}s)")
            return test_result
            
        except Exception as e:
            logger.error(f"Virhe regressiotestissä {test_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _run_test_scenario(self, player, test_name: str) -> Dict[str, Any]:
        """Aja testi skenaario"""
        try:
            # Mock testi skenaario
            # Korvaa oikealla testi logiikalla
            
            events_processed = 0
            errors = 0
            new_tokens_found = 0
            hot_candidates_found = 0
            
            def test_callback(event_data):
                nonlocal events_processed, errors, new_tokens_found, hot_candidates_found
                
                try:
                    events_processed += 1
                    
                    # Simuloi testi logiikka
                    if event_data.get('event_type') == 'new_token':
                        new_tokens_found += 1
                        
                        # Simuloi hot candidate tarkistus
                        score = event_data.get('data', {}).get('score', 0)
                        if score > 0.6:
                            hot_candidates_found += 1
                    
                except Exception as e:
                    errors += 1
                    logger.warning(f"Test callback error: {e}")
            
            # Toista events
            player.replay_events(test_callback)
            
            # Laske metriikat
            success_rate = (events_processed - errors) / events_processed if events_processed > 0 else 0
            hot_candidate_rate = hot_candidates_found / new_tokens_found if new_tokens_found > 0 else 0
            
            return {
                'events_processed': events_processed,
                'errors': errors,
                'success_rate': success_rate,
                'new_tokens_found': new_tokens_found,
                'hot_candidates_found': hot_candidates_found,
                'hot_candidate_rate': hot_candidate_rate
            }
            
        except Exception as e:
            logger.error(f"Virhe testi skenaariossa: {e}")
            return {'error': str(e)}
    
    def _compare_with_baseline(self, test_name: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Vertaa baseline:een"""
        try:
            if test_name not in self.baseline_results:
                return {'status': 'no_baseline', 'message': 'Ei baseline dataa'}
            
            baseline = self.baseline_results[test_name]
            comparison = {}
            
            # Vertaa keskeisiä metriikoita
            metrics_to_compare = ['success_rate', 'hot_candidate_rate', 'events_processed']
            
            for metric in metrics_to_compare:
                if metric in results and metric in baseline:
                    current = results[metric]
                    baseline_val = baseline[metric]
                    
                    if baseline_val > 0:
                        change_pct = ((current - baseline_val) / baseline_val) * 100
                        comparison[metric] = {
                            'current': current,
                            'baseline': baseline_val,
                            'change_pct': change_pct,
                            'status': 'improved' if change_pct > 5 else 'degraded' if change_pct < -5 else 'stable'
                        }
            
            # Yleinen status
            if any(comp.get('status') == 'degraded' for comp in comparison.values()):
                comparison['overall_status'] = 'degraded'
            elif any(comp.get('status') == 'improved' for comp in comparison.values()):
                comparison['overall_status'] = 'improved'
            else:
                comparison['overall_status'] = 'stable'
            
            return comparison
            
        except Exception as e:
            logger.error(f"Virhe vertaillessa baseline:een: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def set_baseline(self, test_name: str, results: Dict[str, Any]):
        """Aseta baseline tulos"""
        try:
            self.baseline_results[test_name] = results
            logger.info(f"✅ Baseline asetettu: {test_name}")
            
        except Exception as e:
            logger.error(f"Virhe asettaessa baseline: {e}")
    
    def run_ci_test_suite(self, replay_dir: str = "replay_logs") -> Dict[str, Any]:
        """Aja CI test suite"""
        try:
            from replay_logger import ReplayLogger
            
            replay_logger = ReplayLogger(replay_dir)
            sessions = replay_logger.list_sessions()
            
            if not sessions:
                return {'success': False, 'error': 'Ei replay sessioita löytynyt'}
            
            # Aja testit kaikille sessioille
            test_results = {}
            overall_success = True
            
            for session in sessions[:5]:  # Max 5 sessiota
                test_name = f"replay_{session['session_name']}"
                result = self.run_regression_test(session['file'], test_name)
                
                test_results[test_name] = result
                if not result.get('success', False):
                    overall_success = False
            
            # Yhteenveto
            summary = {
                'success': overall_success,
                'tests_run': len(test_results),
                'tests_passed': sum(1 for r in test_results.values() if r.get('success', False)),
                'test_results': test_results,
                'timestamp': time.time()
            }
            
            logger.info(f"✅ CI test suite valmis: {summary['tests_passed']}/{summary['tests_run']} passed")
            return summary
            
        except Exception as e:
            logger.error(f"Virhe CI test suitessa: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_ci_report(self, test_results: Dict[str, Any]) -> str:
        """Generoi CI raportti"""
        try:
            if not test_results.get('success', False):
                return f"❌ CI Test Suite FAILED\n\nError: {test_results.get('error', 'Unknown error')}"
            
            summary = test_results
            tests_run = summary.get('tests_run', 0)
            tests_passed = summary.get('tests_passed', 0)
            
            report = f"""✅ CI Test Suite PASSED

📊 Yhteenveto:
• Testejä ajettu: {tests_run}
• Onnistuneita: {tests_passed}
• Epäonnistuneita: {tests_run - tests_passed}

📋 Testi tulokset:
"""
            
            for test_name, result in summary.get('test_results', {}).items():
                status = "✅" if result.get('success', False) else "❌"
                duration = result.get('duration_seconds', 0)
                
                report += f"• {test_name}: {status} ({duration:.2f}s)\n"
                
                # Baseline vertailu
                baseline = result.get('baseline_comparison', {})
                if baseline.get('overall_status'):
                    status_icon = "📈" if baseline['overall_status'] == 'improved' else "📉" if baseline['overall_status'] == 'degraded' else "➡️"
                    report += f"  {status_icon} Baseline: {baseline['overall_status']}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Virhe generoitaessa CI raporttia: {e}")
            return f"❌ Virhe generoitaessa raporttia: {e}"

# Global instance
regression_tester = RegressionTester()
