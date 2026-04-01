"""Circuit Breaker tool — provider-level API resilience.

Re-exports the core CircuitBreaker from hermes_resilience and adds
provider-aware convenience helpers so the agent loop can track
failures per provider/model combination without duplicating state.

Usage from run_agent.py:
    from tools.circuit_breaker import (
        get_provider_breaker,
        record_provider_success,
        record_provider_failure,
    )

    cb = get_provider_breaker(self.provider, self.model)
    if cb.state == CircuitState.OPEN:
        # skip API call, trigger fallback
    record_provider_success(self.provider, self.model)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Re-export core classes from hermes_resilience so callers can import
# from a single location.
from hermes_resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker,
    get_all_circuit_breaker_statuses,
    reset_all_circuit_breakers,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitState",
    "get_circuit_breaker",
    "get_all_circuit_breaker_statuses",
    "reset_all_circuit_breakers",
    "get_provider_breaker",
    "record_provider_success",
    "record_provider_failure",
    "get_all_provider_statuses",
]

# ---------------------------------------------------------------------------
# Provider-aware helpers
# ---------------------------------------------------------------------------

_default_cb_config: Optional[CircuitBreakerConfig] = None


def _cb_key(provider: str, model: str) -> str:
    """Build a unique circuit-breaker key for a provider/model pair."""
    return f"{provider}/{model}"


def get_provider_breaker(
    provider: str,
    model: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """Get or create a CircuitBreaker for the given provider/model.

    Args:
        provider: Provider identifier (e.g. "openrouter", "anthropic").
        model: Model string (e.g. "anthropic/claude-opus-4.6").
        config: Optional custom config; defaults to 5 failures / 60s recovery.

    Returns:
        CircuitBreaker instance for this provider/model.
    """
    key = _cb_key(provider, model)
    cb_cfg = config or _default_cb_config
    return get_circuit_breaker(key, config=cb_cfg)


def record_provider_success(provider: str, model: str) -> None:
    """Record a successful API call for the given provider/model."""
    key = _cb_key(provider, model)
    cb = get_circuit_breaker(key)
    # Simulate success by calling the internal _on_success.
    # The public .call() wrapper is used for direct function invocation,
    # but the agent loop calls the API itself and just records outcomes.
    cb._on_success()


def record_provider_failure(provider: str, model: str) -> None:
    """Record a failed API call for the given provider/model."""
    key = _cb_key(provider, model)
    cb = get_circuit_breaker(key)
    cb._on_failure()


def get_all_provider_statuses() -> Dict[str, Dict[str, Any]]:
    """Return status of all provider circuit breakers."""
    return get_all_circuit_breaker_statuses()
