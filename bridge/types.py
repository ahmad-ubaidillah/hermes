"""Pydantic models for Aizen Bridge message protocol."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages in the Bridge protocol."""

    # Client → Server
    AUTH = "auth"
    CHAT = "chat"
    CHAT_STREAM = "chat_stream"
    SESSION_LIST = "session_list"
    SESSION_GET = "session_get"
    TOOLS_LIST = "tools_list"
    MODELS_LIST = "models_list"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    PING = "ping"

    # Server → Client
    AUTH_OK = "auth_ok"
    AUTH_ERROR = "auth_error"
    CHUNK = "chunk"
    DONE = "done"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PONG = "pong"
    FILE_CONTENT = "file_content"


class AuthToken(BaseModel):
    """JWT authentication token payload."""

    token: str = Field(..., description="JWT token string")


class ChatRequest(BaseModel):
    """Request to send a message to Aizen."""

    message: str = Field(..., min_length=1, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID to use/create")
    model: Optional[str] = Field(None, description="Model override")
    stream: bool = Field(False, description="Stream response chunks")
    tools: Optional[List[str]] = Field(None, description="Enabled toolsets")


class ChatResponse(BaseModel):
    """Complete response from Aizen."""

    response: str = Field(..., description="Full response text")
    session_id: Optional[str] = Field(None, description="Session ID used")
    model: str = Field(..., description="Model that generated the response")
    tokens: Optional[int] = Field(None, description="Total tokens used")
    duration: Optional[float] = Field(None, description="Response time in seconds")


class SessionInfo(BaseModel):
    """Session metadata."""

    id: str
    source: str = "bridge"
    model: Optional[str] = None
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    message_count: int = 0
    tool_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    title: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    model: Optional[str] = None
    sessions_active: int = 0
    uptime: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class ToolCall(BaseModel):
    """Tool call from the agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from a tool execution."""

    id: str
    success: bool
    output: str = ""
    error: Optional[str] = None


class StreamChunk(BaseModel):
    """Streaming response chunk."""

    chunk: str = Field(..., description="Text chunk")
    session_id: Optional[str] = None
    tool_call: Optional[ToolCall] = None


class StreamDone(BaseModel):
    """Signal that streaming is complete."""

    session_id: Optional[str] = None
    total_tokens: Optional[int] = None
    duration: Optional[float] = None


class ErrorPayload(BaseModel):
    """Error response."""

    code: str = "unknown_error"
    message: str
    details: Optional[Dict[str, Any]] = None


class BridgeMessage(BaseModel):
    """Generic Bridge message wrapper for WebSocket protocol."""

    type: MessageType
    data: Optional[Dict[str, Any]] = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = Field(default_factory=time.time)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json

        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "BridgeMessage":
        """Deserialize from JSON string."""
        import json

        data = json.loads(json_str)
        return cls(**data)
