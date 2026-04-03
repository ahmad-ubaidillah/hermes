# AIAgent Modularization Blueprint

**Date**: 2026-04-02
**Status**: Ready for Implementation
**Estimated Effort**: 17 hours

---

## Executive Summary

This blueprint provides a detailed extraction plan for the AIAgent class (9,348 lines, 115 methods) into maintainable, focused modules.

## Recommended Module Structure

```
agent/
├── __init__.py           # Public API exports
├── core.py               # AIAgent class (core initialization, properties)
├── execution.py          # Tool execution logic
├── messaging.py          # API communication and message handling
├── session.py            # Session and memory management
└── utils.py              # Helper classes and utilities
```

## Method Extraction Plan

### 1. agent/core.py (~800 lines)

**Purpose**: Core AIAgent class with initialization and properties

**Methods to extract (15)**:
```python
class AIAgent:
    def __init__(self, ...):                    # Lines 453-1100 (647 lines)
    def base_url(self) -> str:                  # Property getter
    def base_url(self, value: str) -> None:     # Property setter
    def reset_session_state(self):              # State management
    def _safe_print(self, *args, **kwargs):     # Output handling
    def _vprint(self, *args, force: bool, ...):  # Verbose output
    def _emit_status(self, message: str):       # Status updates
    def _is_direct_openai_url(self, ...):       # Provider detection
    def _is_openrouter_url(self) -> bool:       # Provider detection
    def _is_anthropic_url(self) -> bool:        # Provider detection
    def _max_tokens_param(self, value: int):    # API parameter
    def _has_content_after_think_block(...):    # Content processing
    def _strip_think_blocks(self, content):     # Content processing
    def _looks_like_codex_intermediate_ack():   # Response handling
```

**Estimated lines**: 800-1000

---

### 2. agent/execution.py (~1,800 lines)

**Purpose**: Tool execution and context management

**Methods to extract (20)**:
```python
class ToolExecutor:
    def _execute_tool_calls(self, ...):                    # Main tool execution
    def _execute_tool_calls_sequential(self, ...):         # Sequential execution
    def _execute_tool_calls_concurrent(self, ...):         # Parallel execution
    def _invoke_tool(self, ...):                           # Single tool invocation
    def _compress_context(self, messages: list):          # Context compression
    def _get_budget_warning(self, api_call_count):        # Budget warnings
    def _handle_max_iterations(self, messages, count):    # Iteration limits
    def _emit_context_pressure(self, progress, compressor): # Context pressure
    def _cap_delegate_task_calls(self, tool_calls):       # Delegate call limiting
    def _deduplicate_tool_calls(self, tool_calls):        # Deduplication
    def _repair_tool_call(self, tool_name: str):          # Tool call repair
    def _sanitize_api_messages(self, messages):           # Message sanitization
    def _get_tool_call_id_static(self, tc):               # ID extraction
    def _sanitize_tool_calls_for_strict_api(self, ...):   # API compliance
    def _build_assistant_message(self, ...):              # Message building
    def _github_models_reasoning_extra_body(self):        # GitHub models support
    def _supports_reasoning_extra_body(self) -> bool:     # Reasoning support check
    def _fire_tool_gen_started(self, tool_name):          # Tool event
    def _fire_tool_result(self, tool_name, result):       # Tool event
    def _fire_reasoning_delta(self, text: str):           # Reasoning event
```

**Estimated lines**: 1,800-2,000

---

### 3. agent/messaging.py (~3,000 lines)

**Purpose**: API communication, streaming, and message formatting

**Methods to extract (35)**:
```python
class MessagingHandler:
    def _build_api_kwargs(self, api_messages: list):    # API parameters
    def _anthropic_preserve_dots(self) -> bool:          # Anthropic support
    def _prepare_anthropic_messages_for_api(self, ...): # Anthropic messages
    def _preprocess_anthropic_content_for_api(self, ...): # Anthropic content
    def _describe_image_for_anthropic_fallback(self, ...): # Image handling
    def _materialize_data_url_for_vision(self, ...):     # Vision support
    def _content_has_image_parts(self, content):        # Image detection
    def _try_activate_fallback(self) -> bool:           # Fallback activation
    def _interruptible_streaming_api_call(self, ...):   # Streaming API
    def _has_stream_consumers(self) -> bool:            # Stream detection
    def _fire_stream_delta(self, text: str):            # Stream event
    def _responses_tools(self, ...):                    # Responses API tools
    def _deterministic_call_id(fn_name, arguments, index): # ID generation
    def _split_responses_tool_id(raw_id):               # ID parsing
    def _derive_responses_function_call_id(...):        # Function call ID
    def _chat_messages_to_responses_input(...):         # Message conversion
    def _preflight_codex_input_items(self, ...):        # Codex preprocessing
    def _preflight_codex_api_kwargs(self, ...):         # Codex API setup
    def _extract_responses_message_text(item):          # Text extraction
    def _summarize_api_error(error):                    # Error handling
    def _mask_api_key_for_logs(key):                    # Key masking
    def _clean_error_message(error_msg):                # Error cleaning
    def _dump_api_request_debug(...):                   # Debug logging
    def _clean_session_content(content):                # Content cleaning
    def _save_session_log(messages):                    # Session logging
```

**Estimated lines**: 2,500-3,000

---

### 4. agent/session.py (~1,000 lines)

**Purpose**: Session and memory management

**Methods to extract (15)**:
```python
class SessionManager:
    def _spawn_background_review(self, ...):             # Background tasks
    def _apply_persist_user_message_override(self, ...): # Message persistence
    def _persist_session(self, ...):                     # Session saving
    def _flush_messages_to_session_db(self, ...):       # Database flush
    def _get_messages_up_to_last_assistant(self, ...):  # Message retrieval
    def _format_tools_for_system_message(self):         # Tool formatting
    def _convert_to_trajectory_format(self, ...):       # Trajectory conversion
    def _save_trajectory(self, ...):                    # Trajectory saving
    def _hydrate_todo_store(self, history):             # Todo restoration
    def interrupt(self, message=None):                  # Interrupt handling
    def clear_interrupt(self):                          # Interrupt clearing
    def is_interrupted(self) -> bool:                   # Interrupt status
    def _build_system_prompt(self, ...):                # System prompt building
    def _invalidate_system_prompt(self):                # Cache invalidation
```

**Estimated lines**: 1,000-1,200

---

### 5. agent/utils.py (~500 lines)

**Purpose**: Helper classes and utility functions

**Classes**:
```python
class _SafeWriter:
    def __init__(self, inner):
    def write(self, data):
    def flush(self):
    def fileno(self):
    def isatty(self):
    def __getattr__(self, name):

class IterationBudget:
    def __init__(self, max_total: int):
    def consume(self) -> bool:
    def refund(self) -> None:
    def used(self) -> int:
    def remaining(self) -> int:
```

**Functions**:
```python
def _install_safe_stdio() -> None:
def _is_destructive_command(cmd: str) -> bool:
def _should_parallelize_tool_batch(tool_calls) -> bool:
def _extract_parallel_scope_path(tool_name: str, args: dict) -> Path | None:
def _paths_overlap(left: Path, right: Path) -> bool:
def _sanitize_surrogates(text: str) -> str:
def _sanitize_messages_surrogates(messages: list) -> bool:
def _strip_budget_warnings_from_history(messages: list) -> None:
```

**Estimated lines**: 500-600

---

## Refactoring Steps

### Step 1: Create module structure (15 min)
```bash
mkdir -p agent
touch agent/__init__.py
touch agent/core.py
touch agent/execution.py
touch agent/messaging.py
touch agent/session.py
touch agent/utils.py
```

### Step 2: Extract utilities (30 min)
**Risk**: LOW
- Move `_SafeWriter`, `IterationBudget` classes
- Move helper functions
- Update imports in run_agent.py

### Step 3: Extract session management (1 hour)
**Risk**: MEDIUM
- Move session-related methods to agent/session.py
- Test session persistence
- Update imports

### Step 4: Extract execution logic (2 hours)
**Risk**: MEDIUM-HIGH
- Move tool execution methods to agent/execution.py
- Test tool calls
- Update imports

### Step 5: Extract messaging (3 hours)
**Risk**: HIGH
- Move API communication methods to agent/messaging.py
- Test API calls
- Update imports

### Step 6: Extract core (2 hours)
**Risk**: HIGH
- Move initialization and core logic to agent/core.py
- Test initialization
- Update imports across codebase

---

## Testing Strategy

After each extraction:
1. Run unit tests: `pytest tests/test_model_tools.py -v`
2. Test imports: `python -c "from run_agent import AIAgent"`
3. Test initialization: Create agent instance
4. Test tool execution: Run simple query
5. Run full suite: `pytest tests/ -q`

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Circular imports | HIGH | Use lazy imports in __init__.py |
| Breaking tests | HIGH | Run tests after each extraction |
| Import errors | HIGH | Use IDE refactoring tools |
| Runtime errors | MEDIUM | Incremental extraction with testing |

---

## Estimated Effort

| Phase | Hours | Risk |
|-------|-------|------|
| Analysis and planning | 2 | LOW |
| Extract utilities | 1 | LOW |
| Extract session | 2 | MEDIUM |
| Extract execution | 3 | MEDIUM |
| Extract messaging | 4 | HIGH |
| Extract core | 3 | HIGH |
| Testing and verification | 2 | MEDIUM |
| **Total** | **17** | |

---

## Next Steps

1. Review this plan with team
2. Prioritize phases based on risk tolerance
3. Schedule refactoring sprint
4. Assign developers to each phase
5. Set up CI/CD for automated testing

---

*Documentation created by: Sisyphus Agent*
*Ready for: Phase D-2 (Extract CLI classes)*