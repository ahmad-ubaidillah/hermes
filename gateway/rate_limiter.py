"""Rate limiter for gateway message processing.

Provides per-user and per-chat rate limiting with configurable windows
(minute/hour) and cooldown periods.
"""

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    enabled: bool = True
    max_per_minute: int = 30
    max_per_hour: int = 200
    cooldown_seconds: int = 60


@dataclass
class RateLimitState:
    """Tracking state for a single user/chat."""

    minute_requests: list = field(default_factory=list)
    hour_requests: list = field(default_factory=list)
    cooldown_until: float = 0.0


class RateLimiter:
    """Per-user/chat rate limiter with sliding windows.

    Tracks request timestamps in sliding windows (1 minute, 1 hour) and
    enforces configurable limits. When a limit is exceeded, the user enters
    a cooldown period during which all requests are rejected.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self._config = config or RateLimitConfig()
        self._state: Dict[str, RateLimitState] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_dict(cls, config_dict: dict) -> "RateLimiter":
        """Create from gateway config dict."""
        rl_cfg = config_dict.get("rate_limiting", {})
        if not rl_cfg:
            return cls()
        cfg = RateLimitConfig(
            enabled=rl_cfg.get("enabled", True),
            max_per_minute=rl_cfg.get("max_per_minute", 30),
            max_per_hour=rl_cfg.get("max_per_hour", 200),
            cooldown_seconds=rl_cfg.get("cooldown_seconds", 60),
        )
        return cls(cfg)

    def check(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a request from user_id is allowed.

        Returns:
            (allowed, reason) - reason is None if allowed, error message if denied
        """
        if not self._config.enabled:
            return True, None

        now = time.time()

        with self._lock:
            state = self._state.get(user_id)
            if state is None:
                state = RateLimitState()
                self._state[user_id] = state

            # Check cooldown
            if state.cooldown_until > now:
                remaining = int(state.cooldown_until - now)
                return (
                    False,
                    f"Rate limited. Please wait {remaining}s before sending another message.",
                )

            # Clean old entries
            cutoff_minute = now - 60
            cutoff_hour = now - 3600
            state.minute_requests = [
                t for t in state.minute_requests if t > cutoff_minute
            ]
            state.hour_requests = [t for t in state.hour_requests if t > cutoff_hour]

            # Check per-minute limit
            if len(state.minute_requests) >= self._config.max_per_minute:
                state.cooldown_until = now + self._config.cooldown_seconds
                logger.warning(
                    "User %s hit per-minute rate limit (%d/%d)",
                    user_id,
                    len(state.minute_requests),
                    self._config.max_per_minute,
                )
                return False, (
                    f"Too many messages! You've sent {self._config.max_per_minute} messages "
                    f"in the last minute. Please wait {self._config.cooldown_seconds}s."
                )

            # Check per-hour limit
            if len(state.hour_requests) >= self._config.max_per_hour:
                state.cooldown_until = now + self._config.cooldown_seconds
                logger.warning(
                    "User %s hit per-hour rate limit (%d/%d)",
                    user_id,
                    len(state.hour_requests),
                    self._config.max_per_hour,
                )
                return False, (
                    f"Hourly limit reached ({self._config.max_per_hour} messages). "
                    f"Please wait {self._config.cooldown_seconds}s."
                )

            # Record request
            state.minute_requests.append(now)
            state.hour_requests.append(now)
            return True, None

    def get_usage(self, user_id: str) -> Dict[str, int]:
        """Get current usage stats for a user."""
        now = time.time()
        with self._lock:
            state = self._state.get(user_id)
            if state is None:
                return {"minute": 0, "hour": 0, "cooldown_remaining": 0}
            cutoff_minute = now - 60
            cutoff_hour = now - 3600
            minute_count = len([t for t in state.minute_requests if t > cutoff_minute])
            hour_count = len([t for t in state.hour_requests if t > cutoff_hour])
            cooldown = max(0, int(state.cooldown_until - now))
            return {
                "minute": minute_count,
                "hour": hour_count,
                "cooldown_remaining": cooldown,
                "max_per_minute": self._config.max_per_minute,
                "max_per_hour": self._config.max_per_hour,
            }

    def reset(self, user_id: str) -> None:
        """Reset rate limit state for a user."""
        with self._lock:
            self._state.pop(user_id, None)

    def reset_all(self) -> None:
        """Reset all rate limit state."""
        with self._lock:
            self._state.clear()

    def cleanup_stale(self, max_age_seconds: float = 7200) -> int:
        """Remove state entries older than max_age_seconds. Returns count removed."""
        now = time.time()
        with self._lock:
            stale = [
                uid
                for uid, state in self._state.items()
                if (
                    not state.minute_requests
                    or max(state.minute_requests + state.hour_requests + [0])
                    < now - max_age_seconds
                )
            ]
            for uid in stale:
                del self._state[uid]
            return len(stale)
