"""
Hermes Web Dashboard - FastAPI Backend

Provides REST API and WebSocket for:
- Agent status and management
- Sprint board and tasks
- Model budget tracking
- Real-time updates
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="Hermes Dashboard",
    description="Web dashboard for Hermes AI Agent",
    version="3.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class AgentStatus(BaseModel):
    name: str
    role: str
    status: str = "idle"  # idle, busy, error
    current_task: Optional[str] = None
    last_activity: Optional[datetime] = None
    tasks_completed: int = 0
    tokens_used: int = 0


class SprintTask(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str = "todo"  # todo, in_progress, done, blocked
    assignee: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical
    created_at: datetime
    updated_at: datetime
    estimated_tokens: int = 0
    actual_tokens: int = 0


class Sprint(BaseModel):
    id: str
    name: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "active"  # planning, active, completed
    tasks: List[str] = []


class ModelUsage(BaseModel):
    provider: str
    model: str
    tokens_used: int
    cost: float
    is_free: bool


class DashboardStats(BaseModel):
    total_agents: int
    active_agents: int
    total_tasks: int
    completed_tasks: int
    total_tokens: int
    remaining_budget: int


# ============== In-Memory Store ==============

# In production, this would be a database
_agents: Dict[str, AgentStatus] = {
    "Flash": AgentStatus(name="Flash", role="Quick Tasks"),
    "Dev": AgentStatus(name="Dev", role="Development"),
    "Arch": AgentStatus(name="Arch", role="Architecture"),
    "QA": AgentStatus(name="QA", role="Quality Assurance"),
    "Ops": AgentStatus(name="Ops", role="Operations"),
    "Sec": AgentStatus(name="Sec", role="Security"),
    "Research": AgentStatus(name="Research", role="Research"),
}

_sprints: Dict[str, Sprint] = {}
_tasks: Dict[str, SprintTask] = {}
_model_usage: List[ModelUsage] = []

# WebSocket connections
_ws_connections: List[WebSocket] = []


# ============== WebSocket Manager ==============

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# ============== Routes ==============

@app.get("/")
async def root():
    return {"message": "Hermes Dashboard API v3.0", "docs": "/docs"}


@app.get("/api/stats", response_model=DashboardStats)
async def get_stats():
    """Get dashboard statistics."""
    active = sum(1 for a in _agents.values() if a.status == "busy")
    completed = sum(1 for t in _tasks.values() if t.status == "done")
    total_tokens = sum(a.tokens_used for a in _agents.values())
    
    return DashboardStats(
        total_agents=len(_agents),
        active_agents=active,
        total_tasks=len(_tasks),
        completed_tasks=completed,
        total_tokens=total_tokens,
        remaining_budget=550000 - total_tokens,  # Free tier limit
    )


# --- Agents ---

@app.get("/api/agents", response_model=List[AgentStatus])
async def list_agents():
    """List all agents and their status."""
    return list(_agents.values())


@app.get("/api/agents/{agent_name}", response_model=AgentStatus)
async def get_agent(agent_name: str):
    """Get agent status."""
    if agent_name not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agents[agent_name]


@app.post("/api/agents/{agent_name}/assign")
async def assign_task(agent_name: str, task_id: str):
    """Assign a task to an agent."""
    if agent_name not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    _agents[agent_name].current_task = task_id
    _agents[agent_name].status = "busy"
    _tasks[task_id].assignee = agent_name
    _tasks[task_id].status = "in_progress"
    
    # Broadcast update
    await manager.broadcast({
        "type": "agent_assigned",
        "agent": agent_name,
        "task": task_id,
    })
    
    return {"message": f"Task {task_id} assigned to {agent_name}"}


# --- Tasks ---

@app.get("/api/tasks", response_model=List[SprintTask])
async def list_tasks(sprint_id: Optional[str] = None, status: Optional[str] = None):
    """List tasks, optionally filtered."""
    tasks = list(_tasks.values())
    
    if sprint_id:
        sprint = _sprints.get(sprint_id)
        if sprint:
            tasks = [t for t in tasks if t.id in sprint.tasks]
    
    if status:
        tasks = [t for t in tasks if t.status == status]
    
    return tasks


@app.post("/api/tasks", response_model=SprintTask)
async def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    sprint_id: Optional[str] = None,
):
    """Create a new task."""
    task_id = f"task_{len(_tasks) + 1}"
    now = datetime.now()
    
    task = SprintTask(
        id=task_id,
        title=title,
        description=description,
        priority=priority,
        created_at=now,
        updated_at=now,
    )
    
    _tasks[task_id] = task
    
    if sprint_id and sprint_id in _sprints:
        _sprints[sprint_id].tasks.append(task_id)
    
    await manager.broadcast({
        "type": "task_created",
        "task": task.model_dump(),
    })
    
    return task


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, status: Optional[str] = None):
    """Update task status."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _tasks[task_id]
    
    if status:
        task.status = status
        task.updated_at = datetime.now()
        
        # Update agent status if task completed
        if status == "done" and task.assignee:
            if task.assignee in _agents:
                _agents[task.assignee].current_task = None
                _agents[task.assignee].status = "idle"
                _agents[task.assignee].tasks_completed += 1
    
    await manager.broadcast({
        "type": "task_updated",
        "task": task.model_dump(),
    })
    
    return task


# --- Sprints ---

@app.get("/api/sprints", response_model=List[Sprint])
async def list_sprints():
    """List all sprints."""
    return list(_sprints.values())


@app.post("/api/sprints", response_model=Sprint)
async def create_sprint(name: str):
    """Create a new sprint."""
    sprint_id = f"sprint_{len(_sprints) + 1}"
    
    sprint = Sprint(
        id=sprint_id,
        name=name,
        start_date=datetime.now(),
    )
    
    _sprints[sprint_id] = sprint
    
    await manager.broadcast({
        "type": "sprint_created",
        "sprint": sprint.model_dump(),
    })
    
    return sprint


# --- Model Usage ---

@app.get("/api/models/usage", response_model=List[ModelUsage])
async def get_model_usage():
    """Get model usage statistics."""
    return _model_usage


@app.post("/api/models/usage")
async def record_usage(provider: str, model: str, tokens: int, cost: float = 0.0):
    """Record model usage."""
    usage = ModelUsage(
        provider=provider,
        model=model,
        tokens_used=tokens,
        cost=cost,
        is_free=cost == 0.0,
    )
    
    _model_usage.append(usage)
    
    await manager.broadcast({
        "type": "usage_recorded",
        "usage": usage.model_dump(),
    })
    
    return usage


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Parse and handle message
            try:
                message = json.loads(data)
                # Echo back for now
                await websocket.send_json({
                    "type": "echo",
                    "message": message,
                })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============== Startup/Shutdown ==============

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    # Create default sprint
    if not _sprints:
        sprint = Sprint(
            id="sprint_1",
            name="Sprint 1",
            start_date=datetime.now(),
        )
        _sprints["sprint_1"] = sprint


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    pass


# ============== Run ==============

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
