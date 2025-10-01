from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout: float = 60.0  # seconds


class CircuitBreaker:
    """Yksinkertainen circuit breaker DEX/APi -kutsuille."""

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._failure_count = 0
        self._last_failure: float | None = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def allow_request(self) -> bool:
        if self._state == "OPEN":
            if self._last_failure and (time.time() - self._last_failure) >= self._config.timeout:
                self._state = "HALF_OPEN"
                return True
            return False
        return True

    def record_success(self) -> None:
        self._failure_count = 0
        self._last_failure = None
        self._state = "CLOSED"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = time.time()
        if self._failure_count >= self._config.failure_threshold:
            self._state = "OPEN"

    @property
    def state(self) -> str:
        return self._state

