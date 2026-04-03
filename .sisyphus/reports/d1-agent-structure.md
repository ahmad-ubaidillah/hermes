# AIAgent Class Structure - Modularization Plan

**File**: run_agent.py
**Lines**: 9,348
**Class**: AIAgent (lines 436-9105)
**Methods**: 115

## Method Categories

### 1. Initialization & Core (Lines 436-550)
- `__init__` - Constructor (100+ params!)
- `base_url` - Property getter/setter
- `reset_session_state()` - Session management
- `_safe_print()` - Output handling
- `_vprint()` - Verbose output
- `_emit_status()` - Status updates

### 2. Provider Detection (lines 1339-1380)
- `_is_direct_openai_url()`
- `_is_openrouter_url()`
- `_is_anthropic_url()`

### 3. Content processing (lines 1366-1500)
- `_max_tokens_param()`
- `_has_content_after_think_block()`
- `_strip_think_blocks()`
- `_looks_like_codex_intermediate_ack()`

### 4. Reasoning extraction (lines 1488-1590)
- `_extract_reasoning()`
- `_cleanup_task_resources()` - Resource management

### 5. Background Operations (lines 1611-1740)
- `_spawn_background_review()` - Memory/skill review
- `_apply_persist_user_message_override()`
- `_persist_session()`
- `_flush_messages_to_session_db()`

### 6. Message handling (lines 1758-1870)
- `_get_messages_up_to_last_assistant()`
- `_format_tools_for_system_message()`
- `_convert_to_trajectory_format()`
- `_save_trajectory()`
- `_save_session_log()`

### 7. API communication (lines 2061-2240)
- `_summarize_api_error()`
- `_mask_api_key_for_logs()`
- `_clean_error_message()`
- `_dump_api_request_debug()`
- `_clean_session_content()`

### 8. Interrupt handling (lines 2317-2410)
- `interrupt()` - Set interrupt flag
- `clear_interrupt()` - Clear interrupt
- `_hydrate_todo_store()` - Restore todos
- `is_interrupted()` - Check interrupt status
- `_build_system_prompt()` - Prompt assembly

### 9. API message processing (lines 2572-2650)
- `_get_tool_call_id_static()`
- `_sanitize_api_messages()`
- `_cap_delegate_task_calls()`
- `_deduplicate_tool_calls()`
- `_repair_tool_call()`

### 10. OpenAI Responses API (lines 2732-3170)
- `_invalidate_system_prompt()`
- `_responses_tools()`
- `_deterministic_call_id()`
- `_split_responses_tool_id()`
- `_derive_responses_function_call_id()`
- `_chat_messages_to_responses_input()`
- `_preflight_codex_input_items()`
- `_preflight_codex_api_kwargs()`
- `_extract_responses_message_text()`

### 11. Streaming & events (lines 3844-3870)
- `_fire_tool_gen_started()`
- `_fire_reasoning_delta()`
- `_fire_tool_result()`
- `_fire_stream_delta()`
- `_has_stream_consumers()`
- `_interruptible_streaming_api_call()`

### 12. Anthropic-specific (lines 4350-4650)
- `_try_activate_fallback()`
- `_content_has_image_parts()`
- `_materialize_data_url_for_vision()`
- `_describe_image_for_anthropic_fallback()`
- `_preprocess_anthropic_content_for_api()`
- `_prepare_anthropic_messages_for_api()`

### 13. API kwargs building (lines 4657-4690)
- `_build_api_kwargs()`
- `_anthropic_preserve_dots()`

### 14. Main conversation loop (lines 6371-7070)
- `run_conversation()` - Main entry point
- `chat()` - Simple interface
- `_compress_context()`
- `_execute_tool_calls()`
- `_execute_tool_calls_sequential()`
- `_execute_tool_calls_concurrent()`
- `_invoke_tool()`
- `_build_assistant_message()`
- `_sanitize_tool_calls_for_strict_api()`
- `_github_models_reasoning_extra_body()`
- `_supports_reasoning_extra_body()`
- `_emit_context_pressure()`
- `_get_budget_warning()`
- `_handle_max_iterations()`

### 15. Utility methods (lines 9090-9348)
- `main()` - CLI entry point
- `_SafeWriter` class
- `IterationBudget` class

- Helper functions

## Recommended Module Structure

### agent/core.py
**Purpose**: Core initialization and state management

**Methods to (~15):
```python
- __init__
- base_url (getter/setter)
- reset_session_state
- _safe_print
- _vprint
- _emit_status
- _is_direct_openai_url
- _is_openrouter_url
- _is_anthropic_url
- _max_tokens_param
- _has_content_after_think_block
- _strip_think_blocks
- _looks_like_codex_intermediate_ack
- _extract_reasoning
- _cleanup_task_resources
```

**Estimated lines**: ~500-700

### agent/execution.py
**Purpose**: Tool execution logic

**Methods** (~20):
```python
- _execute_tool_calls
- _execute_tool_calls_sequential
- _execute_tool_calls_concurrent
- _invoke_tool
- _cap_delegate_task_calls
- _deduplicate_tool_calls
- _repair_tool_call
- _get_tool_call_id_static
- _sanitize_api_messages
- _compress_context
- _get_budget_warning
- _handle_max_iterations
- _emit_context_pressure
```

**Estimated lines**: ~1,500-2,000

### agent/messaging.py
**Purpose**: Message handling and API communication

**Methods** (~30):
```python
- _build_system_prompt
- _sanitize_api_messages
- _build_api_kwargs
- _build_assistant_message
- _sanitize_tool_calls_for_strict_api
- _responses_tools
- _deterministic_call_id
- _split_responses_tool_id
- _derive_responses_function_call_id
- _chat_messages_to_responses_input
- _preflight_codex_input_items
- _preflight_codex_api_kwargs
- _extract_responses_message_text
- _interruptible_streaming_api_call
- _fire_tool_gen_started
- _fire_reasoning_delta
- _fire_tool_result
- _fire_stream_delta
- _has_stream_consumers
- _try_activate_fallback
- _content_has_image_parts
- _materialize_data_url_for_vision
- _describe_image_for_anthropic_fallback
- _preprocess_anthropic_content_for_api
- _prepare_anthropic_messages_for_api
- _anthropic_preserve_dots
- _github_models_reasoning_extra_body
- _supports_reasoning_extra_body
```

**Estimated lines**: ~2,500-3,000

### agent/session.py
**Purpose**: Session and memory management

**Methods** (~15):
```python
- _spawn_background_review
- _apply_persist_user_message_override
- _persist_session
- _flush_messages_to_session_db
- _get_messages_up_to_last_assistant
- _format_tools_for_system_message
- _convert_to_trajectory_format
- _save_trajectory
- _hydrate_todo_store
- interrupt
- clear_interrupt
- is_interrupted
- _invalidate_system_prompt
```

**Estimated lines**: ~1,000-1,500

### agent/utils.py
**Purpose**: Helper classes and utilities

**Classes**:
```python
- _SafeWriter
- IterationBudget
```

**Functions**:
```python
- _install_safe_stdio
- _is_destructive_command
- _should_parallelize_tool_batch
- _extract_parallel_scope_path
- _paths_overlap
- _sanitize_surrogates
- _sanitize_messages_surrogates
- _strip_budget_warnings_from_history
```

**Estimated lines**: ~500-700

## Refactoring Steps

### Step 1: Create module structure
```bash
mkdir -p agent/__init__.py
touch agent/core.py
touch agent/execution.py
touch agent/messaging.py
touch agent/session.py
touch agent/utils.py
```

### Step 2: Extract utilities (lowest risk)
- Move `_SafeWriter`, `IterationBudget` classes
- Move helper functions
- Update imports in run_agent.py

### Step 3: Extract session management
- Move session-related methods
- Test session persistence
- Update imports

### Step 4: Extract execution logic (medium risk)
- Move tool execution methods
- Test tool calls
- Update imports

### Step 5: Extract messaging (highest risk)
- Move API communication methods
- Test API calls
- Update imports

### Step 6: Extract core (highest risk)
- Move initialization and core logic
- Test initialization
- Update imports across codebase

## Testing Strategy

After each extraction:
1. Run unit tests: `pytest tests/test_model_tools.py -v`
2. Test imports: `python -c "from run_agent import AIAgent"`
3. Test initialization: Create agent instance
4. Test tool execution: Run simple query
5. Run full suite: `pytest tests/ -q`

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Circular imports | High | Use lazy imports in __init__.py |
| Breaking tests | High | Run tests after each extraction |
| Import errors | High | Use IDE refactoring tools |
| Runtime errors | Medium | Incremental extraction with testing |

## Estimated Effort

| Phase | Hours | Risk |
|-------|-------|------|
| Analysis & planning | 2 | Low |
| Extract utilities | 1 | Low |
| Extract session | 2 | Medium |
| Extract execution | 3 | Medium |
| Extract messaging | 4 | High |
| Extract core | 3 | High |
| Testing & verification | 2 | Medium |
| **Total** | **17** | |

## Next Steps

1. **Review this plan** with team
2. **Prioritize phases** based on risk tolerance
3. **Schedule refactoring sprint**
4. **Assign developers** to each phase
5. **Set up CI/CD** for automated testing

---

*Documentation created by: Sisyphus Agent*  
*Ready for: Phase D-2 (Extract CLI classes)*