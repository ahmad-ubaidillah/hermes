"""Doom loop detection for Aizen Agent.

Detects when the agent repeatedly calls the same tool with the same arguments,
causing an infinite loop. Breaks the loop and notifies the user.
"""

import hashlib
import logging
from collections import deque
from typing import Any, Deque, Dict, Optional

logger = logging.getLogger(__name__)


class DoomLoopDetector:
    """Detects doom loops in agent tool execution."""

    def __init__(
        self,
        history_size: int = 10,
        threshold: int = 3,
        backoff_multiplier: float = 1.5,
        max_backoff: int = 30,
    ):
        """Initialize doom loop detector.

        Args:
            history_size: Number of recent tool calls to track
            threshold: Number of identical calls before triggering doom loop
            backoff_multiplier: Multiplier for exponential backoff
            max_backoff: Maximum backoff time in seconds
        """
        self.history_size = history_size
        self.threshold = threshold
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff

        self._call_history: Deque[str] = deque(maxlen=history_size)
        self._call_counts: Dict[str, int] = {}
        self._last_call_time: Dict[str, float] = {}
        self._consecutive_failures: Dict[str, int] = {}

    def _hash_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Create a hash for a tool call.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Hash string representing the call
        """
        args_str = str(sorted(args.items()))
        hash_input = f"{tool_name}:{args_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def record_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Record a tool call in history.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
        """
        call_hash = self._hash_call(tool_name, args)
        self._call_history.append(call_hash)

        if call_hash not in self._call_counts:
            self._call_counts[call_hash] = 0
        self._call_counts[call_hash] += 1

    def check_doom_loop(
        self, tool_name: str, args: Dict[str, Any], result: str
    ) -> Optional[Dict[str, Any]]:
        """Check if a doom loop is detected.

        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Tool execution result

        Returns:
            Doom loop info dict if detected, None otherwise
        """
        call_hash = self._hash_call(tool_name, args)
        call_count = self._call_counts.get(call_hash, 0)

        if call_count >= self.threshold:
            is_error = "error" in result.lower() or "failed" in result.lower()

            if is_error:
                if call_hash not in self._consecutive_failures:
                    self._consecutive_failures[call_hash] = 0
                self._consecutive_failures[call_hash] += 1
            else:
                self._consecutive_failures[call_hash] = 0

            consecutive_failures = self._consecutive_failures.get(call_hash, 0)

            if consecutive_failures >= self.threshold - 1:
                logger.warning(
                    f"Doom loop detected: {tool_name} called {call_count} times "
                    f"with {consecutive_failures} consecutive failures"
                )

                return {
                    "detected": True,
                    "tool_name": tool_name,
                    "call_count": call_count,
                    "consecutive_failures": consecutive_failures,
                    "message": (
                        f"Doom loop detected: {tool_name} has been called "
                        f"{call_count} times with {consecutive_failures} consecutive failures. "
                        f"Consider a different approach."
                    ),
                }

        return None

    def get_call_count(self, tool_name: str, args: Dict[str, Any]) -> int:
        """Get the number of times a specific call has been made.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Number of times this call has been made
        """
        call_hash = self._hash_call(tool_name, args)
        return self._call_counts.get(call_hash, 0)

    def reset(self) -> None:
        """Reset the doom loop detector state."""
        self._call_history.clear()
        self._call_counts.clear()
        self._last_call_time.clear()
        self._consecutive_failures.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get doom loop detector statistics.

        Returns:
            Dict with stats
        """
        return {
            "history_size": len(self._call_history),
            "unique_calls": len(self._call_counts),
            "max_calls": max(self._call_counts.values()) if self._call_counts else 0,
        }


_default_detector: Optional[DoomLoopDetector] = None


def get_doom_detector() -> DoomLoopDetector:
    """Get the default doom loop detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = DoomLoopDetector()
    return _default_detector


def init_doom_detector(
    history_size: int = 10,
    threshold: int = 3,
    backoff_multiplier: float = 1.5,
    max_backoff: int = 30,
) -> DoomLoopDetector:
    """Initialize the default doom loop detector.

    Args:
        history_size: Number of recent tool calls to track
        threshold: Number of identical calls before triggering doom loop
        backoff_multiplier: Multiplier for exponential backoff
        max_backoff: Maximum backoff time in seconds

    Returns:
        Initialized DoomLoopDetector instance
    """
    global _default_detector
    _default_detector = DoomLoopDetector(
        history_size=history_size,
        threshold=threshold,
        backoff_multiplier=backoff_multiplier,
        max_backoff=max_backoff,
    )
    return _default_detector
