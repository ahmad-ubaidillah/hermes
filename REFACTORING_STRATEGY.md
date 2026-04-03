# Refactoring Strategy: run_agent.py & cli.py

## Executive Summary

Two monster files need to be broken down:
- **run_agent.py**: 9,271 lines - AIAgent class + helper functions
- **cli.py**: 8,797 lines - AizenCLI + ChatConsole classes + helpers

**Strategy**: Extract by SECTION boundaries yang sudah ada di file, dengan pendekatan "extract to new file, then import back" untuk menjaga backward compatibility.

---

## Part 1: run_agent.py Refactoring

### Current Sections (udah ada markers)

```
run_agent.py:
├── SECTION 1: Helper Classes - _SafeWriter, IterationBudget    [ALREADY EXTRACTED]
├── SECTION 2: Tool Execution Helpers - parallelization         [IN PLACE]
├── SECTION 3: AIAgent Class Definition                           [IN PLACE]
├── SECTION 4: Core Conversation Loop - run_conversation        [IN PLACE]
└── SECTION 5: Entry Points - chat(), main()                    [IN PLACE]
```

### Task List run_agent.py

#### Task 1.1: Extract Tool Execution Helpers (SECTION 2)
**Current**: Lines ~136-347 (~211 lines)

```python
# Files to create:
src/agent/tool_helpers.py
```

**Extract these items**:
- [ ] `_NEVER_PARALLEL_TOOLS` - frozenset
- [ ] `_PARALLEL_SAFE_TOOLS` - frozenset  
- [ ] `_PATH_SCOPED_TOOLS` - frozenset
- [ ] `_MAX_TOOL_WORKERS` - int
- [ ] `_DESTRUCTIVE_PATTERNS` - regex
- [ ] `_REDIRECT_OVERWRITE` - regex
- [ ] `_is_destructive_command()` - function
- [ ] `_should_parallelize_tool_batch()` - function
- [ ] `_extract_parallel_scope_path()` - function
- [ ] `_paths_overlap()` - function
- [ ] `_sanitize_surrogates()` - function
- [ ] `_sanitize_messages_surrogates()` - function
- [ ] `_strip_budget_warnings_from_history()` - function

**After**: Update import di run_agent.py:
```python
from src.agent.tool_helpers import (
    _NEVER_PARALLEL_TOOLS, _PARALLEL_SAFE_TOOLS, _PATH_SCOPED_TOOLS,
    _MAX_TOOL_WORKERS, _DESTRUCTIVE_PATTERNS, _REDIRECT_OVERWRITE,
    _is_destructive_command, _should_parallelize_tool_batch,
    _extract_parallel_scope_path, _paths_overlap,
    _sanitize_surrogates, _sanitize_messages_surrogates,
    _strip_budget_warnings_from_history,
)
```

---

#### Task 1.2: Extract AIAgent Class Methods (SECTION 3)
**Current**: Lines ~348-9026 (8678 lines)

**Strategy**: Split by method groups:

```
src/agent/aizen_init.py      # __init__ method only (~500 lines)
src/agent/system_prompt.py   # _build_system_prompt + related (~600 lines)
src/agent/client_manager.py  # OpenAI client management (~500 lines)
src/agent/tool_execution.py # Tool call execution (~1500 lines)
src/agent/message_handlers.py # Message formatting (~500 lines)
```

**Extract sequence**:

1. **aizen_init.py** - __init__ method (lines 453-900)
   - [ ] Copy full __init__ method
   - [ ] Create class stub in new file
   - [ ] Update import in original location

2. **system_prompt.py** - System prompt building (lines 901-2000)
   - [ ] _build_system_prompt()
   - [ ] _get_tool_call_id_static()
   - [ ] _sanitize_api_messages()
   - [ ] Helper methods

3. **client_manager.py** - OpenAI client (lines 2001-3000)
   - [ ] _create_openai_client()
   - [ ] _ensure_primary_openai_client()
   - [ ] _create_request_openai_client()
   - [ ] Credential refresh methods
   - [ ] _run_codex_stream()

4. **tool_execution.py** - Tool execution (lines 3001-4500)
   - [ ] _execute_tool_calls()
   - [ ] _invoke_tool()
   - [ ] _execute_tool_calls_concurrent()
   - [ ] _execute_tool_calls_sequential()

5. **message_handlers.py** - Message formatting
   - [ ] _convert_to_trajectory_format()
   - [ ] _format_tools_for_system_message()
   - [ ] Other formatting helpers

---

#### Task 1.3: Extract Core Loop (SECTION 4)
**Current**: Lines ~9026-9080 (~3000+ lines)

```
src/agent/conversation.py
```

**Extract**:
- [ ] run_conversation() - the main loop (3000+ lines)
- [ ] All nested helper methods inside run_conversation

**Note**: This is the hardest task. Consider extracting only the method signature and keeping the body in place initially.

---

#### Task 1.4: Extract Entry Points (SECTION 5)
**Current**: Lines ~9080+ (chat + main)

```
src/agent/entry_points.py
```

**Extract**:
- [ ] chat() method
- [ ] main() function

---

## Part 2: cli.py Refactoring

### Current Sections

```
cli.py:
├── SECTION 1: Configuration Loading          [ALREADY EXTRACTED]
├── SECTION 2: Worktree/Git Helpers            [ALREADY EXTRACTED]
├── SECTION 3: ChatConsole Class               [ALREADY EXTRACTED]
├── SECTION 4: AizenCLI Class                  [IN PLACE]
└── SECTION 5: Main Entry Point                [IN PLACE]
```

### Task List cli.py

#### Task 2.1: Extract AizenCLI.__init__ (SECTION 4a)
**Current**: Lines ~1097-2000 (~900 lines)

```
src/cli/aizen_init.py
```

**Extract**:
- [ ] AizenCLI.__init__ method
- [ ] Property definitions

---

#### Task 2.2: Extract AizenCLI Command Handlers (SECTION 4b)
**Current**: Lines ~2000-5000 (~3000 lines)

```
src/cli/command_handlers.py
```

**Strategy**: Group by command category:

1. **Session commands** (_handle_session_*)
2. **Config commands** (_handle_config_*)
3. **Tool/Skill commands** (_handle_tools_*, _handle_skills_*)
4. **Utility commands** (model, status, etc)

**Extract**:
- [ ] All _handle_* methods
- [ ] Group into logical files

---

#### Task 2.3: Extract AizenCLI Interactive Loop (SECTION 4c)
**Current**: Lines ~5000-8000 (~3000 lines)

```
src/cli/interactive.py
```

**Extract**:
- [ ] _run_interactive_loop()
- [ ] _process_user_input()
- [ ] Input handling methods

---

#### Task 2.4: Extract AizenCLI Helpers (SECTION 4d)
**Current**: Lines ~8000-8576 (~500 lines)

```
src/cli/aizen_helpers.py
```

**Extract**:
- [ ] _print_welcome()
- [ ] _print_exit_summary()
- [ ] Other helper methods

---

## Extraction Pattern ( Gunakan untuk semua )

### Step 1: Create new file
```python
# src/agent/[module_name].py
"""Module description."""

# Copy the code here
```

### Step 2: Update original file (tambahkan import)
```python
# run_agent.py / cli.py
from src.agent.[module_name] import (
    # items yang di-extract
)
```

### Step 3: Test
```bash
python -c "from run_agent import AIAgent"
python -c "from cli import AizenCLI"
```

### Step 4: Remove original (after verifying)
```python
# Remove the duplicate code from original location
# Keep only the import
```

---

## Risk Mitigation

### Before Starting Any Extraction:
1. ✅ Create backup branch: `git checkout -b refactor-backup`
2. ✅ Run existing tests: `python -m pytest tests/ -x -q --tb=short`

### During Extraction:
- Never modify logic - copy as-is
- Keep all edge cases
- Test after each extraction

### Backward Compatibility:
- Keep old import paths working
- Use re-export in original location:
```python
# run_agent.py - after extraction
from src.agent.tool_helpers import (
    _NEVER_PARALLEL_TOOLS,  # Re-export for backward compat
)
# Original code still works
_NEVER_PARALLEL_TOOLS  # This still works
```

---

## Verification Commands

```bash
# Test all imports still work
python -c "from run_agent import AIAgent, main"
python -c "from cli import AizenCLI, ChatConsole, main"

# Run quick tests
python -m pytest tests/test_agent_guardrails.py -x -q --tb=short -k "test_" 2>/dev/null || true
python -m pytest tests/test_cli_tools_command.py -x -q --tb=short 2>/dev/null || true

# Check syntax
python -m py_compile run_agent.py
python -m py_compile cli.py
```

---

## Estimated Timeline

| Task | Effort | Estimated Time |
|------|--------|----------------|
| 1.1 Extract tool helpers | Low | 30 min |
| 1.2a Extract aizen_init | Medium | 1-2 hours |
| 1.2b Extract system_prompt | Medium | 1-2 hours |
| 1.2c Extract client_manager | Medium | 1-2 hours |
| 1.2d Extract tool_execution | High | 3-4 hours |
| 1.3 Extract conversation loop | Very High | 1-2 days |
| 1.4 Extract entry points | Low | 30 min |
| 2.1 Extract aizen_init | Medium | 1-2 hours |
| 2.2 Extract commands | High | 3-4 hours |
| 2.3 Extract interactive | High | 2-3 hours |
| 2.4 Extract helpers | Medium | 1 hour |

**Total: ~1-2 weeks with careful testing**

---

## Priority Order

```
PRIORITY 1 (Start here - Low Risk):
├── Task 1.1: Tool helpers in run_agent.py
├── Task 1.4: Entry points (just move to end of file)
└── Task 2.4: AizenCLI helpers

PRIORITY 2 (Medium Risk):
├── Task 1.2a: aizen_init
├── Task 1.2b: system_prompt
├── Task 2.1: AizenCLI.__init__
└── Task 2.2: Command handlers

PRIORITY 3 (Higher Risk):
├── Task 1.2c: client_manager
├── Task 1.2d: tool_execution
└── Task 2.3: Interactive loop

PRIORITY 4 (Highest Risk - do last):
└── Task 1.3: Core conversation loop
```

---

## Files to Create Summary

```
src/agent/
├── safe_writer.py           [DONE]
├── iteration_budget.py     [DONE]
├── tool_helpers.py          [NEW - Task 1.1]
├── aizen_init.py           [NEW - Task 1.2a]
├── system_prompt.py        [NEW - Task 1.2b]
├── client_manager.py       [NEW - Task 1.2c]
├── tool_execution.py       [NEW - Task 1.2d]
├── conversation.py         [NEW - Task 1.3]
└── entry_points.py         [NEW - Task 1.4]

src/cli/
├── config.py               [DONE]
├── worktree.py            [DONE]
├── display.py              [DONE]
├── chatconsole.py          [DONE]
├── aizen_init.py          [NEW - Task 2.1]
├── command_handlers.py    [NEW - Task 2.2]
├── interactive.py         [NEW - Task 2.3]
└── aizen_helpers.py       [NEW - Task 2.4]
```
