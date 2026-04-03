# Task C-1: Print Statement Inventory Report

**Date**: 2026-04-02  
**Status**: COMPLETE

## Executive Summary

Found **4,064 print() statements** across 137 Python files in the Aizen codebase (excluding third-party libraries).

## Top 20 Files by Print Statement Density

| Rank | File | Print Statements | Category |
|------|------|------------------|----------|
| 1 | cli.py | 597 | CLI Interface |
| 2 | aizen_cli/main.py | 555 | CLI Main Entry |
| 3 | run_agent.py | 213 | Agent Core |
| 4 | aizen_cli/setup.py | 203 | Setup Wizard |
| 5 | aizen_cli/gateway.py | 179 | Gateway Service |
| 6 | aizen_cli/config.py | 142 | Configuration |
| 7 | aizen_cli/skills_hub.py | 111 | Skills System |
| 8 | aizen_cli/auth.py | 80 | Authentication |
| 9 | aizen_cli/tools_config.py | 78 | Tool Config |
| 10 | aizen_cli/status.py | 68 | Status Display |
| 11 | aizen_cli/doctor.py | 65 | Diagnostics |
| 12 | tests/integration/test_web_tools.py | 61 | Testing |
| 13 | aizen_cli/claw.py | 59 | Migration Tool |
| 14 | aizen_cli/uninstall.py | 57 | Uninstaller |
| 15 | tools/web_tools.py | 56 | Web Tools |
| 16 | aizen_cli/plugins_cmd.py | 55 | Plugin System |
| 17 | aizen_cli/cron.py | 52 | Scheduler |
| 18 | scripts/release.py | 51 | Release Script |
| 19 | tools/terminal_tool.py | 50 | Terminal Backend |
| 20 | scripts/sample_and_compress.py | 49 | Compression |

## Analysis

### High-Priority Files (CLI/User-Facing)
- **cli.py** (597): Main CLI interface - most critical for user experience
- **aizen_cli/main.py** (555): CLI entry points
- **aizen_cli/setup.py** (203): Setup wizard
- **aizen_cli/status.py** (68): Status display
- **aizen_cli/doctor.py** (65): Diagnostics

### Medium-Priority Files (Core Logic)
- **run_agent.py** (213): Agent core - logging critical for debugging
- **aizen_cli/gateway.py** (179): Gateway service
- **tools/terminal_tool.py** (50): Terminal execution

### Low-Priority Files (Utilities)
- Scripts (release.py, sample_and_compress.py)
- Test files (test_web_tools.py)

## Recommendations

### Immediate Action (Phase C - Partial)
Focus on converting print() to logging in:
1. **run_agent.py** (213 statements) - Critical for debugging
2. **gateway/run.py** - Service logging

### Gradual Migration Strategy
1. **New code**: Use logging.info() by default
2. **Bug fixes**: Convert print() to logging when fixing issues
3. **Refactoring**: Convert during modularization (Phase D)

### Logging Pattern
```python
import logging
logger = logging.getLogger(__name__)

# Replace:
print(f"Error: {e}")

# With:
logger.error(f"Error: {e}", exc_info=True)
```

## Estimated Effort

- **Full conversion**: 40-60 hours (4,064 statements)
- **Critical files only**: 8-12 hours (~1,000 statements in top 5 files)
- **Gradual migration**: Ongoing, part of other refactoring tasks

## Next Steps

1. **Task C-2**: Convert run_agent.py (213 statements) - HIGH PRIORITY
2. **Task C-3**: Convert cli.py (597 statements) - MEDIUM PRIORITY
3. **Future**: Add to code review guidelines - prefer logging over print

---

*Inventory completed by: Sisyphus Agent*  
*Total files: 137 | Total statements: 4,064*