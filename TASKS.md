# Aizen Development Tasks - Catching Up to Aigo

> Last Updated: 2026-04-04
> Status: In Progress

---

## Overview

This document outlines the task list for enhancing Aizen to match and exceed the Aigo architecture. Aizen already has several competitive advantages (distillation pipeline, skills system, gateway adapters), but there are critical missing features that need implementation.

---

## Executive Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Tools** | ✅ Complete | 35+ native tools |
| **Distillation Pipeline** | ✅ Complete | 70-90% token reduction |
| **Skills System** | ✅ Complete | 100+ built-in skills |
| **Gateway Adapters** | ✅ Complete | 6 platforms |
| **Doom Loop Detection** | ✅ Complete | HIGH priority |
| **L0/L1/L2 Context** | ❌ Not Started | HIGH priority |
| **Vector DB** | ❌ Not Started | HIGH priority |
| **Permission System** | ✅ Complete | HIGH priority |
| **Self-Healing** | ❌ Not Started | HIGH priority |

---

## Phase 1: Critical Missing Features (HIGH Priority)

### Task 1.1: Doom Loop Detection

**Priority**: HIGH  
**Complexity**: Medium  
**Effort**: 2-3 days

**Description**:  
Detect when the agent repeatedly calls the same tool with the same arguments, causing an infinite loop. Break the loop and notify the user.

**Implementation**:
- Track last N tool calls (configurable, default 5)
- Hash tool name + arguments to detect identical sequences
- If same call detected 3+ times, break and notify
- Implement exponential backoff for retries

**Files to Modify**:
- `run_agent.py` - Add detection logic in main loop
- `tools/model_tools.py` - Add tracking

**Acceptance Criteria**:
- [ ] Detects repeated tool calls within 3 iterations
- [ ] Breaks loop and notifies user
- [ ] Logs warning for debugging
- [ ] Configurable threshold

---

### Task 1.2: L0/L1/L2 Context Engine

**Priority**: HIGH  
**Complexity**: High  
**Effort**: 5-7 days

**Description**:  
Implement hierarchical context management with proper token budgeting across three levels.

**Context Levels**:
- **L0** (Hot): System prompt, current task, recent tool results
- **L1** (Warm): Session conversation history
- **L2** (Cold): Historical summaries, learned patterns

**Implementation**:
- Create `src/agent/context_engine.py`
- Implement token budget tracking per level
- Add auto-compaction triggers when approaching limits
- Connect with distillation pipeline for compression

**Files to Create**:
- `src/agent/context_engine.py`

**Files to Modify**:
- `run_agent.py` - Integrate context engine
- `agent/context_compressor.py` - Connect with pipeline

**Acceptance Criteria**:
- [ ] Three-tier context structure
- [ ] Token budget tracking per level
- [ ] Auto-compaction at 50% threshold
- [ ] Distillation integration

---

### Task 1.3: Vector DB Integration

**Priority**: HIGH  
**Complexity**: Medium  
**Effort**: 3-5 days

**Description**:  
Integrate ChromaDB for semantic memory search, enabling context-aware responses based on past conversations.

**Implementation**:
- Add chromadb dependency
- Create `src/agent/vector_memory.py`
- Implement memory embedding generation
- Add semantic search API
- CRUD operations for memories

**Files to Create**:
- `src/agent/vector_memory.py`

**Dependencies**:
```bash
pip install chromadb
```

**Acceptance Criteria**:
- [ ] Chroma client integration
- [ ] Memory embedding generation
- [ ] Semantic search functionality
- [ ] CRUD API for memories

---

### Task 1.4: Permission System

**Priority**: HIGH  
**Complexity**: Low  
**Effort**: 1-2 days

**Description**:  
Implement ruleset-based permission system with allow/deny/ask modes per tool.

**Implementation**:
- Create `src/agent/permissions.py`
- Define permission config in config.yaml
- Support wildcard patterns (e.g., `web*` matches webfetch, websearch)
- Three modes: allow, ask, deny
- Callback for user confirmation on "ask" mode

**Files to Create**:
- `src/agent/permissions.py`

**Files to Modify**:
- `aizen_cli/config.py` - Add permission config
- `tools/registry.py` - Integrate permission checks

**Config Example**:
```yaml
permissions:
  terminal:
    mode: ask
  web*:
    mode: allow
  write_file:
    mode: ask
  dangerous_command:
    mode: deny
```

**Acceptance Criteria**:
- [ ] Wildcard pattern matching
- [ ] Three permission modes
- [ ] User confirmation callback
- [ ] Configurable via YAML

---

## Phase 2: Self-Healing (HIGH Priority)

### Task 2.1: Self-Healing Execution

**Priority**: HIGH  
**Complexity**: High  
**Effort**: 5-7 days

**Description**:  
Auto-detect tool execution failures, analyze tracebacks, and retry with modified approach.

**Implementation**:
- Detect tool execution failures
- Parse error messages/tracebacks
- Identify fix strategy based on error type
- Retry with exponential backoff
- Maximum 3 retry attempts per tool

**Error Categories**:
- Syntax Error → Fix and retry
- Import Error → Auto pip-install and retry
- Permission Error → Skip or ask
- API Rate Limit → Backoff and retry
- Unknown → Log and continue

**Files to Modify**:
- `run_agent.py` - Add retry logic
- `tools/model_tools.py` - Add error handling

**Acceptance Criteria**:
- [ ] Detects 5+ error categories
- [ ] Automatic retry with fixes
- [ ] User notification on repeated failures
- [ ] Logging of all repair attempts

---

### Task 2.2: Auto Pip-Install

**Priority**: MEDIUM  
**Complexity**: Low  
**Effort**: 1-2 days

**Description**:  
Detect missing Python packages and automatically install them.

**Implementation**:
- Parse ImportError from code execution output
- Extract package name from error message
- Run pip install in background
- Retry execution after install

**Files to Modify**:
- `tools/code_execution_tool.py`

**Acceptance Criteria**:
- [ ] Parses ImportError messages
- [ ] Extracts package names
- [ ] Auto-installs missing packages
- [ ] Retries execution after install

---

### Task 2.3: Bughunter Command

**Priority**: MEDIUM  
**Complexity**: Medium  
**Effort**: 3-5 days

**Description**:  
Automated bug detection and fixing through test running and failure analysis.

**Implementation**:
- Run tests on code changes
- Detect test failures
- Analyze failure patterns
- Auto-generate fixes
- Create `tools/bughunter.py`

**Files to Create**:
- `tools/bughunter.py`

**Features**:
- Test discovery and execution
- Failure pattern detection
- Auto-fix suggestions
- Manual review workflow

**Acceptance Criteria**:
- [ ] Test discovery
- [ ] Failure detection
- [ ] Pattern analysis
- [ ] Auto-fix generation

---

## Phase 3: Memory & Learning (MEDIUM Priority)

### Task 3.1: Task Extraction Agent

**Priority**: MEDIUM  
**Complexity**: Medium  
**Effort**: 3-4 days

**Description**:  
Automatically extract tasks from conversation history and track their status.

**Implementation**:
- Analyze conversation for task intents
- Extract task details (title, steps, status)
- Store in task database
- Track pending, running, success, failed states

**Files to Create**:
- `src/agent/task_extractor.py`

**Acceptance Criteria**:
- [ ] Intent detection from messages
- [ ] Task extraction
- [ ] Status tracking
- [ ] Database persistence

---

### Task 3.2: Skill Memory Layer

**Priority**: MEDIUM  
**Complexity**: Medium  
**Effort**: 4-5 days

**Description**:  
Learning layer that stores and recalls skills based on successful task patterns.

**Implementation**:
- Detect successful task patterns
- Extract as skill YAML
- Store in skill memory
- Recall for similar tasks
- Two-phase learning: Distillation → Skill Agent

**Files to Create**:
- `src/agent/skill_memory.py`

**Acceptance Criteria**:
- [ ] Pattern detection
- [ ] Skill extraction
- [ ] Memory storage
- [ ] Pattern recall

---

### Task 3.3: Wisdom Accumulation

**Priority**: MEDIUM  
**Complexity**: Medium  
**Effort**: 3-4 days

**Description**:  
Extract and store lessons learned from completed tasks, inject into future contexts.

**Implementation**:
- Extract lessons from completed tasks
- Categorize by task type
- Store in wisdom database
- Inject relevant wisdom into context

**Files to Create**:
- `src/agent/wisdom.py`

**Acceptance Criteria**:
- [ ] Lesson extraction
- [ ] Categorization
- [ ] Storage
- [ ] Context injection

---

## Phase 4: Advanced Features (MEDIUM Priority)

### Task 4.1: Planning Agents

**Priority**: MEDIUM  
**Complexity**: High  
**Effort**: 7-10 days

**Description**:  
Implement OMO-style planning agents: Prometheus (planner), Metis (gap analyzer), Momus (reviewer).

**Implementation**:
- **Prometheus**: Break down tasks into actionable steps
- **Metis**: Identify missing information and gaps
- **Momus**: Review plans and suggest improvements

**Files to Create**:
- `src/agent/planning/__init__.py`
- `src/agent/planning/prometheus.py`
- `src/agent/planning/metis.py`
- `src/agent/planning/momus.py`

**Acceptance Criteria**:
- [ ] Task breakdown
- [ ] Gap identification
- [ ] Plan review
- [ ] Iteration support

---

### Task 4.2: Hash-Anchored Edits

**Priority**: MEDIUM  
**Complexity**: Medium  
**Effort**: 2-3 days

**Description**:  
Line#ID hash validation for edit reliability, solving the "harness problem" (6.7% → 68.3% success rate improvement).

**Implementation**:
- Generate hash for edit target content
- Verify before applying edit
- Retry with re-read if hash mismatch
- Track edit attempts and success rate

**Files to Modify**:
- `tools/file_tools.py`

**Acceptance Criteria**:
- [ ] Hash generation
- [ ] Pre-edit verification
- [ ] Retry mechanism
- [ ] Success tracking

---

### Task 4.3: Workspace Presets

**Priority**: LOW  
**Complexity**: Medium  
**Effort**: 3-4 days

**Description**:  
Workspace profiles and session templates for quick project setup.

**Implementation**:
- Workspace config in config.yaml
- Session templates
- Profile switching
- Preset management

**Files to Modify**:
- `aizen_cli/config.py`
- `cli.py`

**Acceptance Criteria**:
- [ ] Profile creation
- [ ] Profile switching
- [ ] Template support
- [ ] Config persistence

---

### Task 4.4: Scheduled Jobs

**Priority**: LOW  
**Complexity**: Low  
**Effort**: 2-3 days

**Description**:  
Cron-like task scheduling for background automation.

**Implementation**:
- Cron expression parsing
- Job persistence in SQLite
- Background scheduler
- Notification on completion

**Files to Create/Modify**:
- `cron/scheduler.py` (expand existing stub)

**Acceptance Criteria**:
- [ ] Cron parsing
- [ ] Job persistence
- [ ] Background execution
- [ ] Notifications

---

## Phase 5: Kanban & Issues (LOW Priority)

### Task 5.1: Issue/Kanban System

**Priority**: LOW  
**Complexity**: Medium  
**Effort**: 5-7 days

**Description**:  
Issue management with status workflow, similar to GitHub Issues.

**Implementation**:
- Issue model (title, description, status, priority, tags)
- Status workflow (TODO, IN_PROGRESS, DONE, BLOCKED)
- Sub-issues (parent/child relationships)
- MCP tools for issue CRUD

**Files to Create**:
- `src/agent/kanban.py`

**Acceptance Criteria**:
- [ ] Issue CRUD
- [ ] Status workflow
- [ ] Filtering/sorting
- [ ] MCP tools

---

## Implementation Order

### Quick Wins (Start Here)
1. **Permission System** - 1-2 days, Low complexity
2. **Auto Pip-Install** - 1-2 days, Low complexity
3. **Doom Loop Detection** - 2-3 days, Medium complexity

### Core Features
4. **Self-Healing** - 5-7 days, High complexity
5. **L0/L1/L2 Context** - 5-7 days, High complexity
6. **Vector DB** - 3-5 days, Medium complexity

### Advanced Features
7. **Bughunter** - 3-5 days, Medium complexity
8. **Planning Agents** - 7-10 days, High complexity
9. **Wisdom Accumulation** - 3-4 days, Medium complexity

---

## Dependencies

```bash
# Core dependencies
pip install chromadb

# Optional
pip install qdrant-client  # Alternative vector DB
pip install schedule       # For cron jobs
```

---

## Testing Checklist

### Phase 1 Tests
- [ ] Doom loop detection triggers at 3 repeated calls
- [ ] Context engine tracks tokens correctly
- [ ] Vector DB stores and retrieves memories
- [ ] Permission system blocks denied tools

### Phase 2 Tests
- [ ] Self-healing recovers from syntax errors
- [ ] Auto pip-install works for missing packages
- [ ] Bughunter detects test failures

### Phase 3 Tests
- [ ] Task extraction identifies task intents
- [ ] Skill memory stores and recalls patterns
- [ ] Wisdom injects lessons into context

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Token Efficiency | 70% | 90% |
| Doom Loop Prevention | 0% | 100% |
| Context Engine | Basic | L0/L1/L2 |
| Vector Memory | No | Yes |
| Permission System | No | Yes |
| Self-Healing | No | Yes |
| Bughunter | No | Yes |
| Skills | 100+ | 150+ |
| Gateway Platforms | 6 | 8 |

---

## Notes

- Aizen already has **distillation pipeline** - this is a major competitive advantage over Aigo
- Aizen has **100+ skills** - Aigo only has 12 basic tools
- Focus on **token efficiency** and **self-healing** to differentiate from Aigo
- Use **Python ecosystem** to outpace Go-based Aigo

---

## References

- `docs_reference/architecture.md` - Aigo architecture reference
- `docs_reference/ROADMAP.md` - Aigo roadmap
- `docs_reference/tools.md` - Aigo tools reference
- `COMPARISON_AIZEN_VS_AIGO.md` - Detailed comparison
- `TASKS_AIZEN_VS_AIGO.md` - Task list (alternative format)
