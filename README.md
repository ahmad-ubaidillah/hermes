     1|<p align="center">
     2|  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
     3|</p>
     4|
     5|# Hermes Agent v3.0 ☤
     6|
     7|<p align="center">
     8|  <a href="https://github.com/ahmad-ubaidillah/hermes"><img src="https://img.shields.io/badge/GitHub-ahmad--ubaidillah/hermes-181717?style=for-the-badge&logo=github" alt="GitHub"></a>
     9|  <a href="https://github.com/ahmad-ubaidillah/hermes/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
    10|  <img src="https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge" alt="Version">
    11|</p>
    12|
    13|**Autonomous AI Team Platform - Free + Powerful**
    14|
    15|Fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) with enhanced multi-agent capabilities, smart routing, and enterprise features.
    16|
    17|---
    18|
    19|## What's New in v3.0
    20|
    21|| Feature | Description |
    22||---------|-------------|
    23|| **IntentGate** | Smart intent classification - routes tasks to appropriate agents |
    24|| **Parallel Agents** | Run 5+ agents concurrently with priority queues |
    25|| **48 Lifecycle Hooks** | Fine-grained control over agent lifecycle |
    26|| **Hash-Anchored Edit** | Zero stale-line file editing |
    27|| **LSP Integration** | IDE precision - go to definition, find references |
    28|| **Web Dashboard** | FastAPI + React dashboard for monitoring |
    29|| **Observability** | OpenTelemetry tracing, metrics, logging |

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


    30|
    31|---
    32|
    33|## Architecture
    34|
    35|```
    36|┌─────────────────────────────────────────────────────────────┐
    37|│                    HERMES v3.0                              │
    38|├─────────────────────────────────────────────────────────────┤
    39|│  User Input                                                 │
    40|│      │                                                      │
    41|│      ▼                                                      │
    42|│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
    43|│  │ Intent  │───▶│ Parallel │───▶│   Web    │              │
    44|│  │  Gate   │    │  Agents  │    │Dashboard │              │
    45|│  └─────────┘    └──────────┘    └──────────┘              │
    46|│      │              │               │                      │
    47|│      ▼              ▼               ▼                      │
    48|│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
    49|│  │  Hooks  │    │ HashEdit │    │Observabil│              │
    50|│  │ (48)    │    │ + LSP    │    │  -ity    │              │
    51|│  └─────────┘    └──────────┘    └──────────┘              │
    52|└─────────────────────────────────────────────────────────────┘
    53|```
    54|
    55|---
    56|
    57|## Installation
    58|
    59|### Method 1: Quick Install (Recommended)
    60|
    61|```bash
    62|curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash
    63|source ~/.bashrc
    64|```
    65|
    66|### Method 2: Git Clone
    67|
    68|```bash
    69|git clone https://github.com/ahmad-ubaidillah/hermes.git ~/.hermes/hermes-agent
    70|cd ~/.hermes/hermes-agent
    71|python -m venv venv
    72|source venv/bin/activate
    73|pip install -e ".[all]"
    74|
    75|# Create hermes command
    76|echo 'source ~/.hermes/hermes-agent/venv/bin/activate && python ~/.hermes/hermes-agent/cli.py "$@"' > ~/.local/bin/hermes
    77|chmod +x ~/.local/bin/hermes
    78|```
    79|
    80|### Method 3: pip (Coming Soon)
    81|
    82|```bash
    83|pip install hermes-agent
    84|```
    85|
    86|### Method 4: Docker
    87|
    88|```bash
    89|docker pull ghcr.io/ahmad-ubaidillah/hermes:latest
    90|docker run -it -v ~/.hermes:/root/.hermes hermes:latest
    91|```
    92|
    93|### Method 5: Development
    94|
    95|```bash
    96|git clone https://github.com/ahmad-ubaidillah/hermes.git
    97|cd hermes
    98|python -m venv venv
    99|source venv/bin/activate
   100|pip install -e ".[dev]"
   101|pre-commit install
   102|```
   103|
   104|### Install Options
   105|
   106|```bash
   107|# Skip setup wizard
   108|curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --skip-setup
   109|
   110|# Minimal install (no OpenCode, no dashboard)
   111|curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --minimal
   112|
   113|# Install specific branch
   114|curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --branch develop
   115|
   116|# Custom install directory
   117|curl -fsSL https://raw.githubusercontent.com/ahmad-ubaidillah/hermes/main/scripts/install.sh | bash -s -- --dir /opt/hermes
   118|```
   119|
   120|### Post-Installation
   121|
   122|After installation, you can:
   123|
   124|```bash
   125|# Start chatting with Hermes
   126|hermes
   127|
   128|# Run setup wizard to configure
   129|hermes setup
   130|
   131|# Start web dashboard
   132|hermes-dashboard
   133|
   134|# Or manually
   135|python -m web.server --port 8000
   136|
   137|# Use OpenCode for free AI coding
   138|opencode run "implement feature X"
   139|
   140|# Check installation
   141|hermes --version
   142|hermes doctor
   143|```
   144|
   145|### Use v3.0 Features
   146|
   147|```python
   148|# Intent Classification
   149|from routing import IntentGate
   150|
   151|gate = IntentGate()
   152|result = gate.analyze("implement user authentication")
   153|print(result.verbalize())
   154|# I detect **coding** intent — detected 'implement' indicates coding.
   155|
   156|# Parallel Agent Execution
   157|from lifecycle import BackgroundAgentPool
   158|
   159|pool = BackgroundAgentPool()
   160|task_ids = await pool.spawn_parallel([
   161|    {"agent": "Dev", "prompt": "Implement auth"},
   162|    {"agent": "QA", "prompt": "Write tests"},
   163|    {"agent": "Sec", "prompt": "Security review"},
   164|])
   165|
   166|# Lifecycle Hooks
   167|from lifecycle import hooks, HookEvent
   168|
   169|@hooks.on(HookEvent.TOOL_BEFORE)
   170|def validate_access(ctx):
   171|    if "dangerous" in ctx.data.get("tool", ""):
   172|        ctx.stop("Blocked dangerous tool")
   173|    return ctx
   174|```
   175|
   176|### Run Web Dashboard
   177|
   178|```bash
   179|# Start backend
   180|python -m web.backend.main
   181|
   182|# Open http://localhost:8000 for dashboard
   183|# Open http://localhost:8000/docs for API docs
   184|```
   185|
   186|---
   187|
   188|## Module Structure
   189|
   190|```
   191|hermes-agent/
   192|├── routing/                    # Intent classification
   193|│   ├── __init__.py
   194|│   └── intent_gate.py          # Smart task routing
   195|│
   196|├── lifecycle/                  # Agent lifecycle management
   197|│   ├── __init__.py
   198|│   ├── background_agents.py    # Parallel agent pool
   199|│   ├── parallel_pool.py        # Enhanced pool with priorities
   200|│   └── hooks.py                # 48 lifecycle hooks
   201|│
   202|├── tools/                      # Extended tools
   203|│   ├── hash_edit.py            # Zero stale-line editing
   204|│   └── lsp_client.py           # Language Server Protocol
   205|│
   206|├── web/                        # Web interface
   207|│   ├── backend/main.py         # FastAPI REST + WebSocket
   208|│   └── frontend/               # React dashboard
   209|│
   210|├── orchestration.py            # Main pipeline
   211|├── observability.py            # OpenTelemetry integration
   212|│
   213|└── docs/                       # Documentation
   214|    ├── README.md
   215|    ├── API.md
   216|    ├── HOOKS.md
   217|    └── DEPLOYMENT.md
   218|```
   219|
   220|---
   221|
   222|## IntentGate - Smart Routing
   223|
   224|Classifies user intent and routes to appropriate agent:
   225|
   226|| Intent | Detection | Agent | Workflow |
   227||--------|-----------|-------|----------|
   228|| `quick_task` | "quick", "show", "list" | Flash | Direct |
   229|| `coding` | "implement", "create", "build" | Dev | Sprint |
   230|| `architecture` | "design", "structure" | Arch | Planning |
   231|| `debugging` | "fix", "error", "bug" | Dev | Sprint |
   232|| `deployment` | "deploy", "release" | Ops | Deploy |
   233|| `review` | "review", "check" | QA | Review |
   234|| `research` | "research", "analyze" | Research | Research |
   235|
   236|```python
   237|from routing import IntentGate
   238|
   239|gate = IntentGate()
   240|result = gate.analyze("fix the login bug")
   241|
   242|print(f"Intent: {result.intent.value}")
   243|print(f"Agent: {result.recommended_agent}")
   244|print(f"Workflow: {result.recommended_workflow}")
   245|print(f"Confidence: {result.confidence}")
   246|```
   247|
   248|---
   249|
   250|## Parallel Agents
   251|
   252|Run multiple agents concurrently:
   253|
   254|```python
   255|from lifecycle import BackgroundAgentPool
   256|
   257|pool = BackgroundAgentPool()
   258|
   259|# Spawn 3 agents in parallel
   260|task_ids = await pool.spawn_parallel([
   261|    {"agent": "Dev", "prompt": "Implement user authentication"},
   262|    {"agent": "QA", "prompt": "Write tests for auth module"},
   263|    {"agent": "Sec", "prompt": "Security review of auth flow"},
   264|])
   265|
   266|# Wait for all to complete
   267|results = await pool.wait_all(list(task_ids.values()))
   268|
   269|for agent, result in results.items():
   270|    print(f"{agent}: {result.status}")
   271|```
   272|
   273|---
   274|
   275|## Lifecycle Hooks (48 hooks)
   276|
   277|Fine-grained control over agent lifecycle:
   278|
   279|### Hook Categories
   280|
   281|| Category | Count | Events |
   282||----------|-------|--------|
   283|| Session | 23 | created, deleted, idle, error, resumed, ... |
   284|| Tool | 12 | before, after, error, retry, timeout, ... |
   285|| Agent | 6 | spawn, complete, error, timeout, ... |
   286|| Sprint | 5 | start, end, task.assigned, task.completed, ... |
   287|| Intent | 3 | classified, ambiguous, routed |
   288|| Message | 4 | before, after, transform, validated |
   289|| Continuation | 3 | check, trigger, limit |
   290|| Skill | 2 | loaded, unloaded |
   291|
   292|### Usage
   293|
   294|```python
   295|from lifecycle import hooks, HookEvent
   296|
   297|# Validate file access
   298|@hooks.on(HookEvent.TOOL_BEFORE)
   299|def validate_file_access(ctx):
   300|    tool = ctx.data.get("tool", "")
   301|