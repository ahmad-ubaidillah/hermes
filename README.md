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
    if tool in ("write_file", "patch", "terminal"):
        path = ctx.data.get("path", "")
        blocked = ["/etc/", "/root/", "/boot/"]
        for blocked_path in blocked:
            if blocked_path in str(path):
                ctx.stop(f"Access denied: {blocked_path}")
    return ctx

# Log all tool executions
@hooks.on(HookEvent.TOOL_AFTER)
def log_tool(ctx):
    print(f"Tool {ctx.data['tool']} completed in {ctx.metadata.get('duration')}s")
    return ctx
```

---

## Hash-Anchored Edit

Zero stale-line file editing - prevents errors when files change:

```python
from tools.hash_edit import HashAnchoredEdit

editor = HashAnchoredEdit()

# Read file with content hashes
anchored = editor.read_with_anchors("src/main.py")

# Edit with hash verification - fails if content changed
result = editor.safe_edit(
    "src/main.py",
    line_number=42,
    old_hash="abc123",  # Hash of original content
    new_content="def new_function():\n    pass"
)

if result.success:
    print("Edit applied successfully")
else:
    print(f"Edit failed: {result.error}")
    # File may have changed - refresh and retry
```

---

## LSP Integration

IDE-precision code operations:

```python
from tools.lsp_client import LSPClient

lsp = LSPClient()

# Start language server
await lsp.start("python")

# Go to definition
definition = await lsp.go_to_definition("src/main.py", 15, 10)
print(f"Defined at: {definition.file}:{definition.line}")

# Find all references
refs = await lsp.find_references("src/main.py", 15, 10)
for ref in refs:
    print(f"Referenced in: {ref.file}:{ref.line}")

# Rename symbol across workspace
await lsp.rename("src/main.py", 15, 10, "new_name")

# Get diagnostics
diagnostics = await lsp.get_diagnostics("src/main.py")
for d in diagnostics:
    print(f"{d.severity}: {d.message} at line {d.line}")

# Supported languages: Python, TypeScript, Rust, Go, Java
```

---

## Web Dashboard

FastAPI backend + React frontend for monitoring:

### API Endpoints

```
GET  /api/stats              # Dashboard statistics
GET  /api/agents             # List all agents
POST /api/agents/{name}/assign # Assign task to agent
GET  /api/tasks              # List tasks
POST /api/tasks              # Create task
PATCH /api/tasks/{id}        # Update task status
GET  /api/sprints            # List sprints
GET  /api/models/usage       # Model usage stats
WS   /ws                     # Real-time WebSocket
```

### Run Dashboard

```bash
# Backend
python -m web.backend.main

# Frontend (development)
cd web/frontend && npm run dev
```

---

## Observability

OpenTelemetry tracing and metrics:

```python
from observability import get_observability

obs = get_observability()

# Trace operations
with obs.trace_operation("process_request"):
    # ... do work ...
    obs.record_request("Dev", tokens=1500, success=True)

# Get stats
stats = obs.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Success rate: {stats['success_rate']}%")
```

---

## Free Model Integration via OpenCode

Hermes v3.0 integrates with [OpenCode](https://github.com/opencode-ai/opencode) for free AI models:

| Model | Use Case | Cost |
|-------|----------|------|
| `opencode/qwen3.6-plus-free` | Coding tasks | FREE |
| `opencode/mimo-v2-omni-free` | Fast responses | FREE |
| `opencode/mimo-v2-pro-free` | Advanced tasks | FREE |
| `opencode/minimax-m2.5-free` | Complex reasoning | FREE |
| `opencode/nemotron-3-super-free` | General purpose | FREE |
| `opencode/big-pickle` | Large context | FREE |
| `opencode/gpt-5-nano` | Quick tasks | FREE |

### Install OpenCode

```bash
# Install OpenCode CLI
curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/main/install.sh | bash

# Or via npm
npm install -g @opencode-ai/opencode

# List available models
opencode models
```

### Use with Hermes

```bash
# Start OpenCode (runs as background agent)
opencode &

# Or use OpenCode directly for coding tasks
opencode run "implement user authentication"
```

---

## Original Hermes Features

All original Hermes features are preserved:

- **Multi-platform messaging** - Telegram, Discord, Slack, WhatsApp, Signal
- **Skills system** - Autonomous skill creation and improvement
- **Memory** - Persistent cross-session memory
- **Cron scheduling** - Scheduled automations
- **Delegation** - Spawn isolated subagents
- **MCP integration** - Connect MCP servers
- **40+ tools** - Terminal, browser, file operations, and more

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Main documentation |
| [docs/API.md](docs/API.md) | REST API reference |
| [docs/HOOKS.md](docs/HOOKS.md) | Lifecycle hooks guide |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guide |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | Implementation summary |

---

## Comparison

| Feature | Hermes v3.0 | Nasiko | Oh-My-OpenAgent |
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

## Quick Reference

```bash
# CLI
hermes                          # Start chatting
hermes model                    # Choose model
hermes tools                    # Configure tools
hermes gateway                  # Start messaging gateway
hermes setup                    # Full setup wizard

# v3.0 Tests
python -m routing.intent_gate   # Test IntentGate
python -m lifecycle.hooks       # Test Hooks
python observability.py         # Test Observability
python -m web.backend.main      # Start Dashboard
```

---

## Credits

- **Original Hermes** - [Nous Research](https://nousresearch.com)
- **oh-my-openagent** - IntentGate, Hooks, Hash-Edit, LSP concepts
- **Nasiko** - Dashboard, Observability patterns
- **z.ai** - Free model access

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Nous Research](https://nousresearch.com).
Enhanced with v3.0 features by [Ahmad Ubaidillah](https://github.com/ahmad-ubaidillah).
