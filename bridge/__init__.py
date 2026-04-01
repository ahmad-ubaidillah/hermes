"""Hermes Bridge - Remote WebSocket bridge for Hermes Agent.

Enables remote clients (VS Code, web UI, mobile apps) to connect to a
Hermes Agent instance running on a server/VPS.

Architecture:
    ┌─────────────────┐         WebSocket         ┌─────────────────┐
    │   Hermes Server │ ◄────────────────────────► │  Remote Client  │
    │   (Cloud/VPS)   │         JWT Auth           │  (Laptop/Phone) │
    │                 │                            │                 │
    │  • AIAgent      │     Session State          │  • Web UI       │
    │  • Tools        │ ◄────────────────────────► │  • CLI          │
    │  • Sessions     │     Tool Results           │  • VS Code      │
    │  • Gateway      │                            │  • Mobile App   │
    └─────────────────┘                            └─────────────────┘

Usage:
    # Start bridge server
    python -m bridge.server --port 8765 --jwt-secret "your-secret"

    # Connect with client
    from bridge.client import BridgeClient
    client = BridgeClient("ws://localhost:8765", token="jwt...")
    response = client.chat("Hello Hermes!")
"""

from __future__ import annotations

__version__ = "1.0.0"

# Public API
from bridge.types import (
    BridgeMessage,
    ChatRequest,
    ChatResponse,
    SessionInfo,
    HealthResponse,
    AuthToken,
    ToolCall,
    ToolResult,
    StreamChunk,
    StreamDone,
    ErrorPayload,
    MessageType,
)
from bridge.config import BridgeConfig, load_bridge_config

__all__ = [
    # Types
    "BridgeMessage",
    "ChatRequest",
    "ChatResponse",
    "SessionInfo",
    "HealthResponse",
    "AuthToken",
    "ToolCall",
    "ToolResult",
    "StreamChunk",
    "StreamDone",
    "ErrorPayload",
    "MessageType",
    # Config
    "BridgeConfig",
    "load_bridge_config",
]
