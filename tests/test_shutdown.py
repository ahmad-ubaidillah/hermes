"""Tests for Aizen Shutdown Module."""

import pytest
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestShutdownState:
    """Test shutdown state management."""
    
    def test_initial_state(self):
        """Test initial shutdown state."""
        from shutdown import is_shutting_down
        
        # Should be False initially
        assert is_shutting_down() is False
    
    def test_register_handler(self):
        """Test handler registration."""
        from shutdown import register_shutdown_handler, unregister_shutdown_handler
        
        called = []
        
        def handler():
            called.append(True)
        
        register_shutdown_handler(handler)
        unregister_shutdown_handler(handler)
        
        # Handler removed, list should stay empty
        assert called == []


class TestShutdownContext:
    """Test shutdown context manager."""
    
    def test_context_manager(self):
        """Test ShutdownContext works."""
        from shutdown import ShutdownContext
        
        async def test():
            async with ShutdownContext():
                pass
            return True
        
        import asyncio
        result = asyncio.run(test())
        assert result is True


class TestSignalHandlers:
    """Test signal handler setup."""
    
    def test_setup_handlers(self):
        """Test signal handlers can be set up."""
        from shutdown import setup_shutdown_handlers
        
        # Should not raise
        setup_shutdown_handlers()
        assert True
