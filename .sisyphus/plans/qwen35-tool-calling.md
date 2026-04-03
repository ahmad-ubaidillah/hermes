# Qwen3.5 Tool Calling + Local Mode Enhancement

## Context

**User Request**: Enable Qwen3.5 models running via llama-server (--jinja) to use tool calling with full CRUD capabilities.

**Setup**: llama-server with --jinja flag, OpenAI-compatible API at localhost

## Tasks Summary

- [x] Task 1: Add Qwen3.5 Parser Registration - DONE
- [x] Task 2: Handle llama-server Arguments-as-Object Bug - Already handled in run_agent.py
- [ ] Task 3: Verify Tool Execution Works with llama-server - Requires actual server
- [x] Task 4: Add Model Configuration - Already exists in aizen_cli/models.py
- [ ] Task 5: Add Tests

## Implementation Completed

### Task 1: Qwen3.5 Parser Registration
- Added `qwen3.5` as alias to `qwen3_coder` parser in `environments/tool_call_parsers/__init__.py`
- Fixed import path in `qwen_parser.py` (hermes_parser instead of non-existent aizen_parser)
- Verified: `get_parser('qwen3.5')` returns `Qwen3CoderToolCallParser`

### Task 2: Arguments-as-Object Handling
- Already implemented in run_agent.py lines 8496-8500
- Code converts dict/list arguments to JSON string before processing
- No additional changes needed

### Task 4: Model Configuration
- Qwen3.5 models already present in aizen_cli/models.py:
  - qwen/qwen3.5-plus-02-15
  - qwen/qwen3.5-35b-a3b
  - And more via OpenRouter

## Remaining Tasks

### Task 3: Full Integration Test
Requires running llama-server with Qwen3.5 model to test end-to-end tool calling.

### Task 5: Add Tests
Create tests/test_qwen35_tool_calling.py for parser and tool execution.

## Final Verification

1. Run test suite: `python -m pytest tests/ -q`
2. Test with actual llama-server + Qwen3.5
3. Verify tool calling end-to-end
4. Verify CRUD tools work
