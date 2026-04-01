"""Tests for Aizen Bridge Server."""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if FastAPI is available
try:
    import fastapi
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class TestBridgeTypes:
    """Test bridge type definitions."""
    
    def test_bridge_message_creation(self):
        """Test BridgeMessage can be created."""
        from bridge.types import BridgeMessage, MessageType
        
        msg = BridgeMessage(type=MessageType.CHAT, data={"message": "test"})
        assert msg.type == MessageType.CHAT
        assert msg.data["message"] == "test"
    
    def test_chat_request_defaults(self):
        """Test ChatRequest default values."""
        from bridge.types import ChatRequest
        
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id is None
    
    def test_health_response(self):
        """Test HealthResponse defaults."""
        from bridge.types import HealthResponse
        
        health = HealthResponse()
        assert health.status == "ok"


class TestBridgeConfig:
    """Test bridge configuration."""
    
    def test_default_config(self):
        """Test BridgeConfig default values."""
        from bridge.config import BridgeConfig
        
        config = BridgeConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8765
        assert config.debug is False
    
    def test_generate_jwt_secret(self):
        """Test JWT secret generation."""
        from bridge.config import generate_jwt_secret
        
        secret = generate_jwt_secret()
        assert len(secret) >= 32
        assert isinstance(secret, str)


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestBridgeServer:
    """Test bridge server functionality."""
    
    def test_app_creation(self):
        """Test FastAPI app can be created."""
        from bridge.server import app
        
        assert app is not None
        assert app.title == "Aizen Bridge"
    
    def test_routes_exist(self):
        """Test required routes exist."""
        from bridge.server import app
        
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        assert "/chat" in routes


class TestBridgeClient:
    """Test bridge client functionality."""
    
    def test_client_creation(self):
        """Test BridgeClient can be created."""
        from bridge.client import BridgeClient
        
        client = BridgeClient(base_url="http://localhost:8765")
        assert client.base_url == "http://localhost:8765"
