"""Aizen HTTP API Server - FastAPI-based REST API.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8000

Endpoints:
    POST /chat              - Single message, returns response
    POST /chat/stream       - Streaming via Server-Sent Events
    WebSocket /ws           - Bidirectional chat
    GET /health             - Health check
    GET /docs               - OpenAPI documentation
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(
    title="Aizen Agent API",
    description="REST API for Aizen AI Agent",
    version="1.0.0",
)

# Configuration
API_KEY = os.getenv("AIZEN_API_KEY", "")
DEFAULT_MODEL = os.getenv("AIZEN_DEFAULT_MODEL", "anthropic/claude-sonnet-4")


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    session_id: Optional[str] = None
    tools: Optional[List[str]] = None


class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    model: str


class HealthResponse(BaseModel):
    status: str
    model: str


# Session storage (simple in-memory for now)
_sessions: Dict[str, "Agent"] = {}


def verify_api_key(x_api_key: Optional[str] = None) -> bool:
    """Verify API key if configured."""
    if not API_KEY:
        return True  # No auth required if not configured
    return x_api_key == API_KEY


def get_agent(session_id: Optional[str] = None, model: Optional[str] = None, tools: Optional[List[str]] = None) -> "Agent":
    """Get or create agent for session."""
    from sdk import Agent
    
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    
    agent = Agent(
        model=model or DEFAULT_MODEL,
        tools=tools,
    )
    
    if session_id:
        _sessions[session_id] = agent
    
    return agent


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", model=DEFAULT_MODEL)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Send a message and get a response."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    agent = get_agent(
        session_id=request.session_id,
        model=request.model,
        tools=request.tools,
    )
    
    response = await agent.achat(request.message)
    
    return ChatResponse(
        response=response,
        session_id=request.session_id,
        model=agent.model,
    )


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Stream response via Server-Sent Events."""
    if not verify_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    agent = get_agent(
        session_id=request.session_id,
        model=request.model,
        tools=request.tools,
    )
    
    async def generate() -> AsyncIterator[str]:
        """Generate SSE events."""
        async for chunk in agent.astream(request.message):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket bidirectional chat."""
    await websocket.accept()
    
    agent = get_agent()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                text = message.get("text", "")
                if not text.strip():
                    continue
                
                # Stream response
                async for chunk in agent.astream(text):
                    await websocket.send_json({"chunk": chunk})
                
                await websocket.send_json({"done": True})
                
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    
    except WebSocketDisconnect:
        pass


@app.on_event("startup")
async def startup():
    """Startup event - preload agent."""
    # Preload to warm up imports
    get_agent()


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event - cleanup."""
    _sessions.clear()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
