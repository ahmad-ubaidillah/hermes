# Remote Bridge - Konsep dan Implementasi

## Apa itu Remote Bridge?

Remote Bridge adalah sistem yang memungkinkan Aizen berjalan di satu tempat (server/cloud), tapi bisa diakses dan dikontrol dari tempat lain (laptop, phone, VS Code, web app).

```
┌─────────────────┐         WebSocket         ┌─────────────────┐
│   Aizen Server │ ◄────────────────────────► │  Remote Client  │
│   (Cloud/VPS)   │         JWT Auth           │  (Laptop/Phone) │
│                 │                            │                 │
│  • AIAgent      │     Session State          │  • Web UI       │
│  • Tools        │ ◄────────────────────────► │  • CLI          │
│  • Sessions     │     Tool Results           │  • VS Code      │
│  • Gateway      │                            │  • Mobile App   │
└─────────────────┘                            └─────────────────┘
```

---

## Use Cases

### 1. **VS Code Extension**
```
User types in VS Code → Bridge → Aizen Server → Response → VS Code
```
Tanpa install Aizen lokal, cuma perlu extension.

### 2. **Web Dashboard**
```
Browser → WebSocket → Aizen Cloud → Tools → Response
```
Akses Aizen dari browser mana saja.

### 3. **Mobile Access**
```
Phone App → API Bridge → Aizen VPS → Notifications → Phone
```
Control Aizen dari HP.

### 4. **Multi-Device Session**
```
Laptop: "Continue working on project X"
Phone: "Show me the status"
Both share same session via Bridge
```

### 5. **Team Collaboration**
```
Developer A: Runs command
Developer B: Sees output in real-time
Same Aizen instance, different clients
```

---

## Claude Code Bridge Architecture (31 modules)

Dari file `bridge.json`, Claude Code punya:

| Module | Fungsi |
|--------|--------|
| `bridgeApi.ts` | REST API endpoints |
| `bridgeConfig.ts` | Konfigurasi bridge |
| `bridgeMessaging.ts` | Message protocol |
| `jwtUtils.ts` | JWT authentication |
| `remoteBridgeCore.ts` | Core remote connection |
| `codeSessionApi.ts` | Session management |
| `createSession.ts` | Create new sessions |
| `inboundMessages.ts` | Handle incoming messages |
| `inboundAttachments.ts` | Handle file attachments |
| `capacityWake.ts` | Wake on demand |
| `flushGate.ts` | Rate limiting |
| `replBridge.ts` | REPL over bridge |

---

## Aizen Implementation Plan

### Phase 1: Basic Bridge Server

```python
# bridge/server.py

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt
import asyncio

app = FastAPI(title="Aizen Bridge")
security = HTTPBearer()

# JWT Authentication
def verify_token(credentials):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

# REST API for simple commands
@app.post("/chat")
async def chat(message: str, user_id: str = Depends(verify_token)):
    """Send message to Aizen, get response."""
    agent = get_agent(user_id)
    response = await agent.achat(message)
    return {"response": response}

# WebSocket for streaming
@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """Bidirectional streaming connection."""
    await websocket.accept()
    
    # Verify JWT
    token = await websocket.receive_text()  # First message = token
    user_id = verify_token(token)
    
    agent = get_agent(user_id, session_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Stream response
            async for chunk in agent.astream(data["message"]):
                await websocket.send_json({"chunk": chunk})
            
            await websocket.send_json({"done": True})
    except WebSocketDisconnect:
        save_session(session_id)
```

### Phase 2: Session Sync

```python
# bridge/session_sync.py

class BridgeSession:
    """Sync session state across clients."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.clients: List[WebSocket] = []
        self.history: List[dict] = []
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        for client in self.clients:
            await client.send_json(message)
    
    async def add_client(self, ws: WebSocket):
        """New client joins session."""
        self.clients.append(ws)
        # Send history
        for msg in self.history:
            await ws.send_json(msg)
    
    async def handle_message(self, message: dict):
        """Process and broadcast message."""
        self.history.append(message)
        await self.broadcast(message)
```

### Phase 3: File Sync

```python
# bridge/file_sync.py

class FileSync:
    """Sync project files with remote client."""
    
    async def upload_file(self, path: str, content: bytes):
        """Client uploads file to Aizen workspace."""
        # Store in temp or project dir
        
    async def download_file(self, path: str) -> bytes:
        """Client downloads file from Aizen workspace."""
        
    async def watch_changes(self, ws: WebSocket):
        """Stream file changes to client."""
        # Use watchdog to detect changes
```

---

## Security Model

```
┌────────────┐     JWT Token      ┌────────────┐
│   Client   │ ─────────────────► │   Bridge   │
└────────────┘                    └────────────┘
                                       │
                                       ▼
                                  ┌────────────┐
                                  │  Aizen    │
                                  │  (isolated)│
                                  └────────────┘

JWT Token contains:
- user_id
- permissions (tools allowed)
- session_id
- expiry
```

---

## Comparison with Existing Aizen Features

| Feature | Aizen Current | Bridge Adds |
|---------|---------------|-------------|
| Gateway | Telegram/Discord/Slack | Web UI, VS Code |
| Sessions | SQLite local | Remote sync |
| Tools | Local execution | Remote execution |
| Files | Local filesystem | Remote file sync |
| Auth | Platform auth | JWT universal |

---

## Quick Start Implementation

Saya bisa buat implementasi sederhana dalam 1 file:

```bash
# Start bridge server
python bridge_server.py --port 8765 --secret-key "your-secret"

# Client connects
wscat -c ws://localhost:8765/ws/session-123
> {"type": "auth", "token": "jwt..."}
> {"type": "chat", "message": "Hello Aizen!"}
< {"type": "chunk", "content": "Hi! How can I help?"}
< {"type": "done"}
```

---

## Should We Build This?

### ✅ YES if:
- Kamu mau akses Aizen dari mana saja (web, mobile, VS Code)
- Kamu mau run Aizen di VPS, akses dari laptop/phone
- Kamu mau team collaboration real-time

### ❌ NO if:
- Kamu cuma pakai Aizen di satu laptop
- Kamu sudah puas dengan Telegram/Discord gateway
- Kamu tidak butuh remote access

---

## Estimated Effort

| Phase | Effort | Features |
|-------|--------|----------|
| Phase 1 | 2-3 hours | Basic REST + WebSocket |
| Phase 2 | 4-6 hours | Session sync, multi-client |
| Phase 3 | 8-12 hours | File sync, VS Code extension |

Mau saya implementasikan Phase 1 sekarang?
