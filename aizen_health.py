"""Aizen Health Check Module

Provides:
- System health checks (API connectivity, session DB, disk space)
- Health status reporting (OK/DEGRADED/UNHEALTHY)
- Gateway health endpoint
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aizen_logging import get_logger, get_aizen_home

logger = get_logger(__name__)


class HealthStatus(Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class HealthReport:
    """Aggregate health report."""

    overall: HealthStatus
    checks: List[HealthCheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall.value,
            "timestamp": time.time(),
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Health Check Functions
# ---------------------------------------------------------------------------


def check_disk_space(
    path: Optional[str] = None, min_free_mb: int = 100
) -> HealthCheckResult:
    """Check available disk space."""
    check_path = path or str(get_aizen_home())
    try:
        usage = shutil.disk_usage(check_path)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < min_free_mb:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Low disk space: {free_mb:.1f}MB free (minimum: {min_free_mb}MB)",
                details={"free_mb": round(free_mb, 1), "min_mb": min_free_mb},
            )
        elif free_mb < min_free_mb * 5:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.DEGRADED,
                message=f"Disk space getting low: {free_mb:.1f}MB free",
                details={"free_mb": round(free_mb, 1)},
            )
        return HealthCheckResult(
            name="disk_space",
            status=HealthStatus.OK,
            message=f"Disk space OK: {free_mb:.0f}MB free",
            details={"free_mb": round(free_mb, 1)},
        )
    except Exception as e:
        return HealthCheckResult(
            name="disk_space",
            status=HealthStatus.UNHEALTHY,
            message=f"Failed to check disk space: {e}",
        )


def check_aizen_home() -> HealthCheckResult:
    """Check that AIZEN_HOME directory exists and is writable."""
    home = get_aizen_home()
    if not home.exists():
        return HealthCheckResult(
            name="aizen_home",
            status=HealthStatus.UNHEALTHY,
            message=f"AIZEN_HOME does not exist: {home}",
        )
    if not os.access(home, os.W_OK):
        return HealthCheckResult(
            name="aizen_home",
            status=HealthStatus.UNHEALTHY,
            message=f"AIZEN_HOME is not writable: {home}",
        )
    return HealthCheckResult(
        name="aizen_home",
        status=HealthStatus.OK,
        message=f"AIZEN_HOME OK: {home}",
        details={"path": str(home)},
    )


def check_session_db(session_db_path: Optional[str] = None) -> HealthCheckResult:
    """Check session database integrity."""
    try:
        from aizen_state import SessionDB

        db_path = session_db_path or str(get_aizen_home() / "sessions.db")
        db = SessionDB(db_path)
        # Try a simple query to verify DB is accessible
        db.get_session_count()
        return HealthCheckResult(
            name="session_db",
            status=HealthStatus.OK,
            message="Session database OK",
        )
    except ImportError:
        return HealthCheckResult(
            name="session_db",
            status=HealthStatus.DEGRADED,
            message="Session DB module not available",
        )
    except Exception as e:
        return HealthCheckResult(
            name="session_db",
            status=HealthStatus.UNHEALTHY,
            message=f"Session database error: {e}",
        )


def check_api_connectivity(
    provider: str = "openai", timeout: float = 5.0
) -> HealthCheckResult:
    """Check API connectivity for a provider."""
    try:
        import httpx

        urls = {
            "openai": "https://api.openai.com/v1/models",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "openrouter": "https://openrouter.ai/api/v1/models",
        }
        url = urls.get(provider)
        if not url:
            return HealthCheckResult(
                name=f"api_{provider}",
                status=HealthStatus.DEGRADED,
                message=f"Unknown provider: {provider}",
            )

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            # We just check connectivity, not auth
            if response.status_code in (200, 401, 403):
                return HealthCheckResult(
                    name=f"api_{provider}",
                    status=HealthStatus.OK,
                    message=f"API {provider} reachable",
                    details={"status_code": response.status_code},
                )
            return HealthCheckResult(
                name=f"api_{provider}",
                status=HealthStatus.DEGRADED,
                message=f"API {provider} returned {response.status_code}",
                details={"status_code": response.status_code},
            )
    except ImportError:
        return HealthCheckResult(
            name=f"api_{provider}",
            status=HealthStatus.DEGRADED,
            message="httpx not available for API check",
        )
    except Exception as e:
        return HealthCheckResult(
            name=f"api_{provider}",
            status=HealthStatus.UNHEALTHY,
            message=f"API {provider} unreachable: {e}",
        )


def check_config_validity(config: Optional[dict] = None) -> HealthCheckResult:
    """Check that configuration is valid."""
    try:
        from aizen_config import validate_config

        if config is None:
            from aizen_config import load_config

            config = load_config()
        errors = validate_config(config)
        if errors:
            return HealthCheckResult(
                name="config",
                status=HealthStatus.DEGRADED,
                message=f"Config has {len(errors)} validation error(s)",
                details={"errors": errors},
            )
        return HealthCheckResult(
            name="config",
            status=HealthStatus.OK,
            message="Configuration valid",
        )
    except ImportError:
        return HealthCheckResult(
            name="config",
            status=HealthStatus.DEGRADED,
            message="Config validation module not available",
        )
    except Exception as e:
        return HealthCheckResult(
            name="config",
            status=HealthStatus.UNHEALTHY,
            message=f"Config check failed: {e}",
        )


# ---------------------------------------------------------------------------
# Health Check Runner
# ---------------------------------------------------------------------------


class HealthChecker:
    """Runs all health checks and aggregates results."""

    def __init__(self):
        self._checks: List[Callable[[], HealthCheckResult]] = [
            check_aizen_home,
            check_disk_space,
            check_session_db,
        ]

    def add_check(self, check_fn: Callable[[], HealthCheckResult]) -> None:
        """Add a custom health check."""
        self._checks.append(check_fn)

    def run(self, include_api: bool = False) -> HealthReport:
        """Run all health checks and return aggregated report."""
        checks = list(self._checks)
        if include_api:
            checks.append(lambda: check_api_connectivity())

        results = []
        worst_status = HealthStatus.OK

        for check_fn in checks:
            try:
                result = check_fn()
                results.append(result)
                if result.status == HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.UNHEALTHY
                elif (
                    result.status == HealthStatus.DEGRADED
                    and worst_status != HealthStatus.UNHEALTHY
                ):
                    worst_status = HealthStatus.DEGRADED
            except Exception as e:
                results.append(
                    HealthCheckResult(
                        name=check_fn.__name__,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {e}",
                    )
                )
                worst_status = HealthStatus.UNHEALTHY

        return HealthReport(overall=worst_status, checks=results)


# Global health checker
_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Return the global health checker."""
    return _health_checker


def run_health_check(include_api: bool = False) -> HealthReport:
    """Run all health checks."""
    return _health_checker.run(include_api=include_api)
