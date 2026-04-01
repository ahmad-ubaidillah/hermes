"""Hermes Bridge Server - FastAPI + WebSocket remote bridge.

Starts a bridge server that allows remote clients to interact with
Hermes Agent via REST API and WebSocket connections.

Usage:
    python -m bridge.server                    # Default settings
    python -m bridge.server --port 8765        # Custom port
    python -m bridge.server --jwt-secret "key" # With JWT auth

Endpoints:
    POST /chat              - Send message, get response
    POST /chat/stream       - Stream response via SSE
    GET  /health            - Health check
    GET  /sessions          - List active sessions
    GET  /sessions/{id}     - Get session details
    GET  /tools             - List available tools
    GET  /models            - List available models
    WS   /ws/{session_id}   - WebSocket streaming connection
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from bridge.config import BridgeConfig, load_bridge_config
from bridge.types import (
    ChatRequest,
    ChatResponse,
    SessionInfo,
    HealthResponse,
    BridgeMessage,
    MessageType,
    StreamChunk,
    StreamDone,
    ErrorPayload,
    ToolCall,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bridge.server")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
START_TIME = time.time()
config: BridgeConfig = None  # Set in main()


# ---------------------------------------------------------------------------
# Session Manager — tracks active sessions and connected WebSocket clients
# ---------------------------------------------------------------------------
class SessionManager:
    """Manages bridge sessions and WebSocket connections."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._ws_clients: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._agents: Dict[str, Any] = {}  # session_id -> AIAgent
        self._lock = asyncio.Lock()

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    async def register_session(self, session_id: str, model: str = None) -> SessionInfo:
        """Register a new bridge session."""
        async with self._lock:
            now = time.time()
            self._sessions[session_id] = {
                "id": session_id,
                "model": model or config.default_model,
                "started_at": now,
                "message_count": 0,
                "source": "bridge",
            }
            return SessionInfo(
                id=session_id,
                model=model or config.default_model,
                started_at=now,
            )

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        async with self._lock:
            data = self._sessions.get(session_id)
            if not data:
                return None
            return SessionInfo(**data)

    async def list_sessions(self) -> List[SessionInfo]:
        async with self._lock:
            return [SessionInfo(**s) for s in self._sessions.values()]

    async def add_client(self, session_id: str, ws: WebSocket):
        """Add a WebSocket client to a session."""
        async with self._lock:
            self._ws_clients[session_id].add(ws)
            # Auto-register session if not exists
            if session_id not in self._sessions:
                await self.register_session(session_id)

    def remove_client(self, session_id: str, ws: WebSocket):
        """Remove a WebSocket client from a session."""
        self._ws_clients[session_id].discard(ws)
        if not self._ws_clients[session_id]:
            del self._ws_clients[session_id]

    async def broadcast(self, session_id: str, message: dict):
        """Broadcast a message to all clients in a session."""
        clients = list(self._ws_clients.get(session_id, set()))
        disconnected = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.remove_client(session_id, ws)

    def get_or_create_agent(self, session_id: str, model: str = None) -> Any:
        """Get or create an AIAgent for a session."""
        if session_id not in self._agents:
            try:
                from run_agent import AIAgent

                self._agents[session_id] = AIAgent(
                    model=model or config.default_model,
                    max_iterations=config.max_iterations,
                    quiet_mode=True,
                    session_id=session_id,
                )
                logger.info(
                    "Created agent for session %s (model=%s)", session_id, model
                )
            except Exception as e:
                logger.error("Failed to create agent for session %s: %s", session_id, e)
                raise
        return self._agents[session_id]


session_manager = SessionManager()


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self._minute_buckets: Dict[str, List[float]] = defaultdict(list)
        self._hour_buckets: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        # Clean old entries
        self._minute_buckets[client_id] = [
            t for t in self._minute_buckets[client_id] if now - t < 60
        ]
        self._hour_buckets[client_id] = [
            t for t in self._hour_buckets[client_id] if now - t < 3600
        ]
        if len(self._minute_buckets[client_id]) >= self.rpm:
            return False
        if len(self._hour_buckets[client_id]) >= self.rph:
            return False
        self._minute_buckets[client_id].append(now)
        self._hour_buckets[client_id].append(now)
        return True


rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# JWT Auth
# ---------------------------------------------------------------------------
def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    if not config.jwt_secret:
        return {"user_id": "anonymous"}  # No auth configured
    try:
        import jwt

        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
        )
        return payload
    except Exception as e:
        logger.warning("JWT verification failed: %s", e)
        return None


def verify_api_key_header(x_api_key: Optional[str] = None) -> bool:
    """Verify API key header if configured."""
    if not config.api_key:
        return True
    return x_api_key == config.api_key


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Hermes Bridge",
    description="WebSocket bridge for remote Hermes Agent access",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allow_origins if config else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        model=config.default_model if config else None,
        sessions_active=session_manager.active_session_count,
        uptime=time.time() - START_TIME,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Send a message and get a complete response."""
    if not verify_api_key_header(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Rate limiting
    if config and config.rate_limit.enabled:
        if not rate_limiter.is_allowed("rest"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    session_id = request.session_id or f"bridge_{int(time.time())}"

    try:
        agent = session_manager.get_or_create_agent(session_id, request.model)
        start = time.time()
        response = agent.chat(request.message)
        duration = time.time() - start

        return ChatResponse(
            response=response,
            session_id=session_id,
            model=request.model or config.default_model,
            duration=round(duration, 2),
        )
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Stream response via Server-Sent Events."""
    if not verify_api_key_header(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = request.session_id or f"bridge_{int(time.time())}"

    async def event_generator():
        try:
            agent = session_manager.get_or_create_agent(session_id, request.model)
            # Note: AIAgent.chat is synchronous; we stream the final response
            # For true streaming, use the WebSocket endpoint
            response = await asyncio.to_thread(agent.chat, request.message)
            yield f"data: {json.dumps({'chunk': response, 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    return await session_manager.list_sessions()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Try to get session from Hermes DB
    try:
        from core.hermes_state import SessionDB

        db = SessionDB()
        db_session = db.get_session(session_id)
        if db_session:
            session.message_count = db_session.get("message_count", 0)
    except Exception:
        pass

    return session


@app.get("/tools")
async def list_tools():
    """List available Hermes tools."""
    try:
        from tools.registry import registry

        tools = []
        for name in registry.get_all_tool_names():
            entry = registry._tools.get(name)
            tools.append(
                {
                    "name": name,
                    "description": entry.description if entry else "",
                    "toolset": entry.toolset if entry else "",
                }
            )
        return {"tools": sorted(tools, key=lambda x: x["name"]), "count": len(tools)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def list_models():
    """List available models."""
    try:
        from hermes_cli.models import OPENROUTER_MODELS

        models = [{"id": mid, "description": desc} for mid, desc in OPENROUTER_MODELS]
        return {"models": models, "count": len(models), "default": config.default_model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Bidirectional WebSocket connection for streaming chat.

    Protocol:
    1. Client connects to /ws/{session_id}
    2. First message must be auth: {"type": "auth", "token": "jwt..."}
    3. Subsequent messages: {"type": "chat", "message": "..."}
    4. Server streams: {"type": "chunk", "chunk": "..."}
    5. Server signals done: {"type": "done"}
    """
    await websocket.accept()

    # Authenticate (first message)
    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
    except asyncio.TimeoutError:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Authentication timeout",
            }
        )
        await websocket.close()
        return

    # Verify JWT if configured
    if config and config.has_auth:
        token = auth_data.get("token", "")
        if config.jwt_secret and not verify_jwt_token(token):
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Invalid authentication token",
                }
            )
            await websocket.close()
            return

    # Register client
    await session_manager.add_client(session_id, websocket)
    logger.info("Client connected to session %s", session_id)

    # Send welcome
    await websocket.send_json(
        {
            "type": "auth_ok",
            "session_id": session_id,
            "model": config.default_model if config else None,
        }
    )

    # Message loop
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat" or msg_type == "chat_stream":
                message = data.get("message", "")
                if not message.strip():
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Message cannot be empty",
                        }
                    )
                    continue

                # Rate limiting
                if config and config.rate_limit.enabled:
                    if not rate_limiter.is_allowed(session_id):
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "Rate limit exceeded",
                            }
                        )
                        continue

                try:
                    agent = session_manager.get_or_create_agent(
                        session_id, data.get("model")
                    )
                    # Run agent.chat in thread pool (it's synchronous)
                    response = await asyncio.to_thread(agent.chat, message)

                    # Stream the response back
                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "chunk": response,
                            "session_id": session_id,
                        }
                    )
                    await websocket.send_json(
                        {
                            "type": "done",
                            "session_id": session_id,
                        }
                    )

                    # Broadcast to other clients in the same session
                    await session_manager.broadcast(
                        session_id,
                        {
                            "type": "chunk",
                            "chunk": response,
                            "session_id": session_id,
                        },
                    )

                except Exception as e:
                    logger.error("WebSocket chat error: %s", e, exc_info=True)
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "tools_list":
                try:
                    from tools.registry import registry

                    tools = registry.get_all_tool_names()
                    await websocket.send_json(
                        {
                            "type": "tools_list",
                            "tools": sorted(tools),
                        }
                    )
                except Exception as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

            elif msg_type == "models_list":
                try:
                    from hermes_cli.models import OPENROUTER_MODELS

                    models = [mid for mid, _ in OPENROUTER_MODELS]
                    await websocket.send_json(
                        {
                            "type": "models_list",
                            "models": models,
                        }
                    )
                except Exception as e:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected from session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error in session %s: %s", session_id, e, exc_info=True)
    finally:
        session_manager.remove_client(session_id, websocket)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Start the bridge server."""
    import argparse

    global config
    parser = argparse.ArgumentParser(description="Hermes Bridge Server")
    parser.add_argument("--host", default=None, help="Bind address")
    parser.add_argument("--port", type=int, default=None, help="Listen port")
    parser.add_argument("--jwt-secret", default=None, help="JWT signing secret")
    parser.add_argument("--api-key", default=None, help="Simple API key")
    parser.add_argument("--default-model", default=None, help="Default model")
    parser.add_argument("--config", default=None, help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    # Load config
    config = load_bridge_config(args.config)

    # Override with CLI args
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.jwt_secret:
        config.jwt_secret = args.jwt_secret
    if args.api_key:
        config.api_key = args.api_key
    if args.default_model:
        config.default_model = args.default_model
    if args.debug:
        config.debug = True

    logger.info("Starting Hermes Bridge Server v1.0.0")
    logger.info("Config: %s", config.bind_address)
    logger.info(
        "Auth: %s",
        "JWT" if config.jwt_secret else "API Key" if config.api_key else "None",
    )
    logger.info("Model: %s", config.default_model)

    # Configure CORS middleware with actual config
    app.middleware_stack = None  # Force rebuild
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors.allow_origins,
        allow_methods=config.cors.allow_methods,
        allow_headers=config.cors.allow_headers,
    )

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        access_log=config.debug,
    )


if __name__ == "__main__":
    main()
