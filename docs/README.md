# Aizen v3.0

**Autonomous AI Team Platform - Free + Powerful**

---

## Overview

Aizen is a multi-agent AI system that operates as an autonomous software development team. Version 3.0 introduces intelligent routing, parallel execution, and enterprise-grade infrastructure.

### Key Features

- **Free Models** - 550K tokens/day via z.ai (qwen3.6, minimax, mimo)
- **Smart Routing** - IntentGate classifies and routes tasks automatically
- **Parallel Execution** - Run 5+ agents concurrently
- **Lifecycle Hooks** - 48 hooks for fine-grained control
- **Zero-Error Editing** - Hash-anchored file modifications
- **IDE Precision** - LSP integration for code intelligence
- **Web Dashboard** - Real-time monitoring and management
- **Full Observability** - Tracing, metrics, and logging

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HERMES v3.0                              │
├─────────────────────────────────────────────────────────────┤
│  User Input                                                 │
│      │                                                      │
│      ▼                                                      │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Intent  │───▶│ Parallel │───▶│   Web    │              │
│  │  Gate   │    │  Agents  │    │Dashboard │              │
│  └─────────┘    └──────────┘    └──────────┘              │
│      │              │               │                      │
│      ▼              ▼               ▼                      │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Hooks  │    │ HashEdit │    │Observabil│              │
│  │ (48)    │    │ + LSP    │    │  -ity    │              │
│  └─────────┘    └──────────┘    └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
aizen-agent/
├── routing/                    # Intent classification
│   ├── __init__.py
│   └── intent_gate.py          # Smart task routing
│
├── lifecycle/                  # Agent lifecycle management
│   ├── __init__.py
│   ├── background_agents.py    # Parallel agent pool
│   ├── parallel_pool.py        # Enhanced pool with priorities
│   └── hooks.py                # 48 lifecycle hooks
│
├── tools/                      # Extended tools
│   ├── hash_edit.py            # Zero stale-line editing
│   └── lsp_client.py           # Language Server Protocol
│
├── web/                        # Web interface
│   ├── backend/
│   │   └── main.py             # FastAPI REST + WebSocket
│   └── frontend/
│       ├── src/App.tsx         # React dashboard
│       └── package.json
│
├── orchestration.py            # Main pipeline
├── observability.py            # OpenTelemetry integration
│
└── docs/                       # Documentation
    ├── API.md
    ├── HOOKS.md
    └── DEPLOYMENT.md
```

---

## Quick Start

### 1. Intent Classification

```python
from routing import IntentGate

gate = IntentGate()
result = gate.analyze("implement user authentication")

print(result.verbalize())
# I detect **coding** intent — detected 'implement' indicates coding.
# My approach: sprint_workflow.
```

### 2. Parallel Agent Execution

```python
from lifecycle import BackgroundAgentPool

pool = BackgroundAgentPool()

task_ids = await pool.spawn_parallel([
    {"agent": "Dev", "prompt": "Implement auth"},
    {"agent": "QA", "prompt": "Write tests"},
    {"agent": "Sec", "prompt": "Security review"},
])

results = await pool.wait_all(list(task_ids.values()))
```

### 3. Lifecycle Hooks

```python
from lifecycle import hooks, HookEvent

@hooks.on(HookEvent.TOOL_BEFORE)
def validate_access(ctx):
    if "dangerous" in ctx.data.get("tool", ""):
        ctx.stop("Blocked dangerous tool")
    return ctx
```

### 4. Hash-Anchored Edit

```python
from tools.hash_edit import HashAnchoredEdit

editor = HashAnchoredEdit()

# Read file with anchors
anchored = editor.read_with_anchors("file.py")

# Safe edit with hash verification
result = editor.safe_edit(
    "file.py",
    line_number=5,
    old_hash="abc123",
    new_content="new line content"
)
```

### 5. Web Dashboard

```bash
# Start backend
python -m web.backend.main

# Open http://localhost:8000/docs for API
# Open http://localhost:8000 for dashboard
```

---

## Agent Team

| Agent | Role | Workflow |
|-------|------|----------|
| **Flash** | Quick tasks | Direct execution |
| **Dev** | Development | Sprint workflow |
| **Arch** | Architecture | Planning workflow |
| **QA** | Quality | Review workflow |
| **Ops** | Operations | Deploy workflow |
| **Sec** | Security | Audit workflow |
| **Research** | Research | Research workflow |

---

## Intent Types

| Intent | Detection | Agent |
|--------|-----------|-------|
| `quick_task` | "quick", "show", "list" | Flash |
| `coding` | "implement", "create", "build" | Dev |
| `architecture` | "design", "structure" | Arch |
| `debugging` | "fix", "error", "bug" | Dev |
| `deployment` | "deploy", "release" | Ops |
| `review` | "review", "check" | QA |
| `research` | "research", "analyze" | Research |

---

## API Reference

### REST Endpoints

```
GET  /api/stats              # Dashboard statistics
GET  /api/agents             # List all agents
POST /api/agents/{name}/assign # Assign task to agent
GET  /api/tasks              # List tasks
POST /api/tasks              # Create task
PATCH /api/tasks/{id}        # Update task status
GET  /api/sprints            # List sprints
POST /api/sprints            # Create sprint
GET  /api/models/usage       # Model usage stats
WS   /ws                     # Real-time WebSocket
```

### WebSocket Events

```json
// Task created
{"type": "task_created", "task": {...}}

// Agent assigned
{"type": "agent_assigned", "agent": "Dev", "task": "task_123"}

// Task updated
{"type": "task_updated", "task": {...}}
```

---

## Lifecycle Hooks

### Session Hooks (23)
- `session.created`, `session.deleted`, `session.idle`, `session.error`, ...

### Tool Hooks (12)
- `tool.execute.before`, `tool.execute.after`, `tool.execute.error`, ...

### Agent Hooks (6)
- `agent.spawn`, `agent.complete`, `agent.error`, ...

### Sprint Hooks (5)
- `sprint.start`, `sprint.end`, `sprint.task.assigned`, ...

### Intent Hooks (3)
- `intent.classified`, `intent.ambiguous`, `intent.routed`

---

## Configuration

### Free Models (z.ai)

```yaml
# ~/.aizen/config.yaml
provider: zai
models:
  fast: mimo-v2-omni-free
  coding: qwen3.6-plus-free
  complex: minimax-m2.5-free

limits:
  daily_tokens: 550000
```

### Observability

```yaml
observability:
  tracing:
    enabled: true
    export_file: ~/.aizen/traces.jsonl
  metrics:
    enabled: true
    prometheus_port: 9090
```

---

## Testing

```bash
# Test IntentGate
python -m routing.intent_gate

# Test Hooks
python -m lifecycle.hooks

# Test Hash-Edit
python tools/hash_edit.py

# Test Observability
python observability.py

# Test Web Backend
python -m web.backend.main
```

---

## Comparison

| Feature | Aizen v3.0 | Nasiko | Oh-My-OpenAgent |
|---------|-------------|--------|-----------------|
| Free Models | ✓ 550K/day | ✗ | ✗ |
| Sprint Workflow | ✓ | ✗ | ✗ |
| Local-First | ✓ | ✗ | ✓ |
| IntentGate | ✓ | ✗ | ✓ |
| Background Agents | ✓ 5+ | ✓ | ✓ |
| Lifecycle Hooks | ✓ 48 | ✗ | ✓ 48 |
| Hash-Edit | ✓ | ✗ | ✓ |
| LSP Integration | ✓ | ✗ | ✓ |
| Web Dashboard | ✓ | ✓ | ✗ |
| Observability | ✓ | ✓ | ✗ |

---

## License

MIT License - See LICENSE file for details.

---

## Credits

- **oh-my-openagent** - IntentGate, Hooks, Hash-Edit, LSP concepts
- **Nasiko** - Dashboard, Observability patterns
- **z.ai** - Free model access

---

**Aizen v3.0** - *The Best of Both Worlds: Free + Autonomous + Enterprise*
