# Detailed Task List: run_agent.py & cli.py Refactoring

## Quick Reference

| File | Lines | Sections | New Files Needed |
|------|-------|-----------|------------------|
| run_agent.py | 9,271 | 5 | 7 |
| cli.py | 8,797 | 5 | 4 |

---

## RUN_AGENT.PY TASKS

### Priority 1: Tool Execution Helpers (Low Risk)

**File**: `src/agent/tool_helpers.py`
**Extract from**: run_agent.py SECTION 2 (lines ~136-347)

- [ ] `_NEVER_PARALLEL_TOOLS` - frozenset
- [ ] `_PARALLEL_SAFE_TOOLS` - frozenset
- [ ] `_PATH_SCOPED_TOOLS` - frozenset
- [ ] `_MAX_TOOL_WORKERS` - int
- [ ] `_DESTRUCTIVE_PATTERNS` - regex
- [ ] `_REDIRECT_OVERWRITE` - regex
- [ ] `_is_destructive_command(cmd: str) -> bool`
- [ ] `_should_parallelize_tool_batch(tool_calls) -> bool`
- [ ] `_extract_parallel_scope_path(tool_name: str, function_args: dict) -> Path | None`
- [ ] `_paths_overlap(left: Path, right: Path) -> bool`
- [ ] `_sanitize_surrogates(text: str) -> str`
- [ ] `_sanitize_messages_surrogates(messages: list) -> bool`
- [ ] `_strip_budget_warnings_from_history(messages: list) -> None`

**Dependencies**: None (pure functions)

---

### Priority 2a: AIAgent.__init__ (Medium Risk)

**File**: `src/agent/aizen_init.py`
**Extract from**: run_agent.py SECTION 3 (lines ~453-900)

- [ ] Full `__init__` method (450+ lines)
- [ ] Property definitions (base_url setter/getter)
- [ ] All instance variable initializations

**Dependencies**: 
- IterationBudget (already extracted)
- Various config parameters

---

### Priority 2b: System Prompt Building (Medium Risk)

**File**: `src/agent/system_prompt.py`
**Extract from**: SECTION 3 (lines ~2406-2572)

- [ ] `_build_system_prompt()` (~160 lines)
- [ ] `_get_tool_call_id_static(tc)` 
- [ ] `_sanitize_api_messages()` (~60 lines)
- [ ] `_cap_delegate_task_calls()`
- [ ] `_deduplicate_tool_calls()`
- [ ] `_repair_tool_call()`

**Dependencies**: 
- prompt_builder from agent/ package

---

### Priority 2c: OpenAI Client Management (Medium Risk)

**File**: `src/agent/client_manager.py`
**Extract from**: SECTION 3 (lines ~3384-3620)

- [ ] `_thread_identity()`
- [ ] `_client_log_context()`
- [ ] `_openai_client_lock()`
- [ ] `_is_openai_client_closed()`
- [ ] `_create_openai_client()`
- [ ] `_close_openai_client()`
- [ ] `_replace_primary_openai_client()`
- [ ] `_ensure_primary_openai_client()`
- [ ] `_create_request_openai_client()`
- [ ] `_run_codex_stream()` (~100 lines)
- [ ] `_run_codex_create_stream_fallback()` (~50 lines)
- [ ] Credential refresh methods (~150 lines)

**Dependencies**: 
- OpenAI SDK

---

### Priority 2d: Tool Execution (High Risk)

**File**: `src/agent/tool_execution.py`
**Extract from**: SECTION 3 (lines ~5346-5700)

- [ ] `_execute_tool_calls()` (~30 lines)
- [ ] `_invoke_tool()` (~80 lines)
- [ ] `_execute_tool_calls_concurrent()` (~350 lines)
- [ ] `_execute_tool_calls_sequential()` (~350 lines)
- [ ] `_get_budget_warning()`
- [ ] `_emit_context_pressure()`
- [ ] `_handle_max_iterations()`

**Dependencies**:
- tool registry
- handle_function_call

---

### Priority 3: Core Conversation Loop (Very High Risk)

**File**: `src/agent/conversation.py`
**Extract from**: SECTION 4 (lines ~6291-9026)

- [ ] `run_conversation()` (~2700 lines)
- [ ] All nested helper methods inside run_conversation

**Warning**: This is the hardest extraction. Consider keeping inline initially.

---

### Priority 4: Entry Points (Low Risk)

**File**: `src/agent/entry_points.py`
**Extract from**: SECTION 5 (lines ~9026-end)

- [ ] `chat()` method
- [ ] `main()` function

---

## CLI.PY TASKS

### Priority 1: AizenCLI.__init__ (Medium Risk)

**File**: `src/cli/aizen_init.py`
**Extract from**: SECTION 4 (lines ~1097-2000)

- [ ] Full `__init__` method (900+ lines)
- [ ] Instance variable setup
- [ ] Callback initialization

---

### Priority 2: Command Handlers (High Risk)

**File**: `src/cli/command_handlers.py`
**Extract from**: SECTION 4 (lines ~2000-5000)

**Sub-tasks**:
- [ ] `_handle_session_new()`
- [ ] `_handle_session_resume()`
- [ ] `_handle_session_list()`
- [ ] `_handle_config_get()`
- [ ] `_handle_config_set()`
- [ ] `_handle_tools_list()`
- [ ] `_handle_skills_list()`
- [ ] `_handle_model_switch()`
- [ ] `_handle_status()`
- [ ] `_handle_clear()`

**Dependencies**: 
- Multiple tool imports

---

### Priority 3: Interactive Loop (High Risk)

**File**: `src/cli/interactive.py`
**Extract from**: SECTION 4 (lines ~5000-8000)

- [ ] `_run_interactive_loop()`
- [ ] `_process_user_input()`
- [ ] Input validation
- [ ] Stream handling

---

### Priority 4: AizenCLI Helpers (Low Risk)

**File**: `src/cli/aizen_helpers.py`
**Extract from**: SECTION 4 (lines ~8000-8576)

- [ ] `_print_welcome()`
- [ ] `_print_exit_summary()`
- [ ] `_format_session_info()`
- [ ] Other utility methods

---

## EXECUTION CHECKLIST

### Before Starting Any Task:

```bash
# 1. Create backup
git checkout -b refactor-backup

# 2. Run tests to establish baseline
python -m pytest tests/test_agent_guardrails.py -x -q --tb=short 2>/dev/null | tail -5

# 3. Verify imports work
python -c "from run_agent import AIAgent; print('OK')"
python -c "from cli import AizenCLI; print('OK')"
```

### For Each Extraction:

```bash
# 1. Create new file with extracted code
# 2. Add import in original file
# 3. Test: python -c "from run_agent import AIAgent"
# 4. Run quick test: python -m pytest tests/test_agent_guardrails.py -x -q --tb=short
# 5. If fails: git checkout -- .
# 6. Commit: git add -A && git commit -m "Extract X to src/agent/"
```

---

## TESTING COMMANDS

```bash
# Quick smoke test
python -c "from run_agent import AIAgent, main; print('run_agent OK')"
python -c "from cli import AizenCLI, ChatConsole, main; print('cli OK')"

# Full test suite
python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20

# Specific tests
python -m pytest tests/test_compression_persistence.py -x -q --tb=short 2>/dev/null | tail -10
python -m pytest tests/test_cli_tools_command.py -x -q --tb=short 2>/dev/null | tail -10
```

---

## PROGRESS TRACKER

### run_agent.py
- [ ] 1.1 Tool helpers (SECTION 2)
- [ ] 2a AIAgent.__init__ (SECTION 3a)
- [ ] 2b System prompt (SECTION 3b)
- [ ] 2c Client manager (SECTION 3c)
- [ ] 2d Tool execution (SECTION 3d)
- [ ] 3 Core loop (SECTION 4)
- [ ] 4 Entry points (SECTION 5)

### cli.py
- [ ] 1 AizenCLI.__init__ (SECTION 4a)
- [ ] 2 Command handlers (SECTION 4b)
- [ ] 3 Interactive loop (SECTION 4c)
- [ ] 4 Helpers (SECTION 4d)

---

## FILES CREATED MAPPING

```
src/agent/
├── __init__.py
├── safe_writer.py           ✓ DONE
├── iteration_budget.py      ✓ DONE
├── tool_helpers.py          ☐ TASK 1.1
├── aizen_init.py            ☐ TASK 2a
├── system_prompt.py         ☐ TASK 2b
├── client_manager.py        ☐ TASK 2c
├── tool_execution.py        ☐ TASK 2d
├── conversation.py          ☐ TASK 3
└── entry_points.py           ☐ TASK 4

src/cli/
├── __init__.py
├── config.py                ✓ DONE
├── worktree.py              ✓ DONE
├── display.py               ✓ DONE
├── chatconsole.py            ✓ DONE
├── aizen_init.py             ☐ TASK 1
├── command_handlers.py       ☐ TASK 2
├── interactive.py            ☐ TASK 3
└── aizen_helpers.py           ☐ TASK 4
```
