"""Self-healing execution system for Aizen Agent.

Automatically detects tool execution failures, analyzes tracebacks,
and retries with modified approach.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for self-healing."""

    SYNTAX_ERROR = "syntax"
    IMPORT_ERROR = "import"
    PERMISSION_ERROR = "permission"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""

    error_type: str
    error_message: str
    traceback: Optional[str] = None
    tool_name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class RepairStrategy:
    """A repair strategy to try."""

    name: str
    description: str
    apply: Callable[[ErrorContext], Tuple[bool, str]]
    priority: int = 0


class SelfHealingEngine:
    """Self-healing execution engine."""

    def __init__(
        self, max_retries: int = 3, base_backoff: float = 1.0, max_backoff: float = 30.0
    ):
        """Initialize self-healing engine.

        Args:
            max_retries: Maximum retry attempts
            base_backoff: Base backoff time in seconds
            max_backoff: Maximum backoff time in seconds
        """
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

        self._retry_counts: Dict[str, int] = {}
        self._repair_strategies: List[RepairStrategy] = []
        self._register_strategies()

    def _register_strategies(self) -> None:
        """Register built-in repair strategies."""

        self._repair_strategies.extend(
            [
                RepairStrategy(
                    name="fix_syntax",
                    description="Fix common syntax errors",
                    priority=10,
                    apply=self._fix_syntax_error,
                ),
                RepairStrategy(
                    name="fix_import",
                    description="Fix import errors",
                    priority=20,
                    apply=self._fix_import_error,
                ),
                RepairStrategy(
                    name="backoff",
                    description="Apply exponential backoff",
                    priority=50,
                    apply=self._apply_backoff,
                ),
                RepairStrategy(
                    name="skip_permission",
                    description="Skip or ask for permission errors",
                    priority=30,
                    apply=self._handle_permission_error,
                ),
            ]
        )

    def _categorize_error(self, error_context: ErrorContext) -> ErrorCategory:
        """Categorize the error type.

        Args:
            error_context: Error context

        Returns:
            ErrorCategory
        """
        error_msg = error_context.error_message.lower()

        if any(x in error_msg for x in ["syntaxerror", "syntax error", "expected"]):
            return ErrorCategory.SYNTAX_ERROR
        elif any(
            x in error_msg for x in ["importerror", "modulenotfound", "no module named"]
        ):
            return ErrorCategory.IMPORT_ERROR
        elif any(
            x in error_msg for x in ["permission denied", "access denied", "eacces"]
        ):
            return ErrorCategory.PERMISSION_ERROR
        elif any(x in error_msg for x in ["rate limit", "too many requests", "429"]):
            return ErrorCategory.RATE_LIMIT
        elif any(x in error_msg for x in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT
        elif any(x in error_msg for x in ["connection", "network", "socket"]):
            return ErrorCategory.NETWORK_ERROR

        return ErrorCategory.UNKNOWN

    def _fix_syntax_error(self, context: ErrorContext) -> Tuple[bool, str]:
        """Attempt to fix syntax errors.

        Args:
            error_context: Error context

        Returns:
            (success, message)
        """
        error_msg = context.error_message

        fix_patterns = [
            (r"unexpected EOF", "Missing closing parenthesis or bracket"),
            (r"invalid syntax", "Check for missing colons, parentheses, or brackets"),
            (r"unterminated string", "Add closing quote"),
            (r"expected '.*' before '.*'", "Check for incorrect keyword or operator"),
        ]

        for pattern, suggestion in fix_patterns:
            if re.search(pattern, error_msg, re.IGNORECASE):
                return False, f"Suggestion: {suggestion}"

        return False, "Could not auto-fix syntax error"

    def _fix_import_error(self, context: ErrorContext) -> Tuple[bool, str]:
        """Attempt to fix import errors.

        Args:
            error_context: Error context

        Returns:
            (success, message)
        """
        from src.agent.auto_install import extract_package_from_error, install_package

        package = extract_package_from_error(context.error_message)
        if package:
            success, msg = install_package(package)
            if success:
                return True, f"Installed missing package: {package}"
            return False, msg

        return False, "Could not identify package to install"

    def _apply_backoff(self, context: ErrorContext) -> Tuple[bool, str]:
        """Apply exponential backoff.

        Args:
            error_context: Error context

        Returns:
            (success, message)
        """
        key = context.tool_name or "default"
        retry_count = self._retry_counts.get(key, 0)

        if retry_count < self.max_retries:
            wait_time = min(self.base_backoff * (2**retry_count), self.max_backoff)
            logger.info(
                f"Backing off {wait_time}s before retry ({retry_count + 1}/{self.max_retries})"
            )
            time.sleep(wait_time)
            return True, f"Will retry after {wait_time}s backoff"

        return False, "Max retries exceeded"

    def _handle_permission_error(self, context: ErrorContext) -> Tuple[bool, str]:
        """Handle permission errors.

        Args:
            error_context: Error context

        Returns:
            (success, message)
        """
        return False, "Permission error - requires user intervention"

    def analyze_error(
        self, error: str, tool_name: str, args: Dict[str, Any]
    ) -> ErrorContext:
        """Analyze an error and categorize it.

        Args:
            error: Error message
            tool_name: Tool that caused the error
            args: Tool arguments

        Returns:
            ErrorContext
        """
        context = ErrorContext(
            error_type=self._categorize_error(
                ErrorContext(error_type="", error_message=error)
            ).value,
            error_message=error,
            tool_name=tool_name,
            args=args,
        )

        logger.info(f"Analyzed error: {context.error_type} for tool {tool_name}")
        return context

    def get_repair_strategy(
        self, error_context: ErrorContext
    ) -> Optional[RepairStrategy]:
        """Get the best repair strategy for an error.

        Args:
            error_context: Error context

        Returns:
            RepairStrategy or None
        """
        category = self._categorize_error(error_context)

        strategy_map = {
            ErrorCategory.SYNTAX_ERROR: "fix_syntax",
            ErrorCategory.IMPORT_ERROR: "fix_import",
            ErrorCategory.RATE_LIMIT: "backoff",
            ErrorCategory.TIMEOUT: "backoff",
            ErrorCategory.NETWORK_ERROR: "backoff",
            ErrorCategory.PERMISSION_ERROR: "skip_permission",
        }

        strategy_name = strategy_map.get(category)
        if strategy_name:
            for strategy in self._repair_strategies:
                if strategy.name == strategy_name:
                    return strategy

        return None

    def record_retry(self, tool_name: str) -> int:
        """Record a retry attempt.

        Args:
            tool_name: Tool name

        Returns:
            Current retry count
        """
        key = tool_name or "default"
        self._retry_counts[key] = self._retry_counts.get(key, 0) + 1
        return self._retry_counts[key]

    def should_retry(self, tool_name: str) -> bool:
        """Check if should retry.

        Args:
            tool_name: Tool name

        Returns:
            True if should retry
        """
        key = tool_name or "default"
        return self._retry_counts.get(key, 0) < self.max_retries

    def reset_retries(self, tool_name: Optional[str] = None) -> None:
        """Reset retry counts.

        Args:
            tool_name: Tool name (None to reset all)
        """
        if tool_name:
            key = tool_name or "default"
            self._retry_counts.pop(key, None)
        else:
            self._retry_counts.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get self-healing stats.

        Returns:
            Dict with stats
        """
        return {
            "max_retries": self.max_retries,
            "retry_counts": self._retry_counts,
            "strategies_count": len(self._repair_strategies),
        }


_default_self_healing: Optional[SelfHealingEngine] = None


def get_self_healing() -> SelfHealingEngine:
    """Get the default self-healing engine."""
    global _default_self_healing
    if _default_self_healing is None:
        _default_self_healing = SelfHealingEngine()
    return _default_self_healing


def init_self_healing(
    max_retries: int = 3, base_backoff: float = 1.0, max_backoff: float = 30.0
) -> SelfHealingEngine:
    """Initialize the default self-healing engine.

    Args:
        max_retries: Maximum retry attempts
        base_backoff: Base backoff time
        max_backoff: Maximum backoff time

    Returns:
        Initialized SelfHealingEngine
    """
    global _default_self_healing
    _default_self_healing = SelfHealingEngine(
        max_retries=max_retries, base_backoff=base_backoff, max_backoff=max_backoff
    )
    return _default_self_healing
