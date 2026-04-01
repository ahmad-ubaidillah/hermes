"""Hermes Resilience Module

Provides:
- Retry logic with exponential backoff and jitter
- Circuit breaker pattern for API providers
- Context compression fallback
- Graceful degradation for tool failures
"""

from __future__ import annotations

import random
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from hermes_logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    retry_on_status: tuple = (429, 500, 502, 503, 504)


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for the given attempt number."""
    delay = config.base_delay * (config.exponential_base**attempt)
    delay = min(delay, config.max_delay)
    if config.jitter:
        delay = random.uniform(0, delay)
    return delay


def retry(
    func: Callable[..., T], config: Optional[RetryConfig] = None, *args, **kwargs
) -> T:
    """Execute func with retry logic.

    Args:
        func: Callable to execute.
        config: Retry configuration (uses defaults if None).
        *args: Positional arguments for func.
        **kwargs: Keyword arguments for func.

    Returns:
        The result of func.

    Raises:
        The last exception if all retries are exhausted.
    """
    cfg = config or RetryConfig()
    last_exc = None

    for attempt in range(cfg.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except cfg.retryable_exceptions as exc:
            last_exc = exc
            if attempt < cfg.max_retries:
                delay = _calculate_delay(attempt, cfg)
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.2fs",
                    attempt + 1,
                    cfg.max_retries + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "All %d retries exhausted. Last error: %s",
                    cfg.max_retries + 1,
                    exc,
                )

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    """Circuit breaker for API providers.

    States:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: Too many failures, requests fail fast.
    - HALF_OPEN: Testing if service recovered, one request allowed.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (
                    self._last_failure_time
                    and (time.time() - self._last_failure_time)
                    >= self.config.recovery_timeout
                ):
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(
                        "Circuit breaker '%s' transitioning to HALF_OPEN", self.name
                    )
            return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute func through the circuit breaker.

        Raises:
            CircuitBreakerOpenError: If circuit is open and recovery timeout hasn't elapsed.
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable, try again later."
            )

        if current_state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN, max test calls reached."
                    )
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._success_count = 0
                    logger.info("Circuit breaker '%s' CLOSED (recovered)", self.name)

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(
                    "Circuit breaker '%s' OPEN (half-open test failed)", self.name
                )
            elif self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker '%s' OPEN (%d consecutive failures)",
                    self.name,
                    self._failure_count,
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info("Circuit breaker '%s' manually reset to CLOSED", self.name)

    def get_status(self) -> Dict[str, Any]:
        """Return current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is open and rejects a call."""

    pass


# ---------------------------------------------------------------------------
# Circuit Breaker Registry
# ---------------------------------------------------------------------------

_circuit_breakers: Dict[str, CircuitBreaker] = {}
_cb_lock = threading.Lock()


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _cb_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers to CLOSED."""
    with _cb_lock:
        for cb in _circuit_breakers.values():
            cb.reset()


def get_all_circuit_breaker_statuses() -> Dict[str, Dict[str, Any]]:
    """Return status of all circuit breakers."""
    with _cb_lock:
        return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


# ---------------------------------------------------------------------------
# Context Compression Fallback
# ---------------------------------------------------------------------------


def compress_context_fallback(
    messages: list,
    system_message: Optional[dict] = None,
    keep_last_n: int = 5,
) -> list:
    """Fallback context compression when the primary compressor fails.

    Strategy: Keep system message + last N messages.
    This is a simple truncation that preserves conversation continuity.

    Args:
        messages: Full conversation history.
        system_message: Optional system message to preserve.
        keep_last_n: Number of recent messages to keep.

    Returns:
        Truncated message list.
    """
    compressed = []

    if system_message:
        compressed.append(system_message)

    # Keep the last N messages
    recent = messages[-keep_last_n:] if len(messages) > keep_last_n else messages
    compressed.extend(recent)

    logger.warning(
        "Context compression fallback: truncated to %d messages (kept last %d)",
        len(compressed),
        keep_last_n,
    )

    return compressed


# ---------------------------------------------------------------------------
# Graceful Tool Failure Handling
# ---------------------------------------------------------------------------


@dataclass
class ToolFailureRecord:
    """Record of a tool failure for tracking."""

    tool_name: str
    error: str
    timestamp: float = field(default_factory=time.time)
    turn: int = 0


class ToolFailureTracker:
    """Tracks tool failures per turn to enforce limits."""

    def __init__(self, max_failures_per_turn: int = 3):
        self.max_failures_per_turn = max_failures_per_turn
        self._failures: list = []
        self._lock = threading.Lock()

    def record_failure(self, tool_name: str, error: str, turn: int = 0) -> None:
        """Record a tool failure."""
        with self._lock:
            self._failures.append(
                ToolFailureRecord(tool_name, error, time.time(), turn)
            )

    def should_continue(self, turn: int = 0) -> bool:
        """Check if we should continue trying tools this turn."""
        with self._lock:
            turn_failures = [f for f in self._failures if f.turn == turn]
            return len(turn_failures) < self.max_failures_per_turn

    def get_failure_summary(self, turn: int = 0) -> str:
        """Get a summary of failures for the current turn."""
        with self._lock:
            turn_failures = [f for f in self._failures if f.turn == turn]
            if not turn_failures:
                return ""
            parts = [f"{f.tool_name}: {f.error}" for f in turn_failures]
            return f"{len(turn_failures)} tool failures this turn: " + "; ".join(parts)

    def reset_turn(self, turn: int) -> None:
        """Clear failures for a specific turn."""
        with self._lock:
            self._failures = [f for f in self._failures if f.turn != turn]

    def clear(self) -> None:
        """Clear all failure records."""
        with self._lock:
            self._failures.clear()


def handle_tool_failure(
    tool_name: str,
    error: str,
    tracker: Optional[ToolFailureTracker] = None,
    turn: int = 0,
) -> str:
    """Handle a tool failure and return a user-friendly error message.

    Args:
        tool_name: Name of the failed tool.
        error: Error message.
        tracker: Optional failure tracker.
        turn: Current turn number.

    Returns:
        Error message to return to the model.
    """
    if tracker:
        tracker.record_failure(tool_name, error, turn)

    msg = f"Tool '{tool_name}' failed: {error}"
    if tracker and not tracker.should_continue(turn):
        msg += f"\n\nMaximum tool failures ({tracker.max_failures_per_turn}) reached this turn. Please proceed without tools."

    logger.error(msg)
    return msg
