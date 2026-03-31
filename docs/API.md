# API Reference - Hermes v3.0

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required. For production, add JWT or API key.

---

## Endpoints

### Stats

#### GET /api/stats

Get dashboard statistics.

**Response:**
```json
{
  "total_agents": 7,
  "active_agents": 2,
  "total_tasks": 15,
  "completed_tasks": 10,
  "total_tokens": 25000,
  "remaining_budget": 525000
}
```

---

### Agents

#### GET /api/agents

List all agents and their status.

**Response:**
```json
[
  {
    "name": "Dev",
    "role": "Development",
    "status": "busy",
    "current_task": "task_123",
    "tasks_completed": 5,
    "tokens_used": 10000
  },
  ...
]
```

#### GET /api/agents/{agent_name}

Get single agent details.

**Response:**
```json
{
  "name": "Dev",
  "role": "Development",
  "status": "busy",
  "current_task": "task_123",
  "tasks_completed": 5,
  "tokens_used": 10000
}
```

#### POST /api/agents/{agent_name}/assign

Assign a task to an agent.

**Body:**
```json
{
  "task_id": "task_123"
}
```

**Response:**
```json
{
  "message": "Task task_123 assigned to Dev"
}
```

---

### Tasks

#### GET /api/tasks

List all tasks.

**Query Parameters:**
- `sprint_id` (optional): Filter by sprint
- `status` (optional): Filter by status (todo, in_progress, done, blocked)

**Response:**
```json
[
  {
    "id": "task_1",
    "title": "Implement authentication",
    "description": "Add JWT auth",
    "status": "in_progress",
    "assignee": "Dev",
    "priority": "high",
    "created_at": "2026-03-31T10:00:00",
    "updated_at": "2026-03-31T11:00:00",
    "estimated_tokens": 5000,
    "actual_tokens": 3000
  },
  ...
]
```

#### POST /api/tasks

Create a new task.

**Body:**
```json
{
  "title": "Implement feature X",
  "description": "Details...",
  "priority": "medium",
  "sprint_id": "sprint_1"
}
```

**Response:**
```json
{
  "id": "task_5",
  "title": "Implement feature X",
  "description": "Details...",
  "status": "todo",
  "priority": "medium",
  "created_at": "2026-03-31T12:00:00",
  "updated_at": "2026-03-31T12:00:00"
}
```

#### PATCH /api/tasks/{task_id}

Update task status.

**Body:**
```json
{
  "status": "done"
}
```

**Response:**
```json
{
  "id": "task_1",
  "status": "done",
  "updated_at": "2026-03-31T12:30:00"
}
```

---

### Sprints

#### GET /api/sprints

List all sprints.

**Response:**
```json
[
  {
    "id": "sprint_1",
    "name": "Sprint 1",
    "start_date": "2026-03-25T00:00:00",
    "end_date": null,
    "status": "active",
    "tasks": ["task_1", "task_2", "task_3"]
  }
]
```

#### POST /api/sprints

Create a new sprint.

**Body:**
```json
{
  "name": "Sprint 2"
}
```

---

### Model Usage

#### GET /api/models/usage

Get model usage statistics.

**Response:**
```json
[
  {
    "provider": "zai",
    "model": "qwen3.6-plus-free",
    "tokens_used": 15000,
    "cost": 0.0,
    "is_free": true
  }
]
```

#### POST /api/models/usage

Record model usage.

**Body:**
```json
{
  "provider": "zai",
  "model": "qwen3.6-plus-free",
  "tokens": 1000,
  "cost": 0.0
}
```

---

## WebSocket

### WS /ws

Real-time updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

**Messages:**

```json
// Task created
{
  "type": "task_created",
  "task": { ... }
}

// Agent assigned
{
  "type": "agent_assigned",
  "agent": "Dev",
  "task": "task_123"
}

// Task updated
{
  "type": "task_updated",
  "task": { ... }
}

// Usage recorded
{
  "type": "usage_recorded",
  "usage": { ... }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
