# Refactoring Tasks - Phase by Phase

## Overview

Gradual refactoring plan untuk pecah monster files (run_agent.py 9k+ lines, cli.py 8k+ lines) sambil menjaga backward compatibility.

---

## Phase 1: Add Section Markers (LOW RISK)
**Tujuan**: Mempermudah navigasi dan identifikasi section boundaries

### Task 1.1: Add Section Markers ke run_agent.py
- [ ] Section 1: Imports & Constants (lines 1-250)
- [ ] Section 2: Helper Classes - _SafeWriter, IterationBudget (lines 251-435)
- [ ] Section 3: Tool Execution Helpers - _NEVER_PARALLEL_TOOLS, _should_parallelize_tool_batch, etc (lines 251-435)
- [ ] Section 4: AIAgent.__init__ (lines 436-900)
- [ ] Section 5: System Prompt Building (lines 901-2000)
- [ ] Section 6: API Client Management (lines 2001-3000)
- [ ] Section 7: Tool Call Execution (lines 3001-4000)
- [ ] Section 8: Core Conversation Loop (lines 4001-6000)
- [ ] Section 9: run_conversation method (lines 6001-9090)
- [ ] Section 10: chat() + main() (lines 9090+)

### Task 1.2: Add Section Markers ke cli.py
- [ ] Section 1: Imports & Constants (lines 1-100)
- [ ] Section 2: Config Loading Functions (lines 101-530)
- [ ] Section 3: Worktree/Git Helpers (lines 531-860)
- [ ] Section 4: Display Helpers - _cprint, _build_compact_banner (lines 861-955)
- [ ] Section 5: ChatConsole Class (lines 890-1086)
- [ ] Section 6: AizenCLI Class - __init__ (lines 1087-2000)
- [ ] Section 7: AizenCLI Command Handlers (lines 2000-4000)
- [ ] Section 8: AizenCLI Interactive Loop (lines 4000-6000)
- [ ] Section 9: AizenCLI Helper Methods (lines 6000-8000)
- [ ] Section 10: main() (lines 8566+)

---

## Phase 2: Create Shim Files (LOW RISK)
**Tujuan**: Siapkan backward compatibility sebelum extract

### Task 2.1: Create src/agent/shims/
- [ ] Buat `src/agent/__init__.py` yang re-export dari agent/
- [ ] Buat `src/cli/__init__.py` yang re-export dari aizen_cli/
- [ ] Verifikasi semua existing imports masih jalan

### Task 2.2: Test Shim Compatibility
- [ ] Run `python -c "from run_agent import AIAgent"` - harus jalan
- [ ] Run `python -c "from cli import AizenCLI"` - harus jalan
- [ ] Fix jika ada broken imports

---

## Phase 3: Extract Helper Classes (MEDIUM RISK)
**Tujuan**: Pindahkan kode yang sudah self-contained

### Task 3.1: Extract _SafeWriter ke src/agent/utils.py
- [ ] Copy class definition ke `src/agent/safe_writer.py`
- [ ] Update import di run_agent.py: `from agent.safe_writer import _SafeWriter`
- [ ] Test still works

### Task 3.2: Extract IterationBudget ke src/agent/budget.py
- [ ] Copy class definition ke `src/agent/iteration_budget.py`
- [ ] Update import di run_agent.py
- [ ] Test still works

### Task 3.3: Extract Tool Execution Helpers ke src/agent/tool_helpers.py
- [ ] Copy _NEVER_PARALLEL_TOOLS, _PARALLEL_SAFE_TOOLS, _should_parallelize_tool_batch, etc
- [ ] Update import di run_agent.py
- [ ] Test still works

---

## Phase 4: Extract CLI Helpers (MEDIUM RISK)
**Tujuan**: Pindahkan fungsi-fungsi helper yang tidak bergantung pada class

### Task 4.1: Extract Config Functions ke src/cli/config.py
- [ ] Copy _load_prefill_messages, _parse_reasoning_config, load_cli_config
- [ ] Update import di cli.py
- [ ] Test still works

### Task 4.2: Extract Worktree Helpers ke src/cli/worktree.py
- [ ] Copy _git_repo_root, _path_is_within_root, _setup_worktree, _cleanup_worktree, _prune_stale_worktrees
- [ ] Update import di cli.py
- [ ] Test still works

### Task 4.3: Extract Display Helpers ke src/cli/display.py
- [ ] Copy _accent_hex, _rich_text_from_ansi, _cprint, _build_compact_banner
- [ ] Update import di cli.py
- [ ] Test still works

---

## Phase 5: Extract ChatConsole Class (MEDIUM RISK)
**Tujuan**: Pisahkan class yang相对 independent

### Task 5.1: Extract ChatConsole ke src/cli/chatconsole.py
- [ ] Copy entire ChatConsole class (lines 890-1086)
- [ ] Fix any missing imports
- [ ] Update cli.py: `from src.cli.chatconsole import ChatConsole`
- [ ] Test still works

### Task 5.2: Add Shim for Backward Compat
- [ ] Update original cli.py location to re-export from new location
- [ ] Verify `from cli import ChatConsole` still works

---

## Phase 6: Extract AizenCLI Class - Phase 1 (HIGH RISK)
**Tujuan**: Pecah class terbesar di cli.py

### Task 6.1: Extract AizenCLI.__init__ ke src/cli/aizen_cli_init.py
- [ ] Copy __init__ method only
- [ ] Create new file with class stub
- [ ] Update imports carefully

### Task 6.2: Extract Command Handlers ke src/cli/command_handlers.py
- [ ] Identify all _handle_* methods in AizenCLI
- [ ] Copy to separate file
- [ ] Update references

### Task 6.3: Extract Interactive Loop ke src/cli/interactive.py
- [ ] Copy _run_interactive_loop method
- [ ] Handle callback dependencies

---

## Phase 7: Extract AIAgent Class - Phase 1 (HIGH RISK)
**Tujuan**: Pecah class terbesar di run_agent.py

### Task 7.1: Extract AIAgent.__init__ ke src/agent/aizen_init.py
- [ ] Copy __init__ method and property definitions
- [ ] Create new file with minimal class stub

### Task 7.2: Extract System Prompt Builder ke src/agent/prompt_builder_extended.py
- [ ] Copy _build_system_prompt and related methods
- [ ] Move to separate file

### Task 7.3: Extract API Client Management ke src/agent/client_manager.py
- [ ] Copy _create_openai_client, _ensure_primary_openai_client, etc
- [ ] Move to separate file

---

## Phase 8: Extract Core Loop (HIGH RISK)
**Tujuan**: Pindahkan conversation loop logic

### Task 8.1: Extract Tool Call Execution ke src/agent/tool_executor.py
- [ ] Copy _execute_tool_calls, _invoke_tool, _execute_tool_calls_concurrent
- [ ] Copy _execute_tool_calls_sequential
- [ ] Move to separate file

### Task 8.2: Extract run_conversation ke src/agent/conversation.py
- [ ] Copy entire run_conversation method (3000+ lines)
- [ ] This is the core - handle with extra care

### Task 8.3: Extract Context Compression ke src/agent/context.py
- [ ] Already partially done in agent/context_compressor.py
- [ ] Integrate additional methods

---

## Phase 9: Final Cleanup (LOW RISK)
**Tujuan**: Rapikan dan hapus duplicate

### Task 9.1: Remove Duplicate Imports
- [ ] Check all files for redundant imports
- [ ] Clean up

### Task 9.2: Update All References
- [ ] Find all files importing from old locations
- [ ] Update to new structure

### Task 9.3: Final Compatibility Test
- [ ] Run full test suite
- [ ] Fix any remaining issues

### Task 9.4: Remove Old Shim Layers
- [ ] Once everything works, remove unnecessary shims
- [ ] Update documentation

---

## Backward Compatibility Rules

1. **Never break existing imports** - always create shims first
2. **One section per task** - test after each extraction
3. **Keep all edge cases** - don't "clean up" while moving
4. **Update REFS.md** - document what moved where

---

## Verification Commands

```bash
# Test imports still work
python -c "from run_agent import AIAgent"
python -c "from cli import AizenCLI, ChatConsole"

# Run basic tests
python -m pytest tests/test_agent_guardrails.py -x -q
python -m pytest tests/test_cli_tools_command.py -x -q

# Check for import errors
python -m py_compile run_agent.py
python -m py_compile cli.py
```

---

## Timeline Estimate

| Phase | Effort | Estimate |
|-------|--------|----------|
| Phase 1 | Low | 1 day |
| Phase 2 | Low | 1 day |
| Phase 3 | Medium | 3 days |
| Phase 4 | Medium | 3 days |
| Phase 5 | Medium | 3 days |
| Phase 6 | High | 1 week |
| Phase 7 | High | 1 week |
| Phase 8 | High | 1 week |
| Phase 9 | Low | 1 day |

**Total estimated: ~3-4 weeks with careful testing**
