"""Graceful shutdown handling for Hermes Agent.

Ensures clean shutdown on SIGTERM/SIGINT:
- Finish current tool call before exit
- Save session state
- Notify gateway users
- Cleanup resources
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Global shutdown state
_shutdown_requested = False
_shutdown_handlers: List[Callable] = []


def is_shutting_down() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested


def register_shutdown_handler(handler: Callable):
    """Register a handler to be called during shutdown."""
    _shutdown_handlers.append(handler)


def unregister_shutdown_handler(handler: Callable):
    """Unregister a shutdown handler."""
    if handler in _shutdown_handlers:
        _shutdown_handlers.remove(handler)


async def graceful_shutdown(timeout: float = 30.0):
    """Perform graceful shutdown.
    
    Args:
        timeout: Maximum seconds to wait for cleanup
    """
    global _shutdown_requested
    _shutdown_requested = True
    
    logger.info("Starting graceful shutdown (timeout=%ss)...", timeout)
    
    # Run handlers in reverse order
    for handler in reversed(_shutdown_handlers):
        try:
            result = handler()
            if asyncio.iscoroutine(result):
                await asyncio.wait_for(result, timeout=timeout)
        except Exception as e:
            logger.error("Shutdown handler failed: %s", e)
    
    logger.info("Graceful shutdown complete")


def _sync_shutdown():
    """Synchronous shutdown for signal handlers."""
    global _shutdown_requested
    _shutdown_requested = True
    
    # Run sync handlers
    for handler in reversed(_shutdown_handlers):
        try:
            if not asyncio.iscoroutinefunction(handler):
                handler()
        except Exception as e:
            logger.error("Shutdown handler failed: %s", e)


def setup_shutdown_handlers():
    """Setup signal handlers for graceful shutdown."""
    def handle_signal(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info("Received %s signal", sig_name)
        _sync_shutdown()
        
        # Exit after a short delay to allow logging
        import time
        time.sleep(0.5)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    # Ignore SIGPIPE (broken pipe)
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    except AttributeError:
        pass  # Windows doesn't have SIGPIPE


class ShutdownContext:
    """Context manager for cleanup on shutdown."""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if is_shutting_down():
            await asyncio.sleep(0.1)
        return False


# Auto-setup on import
setup_shutdown_handlers()
