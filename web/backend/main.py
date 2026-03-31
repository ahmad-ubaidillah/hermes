"""
Hermes v3.0 Web Dashboard Backend - FastAPI

Features:
- Agent management (18 agents)
- Sprint/Kanban board
- Model usage tracking
- v3.0 features (IntentGate, Background Agents, Hooks)
- Real-time WebSocket updates
- Observability integration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json
import os
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = FastAPI(
    title="Hermes Dashboard v3.0",
    description="Web dashboard for Hermes AI Agent Team",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== MODELS ==============

class Agent(BaseModel):
    id: str
    name: str
    role: str
    tag: str
    status: str = "idle"
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tokens_used: int = 0
    last_activity: Optional[datetime] = None

class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str = "todo"
    assignee: Optional[str] = None
    priority: str = "medium"
    intent: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Sprint(BaseModel):
    id: str
    name: str
    status: str = "active"
    start_date: datetime
    end_date: Optional[datetime] = None
    tasks: List[str] = []

class Stats(BaseModel):
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    total_tokens: int
    remaining_budget: int
    v3_features: Dict[str, bool]

class IntentResult(BaseModel):
    intent: str
    confidence: float
    recommended_agent: str
    reasoning: str

class HookEvent(BaseModel):
    event: str
    agent: Optional[str] = None
    tool: Optional[str] = None
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None

# ============== DATA STORE ==============

# 18 Hermes Agents
AGENTS = {
    "Flash": Agent(id="flash", name="Flash", role="Quick Tasks", tag="[FLASH]"),
    "Hermes": Agent(id="hermes", name="Hermes", role="CEO - Decision Maker", tag="[CEO]"),
    "Biz": Agent(id="biz", name="Biz", role="Business Development", tag="[BIZ]"),
    "Pixel": Agent(id="pixel", name="Pixel", role="UI/UX Designer", tag="[DESIGN]"),
    "Nova": Agent(id="nova", name="Nova", role="Product Manager", tag="[PM]"),
    "Testa": Agent(id="testa", name="Testa", role="Quality Assurance", tag="[QA]"),
    "Atlas": Agent(id="atlas", name="Atlas", role="Architect", tag="[ARCH]"),
    "Cody": Agent(id="cody", name="Cody", role="Developer", tag="[DEV]"),
    "Deploya": Agent(id="deploya", name="Deploya", role="DevOps", tag="[OPS]"),
    "Query": Agent(id="query", name="Query", role="Database Admin", tag="[DBA]"),
    "Shield": Agent(id="shield", name="Shield", role="Security", tag="[SEC]"),
    "Scoutra": Agent(id="scoutra", name="Scoutra", role="Researcher", tag="[RESEARCH]"),
    "Crawla": Agent(id="crawla", name="Crawla", role="Web Crawler", tag="[CRAWLER]"),
    "Libra": Agent(id="libra", name="Libra", role="Knowledge Manager", tag="[KNOWLEDGE]"),
}

_tasks: Dict[str, Task] = {}
_sprints: Dict[str, Sprint] = {}
_hooks_log: List[HookEvent] = []
_model_usage: List[Dict] = []

# v3.0 Feature flags
_v3_features = {
    "intent_gate": True,
    "background_agents": True,
    "lifecycle_hooks": True,
    "hash_edit": True,
    "lsp_integration": False,
}

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
    
    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
    
    async def broadcast(self, msg: dict):
        for ws in self.connections:
            try:
                await ws.send_json(msg)
            except:
                pass

manager = ConnectionManager()

# ============== ROUTES ==============

@app.get("/")
async def root():
    return {
        "name": "Hermes Dashboard v3.0",
        "docs": "/docs",
        "websocket": "/ws",
    }

# --- Stats ---

@app.get("/api/stats", response_model=Stats)
async def get_stats():
    active = sum(1 for a in AGENTS.values() if a.status == "busy")
    completed = sum(1 for t in _tasks.values() if t.status == "done")
    tokens = sum(a.tokens_used for a in AGENTS.values())
    
    return Stats(
        total_agents=len(AGENTS),
        active_agents=active,
        total_tasks=len(_tasks),
        completed_tasks=completed,
        total_tokens=tokens,
        remaining_budget=550000 - tokens,
        v3_features=_v3_features,
    )

# --- Agents ---

@app.get("/api/agents")
async def list_agents():
    return list(AGENTS.values())

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise HTTPException(404, "Agent not found")
    return AGENTS[agent_id]

@app.post("/api/agents/{agent_id}/assign")
async def assign_task(agent_id: str, task_id: str):
    if agent_id not in AGENTS:
        raise HTTPException(404, "Agent not found")
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    
    AGENTS[agent_id].current_task = task_id
    AGENTS[agent_id].status = "busy"
    _tasks[task_id].assignee = agent_id
    _tasks[task_id].status = "in_progress"
    _tasks[task_id].updated_at = datetime.now()
    
    await manager.broadcast({
        "type": "agent_assigned",
        "agent": agent_id,
        "task": task_id,
    })
    
    return {"message": f"Task {task_id} assigned to {agent_id}"}

@app.post("/api/agents/{agent_id}/complete")
async def complete_task(agent_id: str, tokens_used: int = 0):
    if agent_id not in AGENTS:
        raise HTTPException(404, "Agent not found")
    
    agent = AGENTS[agent_id]
    task_id = agent.current_task
    
    if task_id and task_id in _tasks:
        _tasks[task_id].status = "done"
        _tasks[task_id].updated_at = datetime.now()
    
    agent.current_task = None
    agent.status = "idle"
    agent.tasks_completed += 1
    agent.tokens_used += tokens_used
    agent.last_activity = datetime.now()
    
    await manager.broadcast({
        "type": "task_completed",
        "agent": agent_id,
        "task": task_id,
    })
    
    return {"message": "Task completed"}

# --- Tasks ---

@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None, assignee: Optional[str] = None):
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t.status == status]
    if assignee:
        tasks = [t for t in tasks if t.assignee == assignee]
    return tasks

@app.post("/api/tasks")
async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    intent: Optional[str] = None,
):
    task_id = f"task_{len(_tasks) + 1}"
    now = datetime.now()
    
    # Use IntentGate if enabled and no intent provided
    if _v3_features["intent_gate"] and not intent:
        try:
            from routing.intent_gate import IntentGate
            gate = IntentGate()
            result = gate.analyze(title)
            intent = result.intent.value
        except:
            intent = "unknown"
    
    task = Task(
        id=task_id,
        title=title,
        description=description,
        priority=priority,
        intent=intent,
        created_at=now,
        updated_at=now,
    )
    
    _tasks[task_id] = task
    
    await manager.broadcast({
        "type": "task_created",
        "task": task.model_dump(),
    })
    
    return task

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, status: Optional[str] = None, assignee: Optional[str] = None):
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    
    task = _tasks[task_id]
    
    if status:
        task.status = status
        task.updated_at = datetime.now()
    
    if assignee:
        task.assignee = assignee
    
    await manager.broadcast({
        "type": "task_updated",
        "task": task.model_dump(),
    })
    
    return task

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(404, "Task not found")
    
    del _tasks[task_id]
    
    await manager.broadcast({
        "type": "task_deleted",
        "task_id": task_id,
    })
    
    return {"message": "Task deleted"}

# --- Sprints ---

@app.get("/api/sprints")
async def list_sprints():
    return list(_sprints.values())

@app.post("/api/sprints")
async def create_sprint(name: str):
    sprint_id = f"sprint_{len(_sprints) + 1}"
    
    sprint = Sprint(
        id=sprint_id,
        name=name,
        start_date=datetime.now(),
    )
    
    _sprints[sprint_id] = sprint
    
    return sprint

# --- v3.0 Features ---

@app.get("/api/v3/features")
async def get_v3_features():
    return _v3_features

@app.post("/api/v3/features")
async def set_v3_features(features: Dict[str, bool]):
    global _v3_features
    _v3_features.update(features)
    return _v3_features

@app.post("/api/v3/intent")
async def analyze_intent(text: str):
    """Analyze intent using IntentGate."""
    try:
        from routing.intent_gate import IntentGate
        gate = IntentGate()
        result = gate.analyze(text)
        return IntentResult(
            intent=result.intent.value,
            confidence=result.confidence,
            recommended_agent=result.recommended_agent,
            reasoning=result.verbalize(),
        )
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v3/hooks")
async def get_hooks_log():
    """Get recent hook events."""
    return [h.model_dump() for h in _hooks_log[-50:]]

@app.post("/api/v3/hooks")
async def log_hook_event(event: HookEvent):
    """Log a hook event."""
    _hooks_log.append(event)
    await manager.broadcast({
        "type": "hook_event",
        "event": event.model_dump(),
    })
    return event

# --- Model Usage ---

@app.get("/api/models/usage")
async def get_model_usage():
    return _model_usage

@app.post("/api/models/usage")
async def record_usage(provider: str, model: str, tokens: int, cost: float = 0.0):
    usage = {
        "provider": provider,
        "model": model,
        "tokens": tokens,
        "cost": cost,
        "is_free": cost == 0.0,
        "timestamp": datetime.now().isoformat(),
    }
    _model_usage.append(usage)
    return usage

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                await ws.send_json({"type": "echo", "message": msg})
            except:
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)

# --- Startup ---

@app.on_event("startup")
async def startup():
    # Create default sprint
    if not _sprints:
        sprint = Sprint(
            id="sprint_1",
            name="Sprint 1",
            start_date=datetime.now(),
        )
        _sprints["sprint_1"] = sprint

# --- Run ---

def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
