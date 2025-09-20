# metrics.py
from __future__ import annotations
try:
	from prometheus_client import (
		Counter, Gauge, Histogram,
		start_http_server, CollectorRegistry, REGISTRY, generate_latest
	)
except Exception:
	class _Noop:
		def __init__(self, *a, **k): pass
		def inc(self, *a, **k): pass
		def labels(self, *a, **k): return self
		def set(self, *a, **k): pass
		def observe(self, *a, **k): pass
	class Counter(_Noop): pass
	class Gauge(_Noop): pass
	class Histogram(_Noop): pass
	def start_http_server(*a, **k): return None
	class _Reg: pass
	CollectorRegistry = _Reg
	REGISTRY = _Reg()
	def generate_latest(_): return b""
import threading, socket, time, logging
import contextlib

log = logging.getLogger(__name__)

# JSON logger for alerts
json_logger = None

class Metrics:
	def __init__(self, namespace: str = "hybrid_bot", registry: CollectorRegistry | None = None):
		ns = namespace
		self._server_started = False
		self._lock = threading.Lock()
		self.registry = registry or REGISTRY  # <-- TESTEISSÄ oma registry

		# Counters
		self.candidates_seen = Counter(f"{ns}_candidates_seen_total", "Ehdokkaita havaittu yhteensä", registry=self.registry)
		self.candidates_filtered = Counter(f"{ns}_candidates_filtered_total", "Pikafiltteri hylkäsi", registry=self.registry)
		self.candidates_scored = Counter(f"{ns}_candidates_scored_total", "Ehdokkaita pisteytetty", registry=self.registry)
		self.telegram_sent = Counter(f"{ns}_telegram_sent_total", "Lähetetyt Telegram-viestit", registry=self.registry)
		self.rpc_errors = Counter(f"{ns}_rpc_errors_total", "RPC-virheet", registry=self.registry)
		self.source_errors = Counter(f"{ns}_source_errors_total", "Lähdeadapterivirheet", registry=self.registry)
		self.loop_restarts = Counter(f"{ns}_scorer_loop_restarts_total", "Scorer-loop restartit", registry=self.registry)
		
		# Uudet metriikat
		self.candidates_in = Counter(f"{ns}_candidates_in_total", "Ehdokkaita sisään per lähde", ["source"], registry=self.registry)
		self.candidates_filtered_reason = Counter(f"{ns}_candidates_filtered_reason_total", "Hylkäyksen syyt", ["reason"], registry=self.registry)
		self.min_score_effective = Gauge(f"{ns}_min_score_effective", "Todellinen dynaaminen score-kynnys", registry=self.registry)
		self.source_health = Gauge(f"{ns}_source_health", "Lähde health (1=ok, 0=down)", ["source"], registry=self.registry)
		self.fresh_pass_total = Counter(f"{ns}_fresh_pass_total", "Fresh-pass läpimenot WS-kandille", registry=self.registry)
		
		# Trading metriikat
		self.trades_sent = Counter(f"{ns}_trades_sent_total", "Lähetetyt kaupat (live/paper)", ["mode"], registry=self.registry)
		self.trades_failed = Counter(f"{ns}_trades_failed_total", "Epäonnistuneet kaupat", ["stage"], registry=self.registry)
		
		# Burn-in seuranta
		self.hot_candidates_per_hour = Gauge(f"{ns}_hot_candidates_per_hour", "Hot candidates tunnissa", registry=self.registry)
		self.spam_ratio = Gauge(f"{ns}_spam_ratio", "Spam-suhde (filtered/total)", registry=self.registry)
		self.cycle_p95_duration = Gauge(f"{ns}_cycle_p95_duration", "P95 sykli kesto (s)", registry=self.registry)
		self.rpc_error_rate = Gauge(f"{ns}_rpc_error_rate", "RPC virhe rate (per min)", registry=self.registry)

		# Gauges
		self.queue_depth = Gauge(f"{ns}_queue_depth", "Candidate-jonon pituus", registry=self.registry)
		self.engine_running = Gauge(f"{ns}_engine_running", "DiscoveryEngine käynnissä (1/0)", registry=self.registry)
		self.hot_candidates_gauge = Gauge(f"{ns}_hot_candidates", "Hot candidate -määrä", registry=self.registry)
		self.health = Gauge(f"{ns}_metrics_health", "Metrics-palvelin OK (1/0)", registry=self.registry)
		self.health.set(1)

		# Histograms
		self.score_hist = Histogram(f"{ns}_score_hist", "Score-jakauma", buckets=[0.2,0.4,0.6,0.7,0.8,0.9,1.0], registry=self.registry)
		self.rpc_latency = Histogram(f"{ns}_rpc_latency_sec", "RPC-kutsun kesto (s)", buckets=(0.05,0.1,0.2,0.5,1,2,5), registry=self.registry)
		self.cycle_duration = Histogram(f"{ns}_cycle_duration_sec", "Trading-syklin kesto (s)", buckets=(0.1,0.5,1,2,3,5,10), registry=self.registry)

	def _create_alert_logger(self):
		"""Create alert logger function"""
		def log_alert(alert_name: str, severity: str, description: str, **kwargs):
			global json_logger
			if json_logger:
				json_logger.warning(f"Alert triggered: {alert_name}", extra={
					"alert_name": alert_name,
					"severity": severity,
					"description": description,
					**kwargs
				})
		return log_alert

	def _tcp_probe(self, host: str, port: int, timeout: float = 1.0) -> bool:
		try:
			with socket.create_connection((host, port), timeout=timeout):
				return True
		except Exception:
			return False

	def start_server(self, host: str, port: int, fallback_ports: int = 10, *, enable_http: bool = True) -> int | None:
		"""Käynnistä HTTP-serveri. Testeissä voit asettaa enable_http=False."""
		if not enable_http:
			log.info("Metrics HTTP-server ohitettu (enable_http=False).")
			self.health.set(1)  # registry itsessään OK
			return None

		with self._lock:
			if self._server_started:
				log.info("Metrics-palvelin on jo käynnissä")
				return port

			last_err = None
			for p in range(port, port + fallback_ports + 1):
				try:
					start_http_server(p, addr=host, registry=self.registry)
					self._server_started = True
					# readiness wait
					ok_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
					healthy = False
					for _ in range(60):
						time.sleep(0.05)
						if self._tcp_probe(ok_host, p):
							healthy = True
							break
					self.health.set(1 if healthy else 0)
					log.info(f"✅ Metrics-palvelin käynnissä: http://{host}:{p}/metrics (health={healthy})")
					return p
				except OSError as e:
					last_err = e
					log.warning(f"Metrics-portti {p} varattu ({e}). Yritetään seuraavaa...")
				except Exception as e:
					last_err = e
					log.error(f"Metrics-palvelimen käynnistysvirhe portissa {p}: {e}")

			raise RuntimeError(f"Metrics-palvelinta ei voitu käynnistää (viimeisin virhe: {last_err})")

# Globaalisti käytettävä instanssi
metrics: Metrics | None = None

def init_metrics(
	namespace: str = "hybrid_bot",
	host: str = "0.0.0.0",
	port: int = 9108,
	enabled: bool = True,
	*,
	enable_http: bool = True,                # <-- UUSI
	registry: CollectorRegistry | None = None  # <-- UUSI
):
	"""Alustaa mittarit. Testeissä: enabled=True, enable_http=False, registry=CollectorRegistry()."""
	global metrics, json_logger
	if not enabled:
		metrics = None
		log.info("Metrics poistettu käytöstä (enabled=false).")
		return None

	metrics = Metrics(namespace=namespace, registry=registry)
	actual_port = None
	with contextlib.suppress(Exception):
		actual_port = metrics.start_server(host=host, port=port, enable_http=enable_http)
	
	# Setup JSON logger for alerts
	try:
		from json_logging import setup_json_logging
		json_logger = setup_json_logging()
	except Exception:
		json_logger = None
	
	return actual_port

def dump_metrics_text() -> str:
	"""Palauta nykyisen registryn metriikat tekstinä (hyvä asserteihin testeissä)."""
	if not metrics:
		return ""
	return generate_latest(metrics.registry).decode("utf-8")