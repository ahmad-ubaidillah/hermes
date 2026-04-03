# Refactoring Plan: Codebase Simplification

## Executive Summary

This document outlines a step-by-step plan to simplify the codebase structure while maintaining backward compatibility.

## Current State

```
ROOT (30+ files that should be in folders)
├── run_agent.py (9,348 lines) - MONSTER FILE
├── cli.py (8,787 lines) - MONSTER FILE  
├── repl.py (19138 lines)
├── sdk.py
├── server.py
├── utils.py
├── supervisor.py
├── shutdown.py
├── trajectory_compressor.py
├── aizen_*.py (multiple config/health files)
├── tools/ (3.7MB - needs subfolder organization)
├── aizen_cli/ (1.9MB)
├── agent/ (already organized ✓)
├── core/ (already organized ✓)
├── gateway/ (already organized ✓)
└── web/ (186MB - needs audit)
```

## Target State

```
src/
├── __init__.py
├── main.py                    # from aizen script
├── run_agent.py              # backward compat shim → src/agent/engine.py
├── cli.py                   # backward compat shim → src/cli/interface.py
│
├── agent/                   # AI Agent core
│   ├── __init__.py
│   ├── engine.py           # AIAgent class (extracted from run_agent.py)
│   ├── client.py           # OpenAI client management
│   ├── context.py          # Context compression
│   └── tools.py            # Tool orchestration
│
├── cli/                     # CLI interface
│   ├── __init__.py
│   ├── interface.py        # ChatConsole, AizenCLI (extracted from cli.py)
│   ├── commands.py         # Command handlers
│   ├── completion.py       # Autocomplete
│   └── repl.py             # REPL (from repl.py)
│
├── shared/                  # Shared utilities
│   ├── __init__.py
│   ├── config.py           # from aizen_config.py
│   ├── health.py           # from aizen_health.py
│   ├── resilience.py       # from aizen_resilience.py
│   └── logging.py          # from aizen_logging.py
│
├── server/                  # Server components
│   ├── __init__.py
│   ├── main.py             # from server.py
│   ├── supervisor.py      # from supervisor.py
│   └── shutdown.py        # from shutdown.py
│
├── tools/                   # Tool system (RESTRUCTURE)
│   ├── __init__.py
│   ├── core/               # Registry, model_tools, toolsets
│   ├── terminal/           # terminal_tool, process_registry
│   ├── web/                # web_tools, browser_tool
│   ├── memory/             # memory_tool, session_search
│   └── execution/          # code_execution, etc
│
└── skills/                  # Skill system
    └── ...
```

## Phase 1: Create Backward-Compatible Shims (No Breaking Changes)

### Step 1.1: Create src/ directory structure

```bash
mkdir -p src/agent src/cli src/shared src/server
```

### Step 1.2: Create shim files that redirect to old locations

This allows gradual migration without breaking existing imports.

## Phase 2: Extract Logic from Monster Files

### Step 2.1: Extract from run_agent.py (~9k lines)

Logical divisions:
- Lines 1-250: Imports, constants, helper classes
- Lines 251-435: Tool execution helpers (parallel, sequential)
- Lines 436-900: AIAgent class definition (__init__)
- Lines 901-2000: System prompt building
- Lines 2001-3000: API client management
- Lines 3001-4000: Tool call execution
- Lines 4001-6000: Core conversation loop
- Lines 6001-9090: run_conversation method

Proposed extraction:
- `src/agent/engine.py` - AIAgent class (keep as minimal wrapper)
- `src/agent/client.py` - OpenAI client, credential refresh
- `src/agent/context.py` - Context compression
- `src/agent/tools.py` - Tool execution logic

### Step 2.2: Extract from cli.py (~8k lines)

Logical divisions:
- Lines 1-400: Imports, constants
- Lines 401-889: Helper functions
- Lines 890-1086: ChatConsole class
- Lines 1087+: AizenCLI class

Proposed extraction:
- `src/cli/interface.py` - Main CLI classes
- `src/cli/commands.py` - Command handlers
- `src/cli/repl.py` - REPL functionality

## Phase 3: Consolidate Root Files

### Files to move:

| Current | Target |
|----------|---------|
| `sdk.py` | `src/sdk.py` |
| `server.py` | `src/server/main.py` |
| `supervisor.py` | `src/server/supervisor.py` |
| `shutdown.py` | `src/server/shutdown.py` |
| `utils.py` | `src/shared/utils.py` |
| `aizen_config.py` | `src/shared/config.py` |
| `aizen_health.py` | `src/shared/health.py` |
| `aizen_resilience.py` | `src/shared/resilience.py` |
| `aizen_logging.py` | `src/shared/logging.py` |
| `trajectory_compressor.py` | `src/agent/trajectory.py` |

## Phase 4: Restructure tools/ Folder

Current: 40+ files in single folder
Target: Logical grouping

```
tools/
├── __init__.py           # Re-exports
├── core/                 # Registry, model_tools, toolsets
│   ├── __init__.py
│   ├── registry.py
│   ├── model_tools.py
│   └── toolsets.py
├── terminal/             # Terminal/Process tools
│   ├── __init__.py
│   ├── terminal_tool.py
│   └── process_registry.py
├── web/                  # Web tools
│   ├── __init__.py
│   ├── web_tools.py
│   ├── browser_tool.py
│   └── vision_tools.py
├── memory/               # Memory/Session tools
│   ├── __init__.py
│   ├── memory_tool.py
│   └── session_search_tool.py
├── skills/               # Skill tools
│   ├── __init__.py
│   ├── skills_tool.py
│   ├── skill_manager_tool.py
│   └── skills_hub.py
├── mcp/                  # MCP tools
│   └── mcp_tool.py
└── ...                   # Other tools
```

## Phase 5: Audit web/ Folder

```
web/ (186MB) - investigate:
├── Check for unnecessary dependencies
├── Move static assets elsewhere
├── Remove unused files
```

## Implementation Priority

1. **HIGH IMPACT**: Extract `run_agent.py` core logic (e.g., create `src/agent/`)
2. **HIGH IMPACT**: Extract `cli.py` core logic (e.g., create `src/cli/`)
3. **MEDIUM IMPACT**: Move `aizen_*.py` → `src/shared/`
4. **MEDIUM IMPACT**: Move `server.py`, `supervisor.py` → `src/server/`
5. **LOW IMPACT**: Restructure `tools/` (lower priority - already organized reasonably)

## Backward Compatibility Strategy

During transition, maintain:

```python
# run_agent.py - shim that imports from new location
from src.agent.engine import AIAgent

# cli.py - shim
from src.cli.interface import AizenCLI, ChatConsole

# This allows:
# 1. Old imports to still work: from run_agent import AIAgent
# 2. New code to use: from src.agent.engine import AIAgent
# 3. Gradual migration over time
```

## Migration Commands

```bash
# After implementing changes:
# Update imports in:
# - aizen script
# - setup.py / pyproject.toml
# - test files

# Then remove old files:
# rm run_agent.py cli.py
# rm sdk.py server.py aizen_*.py utils.py
```
