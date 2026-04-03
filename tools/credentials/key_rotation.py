"""Key rotation tool — multi-key provider resilience.

Manages pools of API keys per provider, rotating on rate-limit errors
and tracking per-key health.  Designed to work alongside the existing
circuit breaker (which operates at the provider/model level) by adding
a per-key layer of resilience.

Usage from run_agent.py or gateway:

    from tools.key_rotation import get_key_pool

    pool = get_key_pool("openrouter")
    key = pool.get_next_key()        # returns an API key string
    pool.record_success(key)         # mark key healthy after successful call
    pool.record_rate_limit(key)      # trigger rotation on 429

Registration:
    This module auto-registers a ``key_rotation`` tool with the central
    registry so the agent can query key health via tool calling.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KeyHealth — per-key state
# ---------------------------------------------------------------------------


class KeyHealth:
    """Tracks the health and usage of a single API key."""

    __slots__ = (
        "key",
        "label",
        "successes",
        "failures",
        "rate_limits",
        "last_used",
        "last_rate_limit",
        "is_active",
        "total_calls",
    )

    def __init__(self, key: str, label: str = ""):
        self.key = key
        self.label = label or key[:12] + "..."
        self.successes: int = 0
        self.failures: int = 0
        self.rate_limits: int = 0
        self.last_used: float = 0.0
        self.last_rate_limit: float = 0.0
        self.is_active: bool = True
        self.total_calls: int = 0

    def health_score(self) -> float:
        """Return a health score between 0.0 (dead) and 1.0 (perfect).

        Heavily penalises recent rate limits; they decay over 5 minutes.
        """
        if self.total_calls == 0:
            return 1.0

        # Recent rate limit penalty (decays over 300 seconds)
        now = time.time()
        recent_penalty = 0.0
        if self.last_rate_limit > 0:
            age = now - self.last_rate_limit
            if age < 300:
                recent_penalty = (1 - age / 300) * 0.5 * min(self.rate_limits, 4)

        error_rate = (self.failures + self.rate_limits) / max(self.total_calls, 1)
        score = max(0.0, 1.0 - error_rate - recent_penalty)
        return round(score, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "is_active": self.is_active,
            "health_score": self.health_score(),
            "total_calls": self.total_calls,
            "successes": self.successes,
            "failures": self.failures,
            "rate_limits": self.rate_limits,
            "last_used": self.last_used,
        }


# ---------------------------------------------------------------------------
# KeyPool — manages multiple keys for a single provider
# ---------------------------------------------------------------------------


class KeyPool:
    """Manages a pool of API keys for one provider with rotation and health tracking.

    Keys are loaded from environment variables following the convention:
        {PROVIDER}_API_KEY          — primary key
        {PROVIDER}_API_KEY_2        — secondary key
        {PROVIDER}_API_KEY_3        — tertiary key
        ...

    For example, for OpenRouter:
        OPENROUTER_API_KEY
        OPENROUTER_API_KEY_2
        OPENROUTER_API_KEY_3
    """

    def __init__(self, provider: str, env_prefix: Optional[str] = None):
        self.provider = provider
        self._lock = threading.Lock()
        self._keys: List[KeyHealth] = []
        self._index: int = 0
        self._cooldown_seconds: float = 60.0  # how long to skip a rate-limited key

        self._load_from_env(env_prefix or provider.upper())

    # -- Loading --

    def _load_from_env(self, prefix: str) -> None:
        """Discover keys from environment variables."""
        # Primary key
        primary = os.getenv(f"{prefix}_API_KEY") or os.getenv(f"{prefix}_TOKEN")
        if primary:
            self._keys.append(KeyHealth(primary, label=f"{self.provider} (primary)"))

        # Numbered keys: _API_KEY_2, _API_KEY_3, ...
        for i in range(2, 20):
            key_val = os.getenv(f"{prefix}_API_KEY_{i}")
            if key_val:
                self._keys.append(KeyHealth(key_val, label=f"{self.provider} #{i}"))

        if len(self._keys) > 1:
            logger.info("KeyPool[%s]: loaded %d keys", self.provider, len(self._keys))

    def add_key(self, key: str, label: str = "") -> None:
        """Manually add a key to the pool."""
        with self._lock:
            # Avoid duplicates
            if any(k.key == key for k in self._keys):
                return
            self._keys.append(KeyHealth(key, label=label))

    # -- Rotation --

    def get_next_key(self) -> Optional[str]:
        """Return the next healthy API key, rotating past rate-limited ones.

        Returns None if no keys are available.
        """
        with self._lock:
            if not self._keys:
                return None

            if len(self._keys) == 1:
                # Single key — just return it (circuit breaker handles resilience)
                k = self._keys[0]
                k.last_used = time.time()
                k.total_calls += 1
                return k.key

            # Round-robin with cooldown for rate-limited keys
            attempts = 0
            total = len(self._keys)
            while attempts < total:
                idx = self._index % total
                self._index = (self._index + 1) % total
                attempts += 1

                k = self._keys[idx]
                if not k.is_active:
                    continue

                # Check cooldown after rate limit
                if k.last_rate_limit > 0:
                    elapsed = time.time() - k.last_rate_limit
                    if elapsed < self._cooldown_seconds:
                        continue
                    else:
                        # Cooldown expired — reactivate
                        k.is_active = True
                        k.last_rate_limit = 0.0

                k.last_used = time.time()
                k.total_calls += 1
                return k.key

            # All keys are in cooldown — return the one with the shortest remaining
            best = min(self._keys, key=lambda k: k.last_rate_limit)
            best.last_used = time.time()
            best.total_calls += 1
            return best.key

    # -- Health tracking --

    def record_success(self, key: str) -> None:
        """Record a successful API call for the given key."""
        with self._lock:
            for k in self._keys:
                if k.key == key:
                    k.successes += 1
                    k.is_active = True
                    return

    def record_failure(self, key: str) -> None:
        """Record a non-rate-limit failure."""
        with self._lock:
            for k in self._keys:
                if k.key == key:
                    k.failures += 1
                    return

    def record_rate_limit(self, key: str) -> None:
        """Record a rate-limit (429) and deactivate the key temporarily."""
        with self._lock:
            for k in self._keys:
                if k.key == key:
                    k.rate_limits += 1
                    k.last_rate_limit = time.time()
                    k.is_active = False
                    logger.warning(
                        "KeyPool[%s]: key %s rate-limited, rotating",
                        self.provider,
                        k.label,
                    )
                    return

    # -- Introspection --

    def get_health_report(self) -> Dict[str, Any]:
        """Return a health report for all keys in the pool."""
        with self._lock:
            return {
                "provider": self.provider,
                "total_keys": len(self._keys),
                "active_keys": sum(1 for k in self._keys if k.is_active),
                "keys": [k.to_dict() for k in self._keys],
            }

    def size(self) -> int:
        """Return the number of keys in the pool."""
        return len(self._keys)


# ---------------------------------------------------------------------------
# Global pool registry
# ---------------------------------------------------------------------------

_pools: Dict[str, KeyPool] = {}
_pools_lock = threading.Lock()


def get_key_pool(provider: str, env_prefix: Optional[str] = None) -> KeyPool:
    """Get or create a KeyPool for the given provider.

    Args:
        provider: Provider identifier (e.g. "openrouter", "anthropic").
        env_prefix: Environment variable prefix (defaults to provider.upper()).

    Returns:
        KeyPool instance for the provider.
    """
    key = provider.lower()
    if key not in _pools:
        with _pools_lock:
            if key not in _pools:
                _pools[key] = KeyPool(provider, env_prefix)
    return _pools[key]


def get_all_pool_reports() -> Dict[str, Dict[str, Any]]:
    """Return health reports for all key pools."""
    with _pools_lock:
        return {name: pool.get_health_report() for name, pool in _pools.items()}


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def _check_key_rotation() -> bool:
    """Tool is available if at least one provider has multiple keys."""
    with _pools_lock:
        return any(pool.size() > 1 for pool in _pools.values())


def key_rotation_tool(
    action: str = "status", provider: str = "", task_id: str = None
) -> str:
    """Query or manage API key pools.

    Args:
        action: One of "status", "health", "rotate", "add".
        provider: Provider name (e.g. "openrouter"). Empty = all providers.
    """
    try:
        if action == "status":
            if provider:
                pool = get_key_pool(provider)
                report = pool.get_health_report()
            else:
                report = get_all_pool_reports()
            return json.dumps({"success": True, "data": report})

        elif action == "health":
            if provider:
                pool = get_key_pool(provider)
                return json.dumps({"success": True, "data": pool.get_health_report()})
            else:
                return json.dumps({"success": True, "data": get_all_pool_reports()})

        elif action == "rotate":
            if provider:
                pool = get_key_pool(provider)
                with pool._lock:
                    pool._index = (pool._index + 1) % max(len(pool._keys), 1)
                return json.dumps(
                    {"success": True, "message": f"Rotated {provider} key pool"}
                )
            return json.dumps(
                {"success": False, "error": "Provider required for rotate action"}
            )

        elif action == "add":
            return json.dumps(
                {
                    "success": False,
                    "error": "Use the add_key() API directly — adding keys via tool call is not supported for security reasons",
                }
            )

        else:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown action: {action}. Valid actions: status, health, rotate",
                }
            )

    except Exception as e:
        logger.exception("key_rotation_tool error: %s", e)
        return json.dumps({"success": False, "error": str(e)})


registry.register(
    name="key_rotation",
    toolset="key_rotation",
    schema={
        "name": "key_rotation",
        "description": (
            "Query the health and status of API key pools for providers. "
            "Use action='status' to see all providers, action='health' for detailed health scores, "
            "action='rotate' to force rotation to the next key for a specific provider. "
            "Only available when multiple API keys are configured for a provider."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "health", "rotate"],
                    "description": "Action to perform: 'status' for overview, 'health' for detailed scores, 'rotate' to force key rotation",
                },
                "provider": {
                    "type": "string",
                    "description": "Provider name (e.g. 'openrouter', 'anthropic'). Leave empty for all providers.",
                },
            },
            "required": ["action"],
        },
    },
    handler=lambda args, **kw: key_rotation_tool(
        action=args.get("action", "status"),
        provider=args.get("provider", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=_check_key_rotation,
    requires_env=[],
    description="Query and manage API key pool health and rotation",
    emoji="🔑",
)
