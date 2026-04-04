"""Permission system for Aizen Agent.

Provides ruleset-based permission system with allow/deny/ask modes per tool.
Supports wildcard patterns (e.g., web* matches webfetch, websearch).
"""

import fnmatch
import logging
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class PermissionMode(Enum):
    """Permission modes for tool execution."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionResult(Enum):
    """Result of permission check."""

    ALLOWED = "allowed"
    DENIED = "denied"
    ASKED = "asked"


class PermissionConfig:
    """Permission configuration for a tool pattern."""

    def __init__(self, pattern: str, mode: str, description: Optional[str] = None):
        self.pattern = pattern
        self.mode = PermissionMode(mode.lower())
        self.description = description or f"Permission for {pattern}"


class PermissionSystem:
    """Ruleset-based permission system for tool execution."""

    def __init__(
        self,
        config: Optional[dict] = None,
        confirm_callback: Optional[Callable[[str, str], bool]] = None,
    ):
        """Initialize permission system.

        Args:
            config: Dict mapping tool patterns to permission modes
                   e.g., {"terminal": "ask", "web*": "allow", "dangerous": "deny"}
            confirm_callback: Callback function(tool_name, action) -> bool
                            Called when permission is "ask" mode.
                            Should return True if user confirms, False otherwise.
        """
        self._config = {}
        self._confirm_callback = confirm_callback

        if config:
            self.load_config(config)

    def load_config(self, config: dict) -> None:
        """Load permission configuration from dict.

        Args:
            config: Dict mapping tool patterns to permission modes.
                   Modes: "allow", "deny", "ask"
        """
        for pattern, mode in config.items():
            if isinstance(mode, str):
                self._config[pattern] = PermissionConfig(pattern, mode)
            elif isinstance(mode, dict):
                self._config[pattern] = PermissionConfig(
                    pattern, mode.get("mode", "allow"), mode.get("description")
                )

        logger.info(f"Loaded {len(self._config)} permission rules")

    def set_confirm_callback(self, callback: Callable[[str, str], bool]) -> None:
        """Set callback for user confirmation on 'ask' mode."""
        self._confirm_callback = callback

    def check_permission(
        self, tool_name: str, action: str = "execute"
    ) -> PermissionResult:
        """Check if tool execution is permitted.

        Args:
            tool_name: Name of the tool to check
            action: Action being performed (default: "execute")

        Returns:
            PermissionResult: ALLOWED, DENIED, or ASKED
        """
        matching_config = self._find_matching_config(tool_name)

        if matching_config is None:
            return PermissionResult.ALLOWED

        mode = matching_config.mode

        if mode == PermissionMode.ALLOW:
            logger.debug(
                f"Permission ALLOWED for {tool_name} (pattern: {matching_config.pattern})"
            )
            return PermissionResult.ALLOWED

        elif mode == PermissionMode.DENY:
            logger.debug(
                f"Permission DENIED for {tool_name} (pattern: {matching_config.pattern})"
            )
            return PermissionResult.DENIED

        elif mode == PermissionMode.ASK:
            if self._confirm_callback:
                confirmed = self._confirm_callback(tool_name, action)
                if confirmed:
                    logger.debug(f"Permission ASKED and CONFIRMED for {tool_name}")
                    return PermissionResult.ALLOWED
                else:
                    logger.debug(f"Permission ASKED and DENIED for {tool_name}")
                    return PermissionResult.DENIED
            else:
                logger.warning(
                    f"Permission ASKED for {tool_name} but no confirm callback set"
                )
                return PermissionResult.ASKED

    def _find_matching_config(self, tool_name: str) -> Optional[PermissionConfig]:
        """Find matching permission config for tool name.

        Supports wildcard patterns (e.g., web* matches webfetch).

        Args:
            tool_name: Name of the tool

        Returns:
            Matching PermissionConfig or None if no match
        """
        for pattern in self._config:
            if self._matches_pattern(tool_name, pattern):
                return self._config[pattern]
        return None

    def _matches_pattern(self, tool_name: str, pattern: str) -> bool:
        """Check if tool name matches pattern.

        Supports:
        - Exact match: "terminal" matches "terminal"
        - Wildcard: "web*" matches "webfetch", "websearch"
        - Suffix: "*_tool" matches "terminal_tool"

        Args:
            tool_name: Tool name to check
            pattern: Pattern to match against

        Returns:
            True if tool matches pattern
        """
        if fnmatch.fnmatch(tool_name.lower(), pattern.lower()):
            return True
        return False

    def get_config_for_tool(self, tool_name: str) -> Optional[PermissionConfig]:
        """Get permission config for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            PermissionConfig if found, None otherwise
        """
        return self._find_matching_config(tool_name)

    def list_permissions(self) -> dict:
        """List all permission rules.

        Returns:
            Dict mapping patterns to modes
        """
        return {pattern: config.mode.value for pattern, config in self._config.items()}


_default_permission_system: Optional[PermissionSystem] = None


def get_permission_system() -> PermissionSystem:
    """Get the default permission system instance."""
    global _default_permission_system
    if _default_permission_system is None:
        _default_permission_system = PermissionSystem()
    return _default_permission_system


def init_permission_system(
    config: Optional[dict] = None,
    confirm_callback: Optional[Callable[[str, str], bool]] = None,
) -> PermissionSystem:
    """Initialize the default permission system.

    Args:
        config: Permission configuration dict
        confirm_callback: Callback for user confirmation

    Returns:
        Initialized PermissionSystem instance
    """
    global _default_permission_system
    _default_permission_system = PermissionSystem(config, confirm_callback)
    return _default_permission_system


def check_tool_permission(tool_name: str, action: str = "execute") -> PermissionResult:
    """Quick function to check tool permission using default system.

    Args:
        tool_name: Name of the tool
        action: Action being performed

    Returns:
        PermissionResult
    """
    return get_permission_system().check_permission(tool_name, action)
