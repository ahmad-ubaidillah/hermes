<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent v3.0 ☤

<p align="center">
  <a href="https://github.com/ahmad-ubaidillah/hermes"><img src="https://img.shields.io/badge/GitHub-ahmad--ubaidillah/hermes-181717?style=for-the-badge&logo=github" alt="GitHub"></a>
  <a href="https://github.com/ahmad-ubaidillah/hermes/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge" alt="Version">
</p>

**Autonomous AI Team Platform - Free + Powerful**

Fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) with enhanced multi-agent capabilities, smart routing, and enterprise features.

---

## What's New in v3.0

| Feature | Description |
|---------|-------------|
| **IntentGate** | Smart intent classification - routes tasks to appropriate agents |
| **Parallel Agents** | Run 5+ agents concurrently with priority queues |
| **48 Lifecycle Hooks** | Fine-grained control over agent lifecycle |
| **Hash-Anchored Edit** | Zero stale-line file editing |
| **LSP Integration** | IDE precision - go to definition, find references |
| **Web Dashboard** | FastAPI + React dashboard for monitoring |
| **Observability** | OpenTelemetry tracing, metrics, logging |

| **REPL Debug Mode** | Interactive Python REPL for debugging agent state |
| **Remote Bridge** | WebSocket + REST API for remote agent access |
| **Skill Marketplace** | Browse, install, and manage skills locally |
| **Admin Dashboard** | Single-file Vue 3 dashboard for monitoring |
| **Graceful Shutdown** | Safe cleanup on SIGTERM/SIGINT |
| **Process Supervisor** | Auto-restart and health monitoring |

---

## Quick Start

```bash
# Chat with Hermes
hermes

# Use free models via OpenCode
hermes --model opencode/qwen3.6-plus-free

# Start REPL for debugging
python repl.py

# Start remote bridge
python -m bridge.server

# Open admin dashboard
open dashboard/index.html
```

---

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

## Installation

### Method 1: Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash
source ~/.bashrc
```

### Method 2: Git Clone

```bash
git clone https://github.com/ahmad-ubaidillah/hermes.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
python -m venv venv
source venv/bin/activate
pip install -e ".[all]"

# Create hermes command
echo 'source ~/.hermes/hermes-agent/venv/bin/activate && python ~/.hermes/hermes-agent/cli.py "$@"' > ~/.local/bin/hermes
chmod +x ~/.local/bin/hermes
```

### Method 3: pip (Coming Soon)

```bash
pip install hermes-agent
```

### Method 4: Docker

```bash
docker pull ghcr.io/ahmad-ubaidillah/hermes:latest
docker run -it -v ~/.hermes:/root/.hermes hermes:latest
```

### Method 5: Development

```bash
git clone https://github.com/ahmad-ubaidillah/hermes.git
cd hermes
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Install Options

```bash
# Skip setup wizard
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --skip-setup

# Minimal install (no OpenCode, no dashboard)
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --minimal

# Install specific branch
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --branch develop

# Custom install directory
curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --dir /opt/hermes
```

### Post-Installation

After installation, you can:

```bash
# Start chatting with Hermes
hermes

# Run setup wizard to configure
hermes setup

# Start web dashboard
hermes-dashboard

# Or manually
python -m web.server --port 8000

# Use OpenCode for free AI coding
opencode run "implement feature X"

# Check installation
hermes --version
hermes doctor
```

### Use v3.0 Features

```python
# Intent Classification
from routing import IntentGate

gate = IntentGate()
result = gate.analyze("implement user authentication")
print(result.verbalize())
# I detect **coding** intent — detected 'implement' indicates coding.

# Parallel Agent Execution
from lifecycle import BackgroundAgentPool

pool = BackgroundAgentPool()
task_ids = await pool.spawn_parallel([
    {"agent": "Dev", "prompt": "Implement auth"},
    {"agent": "QA", "prompt": "Write tests"},
    {"agent": "Sec", "prompt": "Security review"},
])

# Lifecycle Hooks
from lifecycle import hooks, HookEvent

@hooks.on(HookEvent.TOOL_BEFORE)
def validate_access(ctx):
    if "dangerous" in ctx.data.get("tool", ""):
        ctx.stop("Blocked dangerous tool")
    return ctx
```

### Run Web Dashboard

```bash
# Start backend
python -m web.backend.main

# Open http://localhost:8000 for dashboard
# Open http://localhost:8000/docs for API docs
```

---

## Module Structure

```
hermes-agent/
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
│   ├── backend/main.py         # FastAPI REST + WebSocket
│   └── frontend/               # React dashboard
│
├── orchestration.py            # Main pipeline
├── observability.py            # OpenTelemetry integration
│
└── docs/                       # Documentation
    ├── README.md
    ├── API.md
    ├── HOOKS.md
    └── DEPLOYMENT.md
```

---

## IntentGate - Smart Routing

Classifies user intent and routes to appropriate agent:

| Intent | Detection | Agent | Workflow |
|--------|-----------|-------|----------|
| `quick_task` | "quick", "show", "list" | Flash | Direct |
| `coding` | "implement", "create", "build" | Dev | Sprint |
| `architecture` | "design", "structure" | Arch | Planning |
| `debugging` | "fix", "error", "bug" | Dev | Sprint |
| `deployment` | "deploy", "release" | Ops | Deploy |
| `review` | "review", "check" | QA | Review |
| `research` | "research", "analyze" | Research | Research |

```python
from routing import IntentGate

gate = IntentGate()
result = gate.analyze("fix the login bug")

print(f"Intent: {result.intent.value}")
print(f"Agent: {result.recommended_agent}")
print(f"Workflow: {result.recommended_workflow}")
print(f"Confidence: {result.confidence}")
```

---

## Parallel Agents

Run multiple agents concurrently:

```python
from lifecycle import BackgroundAgentPool

pool = BackgroundAgentPool()

# Spawn 3 agents in parallel
task_ids = await pool.spawn_parallel([
    {"agent": "Dev", "prompt": "Implement user authentication"},
    {"agent": "QA", "prompt": "Write tests for auth module"},
    {"agent": "Sec", "prompt": "Security review of auth flow"},
])

# Wait for all to complete
results = await pool.wait_all(list(task_ids.values()))

for agent, result in results.items():
    print(f"{agent}: {result.status}")
```

---

## Lifecycle Hooks (48 hooks)

Fine-grained control over agent lifecycle:

### Hook Categories

| Category | Count | Events |
|----------|-------|--------|
| Session | 23 | created, deleted, idle, error, resumed, ... |
| Tool | 12 | before, after, error, retry, timeout, ... |
| Agent | 6 | spawn, complete, error, timeout, ... |
| Sprint | 5 | start, end, task.assigned, task.completed, ... |
| Intent | 3 | classified, ambiguous, routed |
| Message | 4 | before, after, transform, validated |
| Continuation | 3 | check, trigger, limit |
| Skill | 2 | loaded, unloaded |

### Usage

```python
from lifecycle import hooks, HookEvent

# Validate file access
@hooks.on(HookEvent.TOOL_BEFORE)
def validate_file_access(ctx):
    tool = ctx.data.get("tool", "")
