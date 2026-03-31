# Lifecycle Hooks - Hermes v3.0

48 hooks for fine-grained control over agent lifecycle.

---

## Hook Events

### Session Lifecycle (23 hooks)

| Event | Description |
|-------|-------------|
| `session.created` | New session created |
| `session.deleted` | Session deleted |
| `session.idle` | Session idle timeout |
| `session.error` | Session error occurred |
| `session.resumed` | Session resumed |
| `session.paused` | Session paused |
| `session.expired` | Session expired |
| `session.cloned` | Session cloned |
| `session.merged` | Sessions merged |
| `session.forked` | Session forked |
| `session.rollback` | Session rolled back |
| `session.checkpoint` | Checkpoint created |
| `session.restored` | Session restored |
| `session.archived` | Session archived |
| `session.unarchived` | Session unarchived |
| `session.shared` | Session shared |
| `session.transferred` | Session transferred |
| `session.compacted` | Context compacted |
| `session.summarized` | Session summarized |
| `session.split` | Session split |
| `session.joined` | Sessions joined |
| `session.migrated` | Session migrated |
| `session.validated` | Session validated |

---

### Tool Execution (12 hooks)

| Event | Description |
|-------|-------------|
| `tool.execute.before` | Before tool execution |
| `tool.execute.after` | After tool execution |
| `tool.execute.error` | Tool execution error |
| `tool.execute.retry` | Tool retry |
| `tool.execute.timeout` | Tool timeout |
| `tool.execute.cached` | Cached result used |
| `tool.execute.validated` | Tool input validated |
| `tool.execute.transformed` | Tool output transformed |
| `tool.execute.queued` | Tool queued |
| `tool.execute.dequeued` | Tool dequeued |
| `tool.execute.cancelled` | Tool cancelled |
| `tool.execute.skipped` | Tool skipped |

---

### Message Handling (4 hooks)

| Event | Description |
|-------|-------------|
| `message.before` | Before message processing |
| `message.after` | After message processing |
| `message.transform` | Message transformation |
| `message.validated` | Message validated |

---

### Agent Lifecycle (6 hooks)

| Event | Description |
|-------|-------------|
| `agent.spawn` | Agent spawned |
| `agent.complete` | Agent completed |
| `agent.error` | Agent error |
| `agent.timeout` | Agent timeout |
| `agent.retry` | Agent retry |
| `agent.cancelled` | Agent cancelled |

---

### Sprint Lifecycle (5 hooks)

| Event | Description |
|-------|-------------|
| `sprint.start` | Sprint started |
| `sprint.end` | Sprint ended |
| `sprint.task.assigned` | Task assigned to agent |
| `sprint.task.completed` | Task completed |
| `sprint.review` | Sprint review |

---

### Continuation (3 hooks)

| Event | Description |
|-------|-------------|
| `continuation.check` | Check if should continue |
| `continuation.trigger` | Trigger continuation |
| `continuation.limit` | Continuation limit reached |

---

### Skill (2 hooks)

| Event | Description |
|-------|-------------|
| `skill.loaded` | Skill loaded |
| `skill.unloaded` | Skill unloaded |

---

### Intent (3 hooks)

| Event | Description |
|-------|-------------|
| `intent.classified` | Intent classified |
| `intent.ambiguous` | Ambiguous intent |
| `intent.routed` | Intent routed to agent |

---

## Usage

### Register a Hook

```python
from lifecycle import hooks, HookEvent

@hooks.on(HookEvent.TOOL_BEFORE)
def validate_file_access(ctx: HookContext) -> HookContext:
    """Block access to system directories."""
    tool = ctx.data.get("tool", "")
    
    if tool in ("write_file", "patch", "terminal"):
        path = ctx.data.get("path", "")
        blocked = ["/etc/", "/root/", "/boot/"]
        
        for blocked_path in blocked:
            if blocked_path in str(path):
                ctx.should_continue = False
                ctx.error = f"Access denied: {blocked_path}"
                break
    
    return ctx
```

### Register with Priority

```python
# Higher priority = runs first
@hooks.on(HookEvent.TOOL_BEFORE, priority=10)
def first_hook(ctx):
    return ctx

@hooks.on(HookEvent.TOOL_BEFORE, priority=5)
def second_hook(ctx):
    return ctx
```

### Global Hook (All Events)

```python
@hooks.on_all()
def log_all_events(ctx: HookContext):
    print(f"Event: {ctx.event.value}")
    return ctx
```

### Trigger Hooks

```python
# Async
ctx = await hooks.trigger(
    HookEvent.TOOL_BEFORE,
    {"tool": "write_file", "path": "/tmp/test.txt"}
)

# Sync
ctx = hooks.trigger_sync(
    HookEvent.TOOL_BEFORE,
    {"tool": "write_file", "path": "/tmp/test.txt"}
)
```

---

## HookContext

```python
@dataclass
class HookContext:
    event: HookEvent              # The event type
    data: Dict[str, Any]          # Event data
    result: Optional[Any]         # Result to set
    error: Optional[str]          # Error message
    should_continue: bool = True  # Stop chain if False
    modified_data: Optional[Dict] # Modified data
    metadata: Dict[str, Any]      # Additional metadata
    timestamp: float              # Event timestamp
```

### Methods

```python
# Modify data
ctx.modify(key="value")

# Stop chain
ctx.stop("Reason")

# Check if should continue
if ctx.should_continue:
    # continue...
```

---

## Built-in Hooks

Hermes includes these pre-registered hooks:

| Hook | Event | Purpose |
|------|-------|---------|
| `validate_file_access` | `tool.execute.before` | Block system directory access |
| `log_tool_execution` | `tool.execute.before` | Log tool calls |
| `measure_tool_duration` | `tool.execute.after` | Track execution time |
| `auto_continue_on_incomplete` | `continuation.check` | Auto-detect continuation |
| `log_session_error` | `session.error` | Log session errors |
| `handle_agent_error` | `agent.error` | Retry suggestions |
| `log_intent` | `intent.classified` | Log intent classification |
| `notify_task_assignment` | `sprint.task.assigned` | Send notifications |

---

## Unregister Hooks

```python
# Disable by name
hooks.disable(HookEvent.TOOL_BEFORE, "validate_file_access")

# Enable again
hooks.enable(HookEvent.TOOL_BEFORE, "validate_file_access")

# Remove completely
hooks.unregister(HookEvent.TOOL_BEFORE, "validate_file_access")
```

---

## List Hooks

```python
# All hooks
all_hooks = hooks.list_hooks()

# Specific event
event_hooks = hooks.list_hooks(HookEvent.TOOL_BEFORE)
```

---

## Clear Hooks

```python
# Clear specific event
hooks.clear(HookEvent.TOOL_BEFORE)

# Clear all
hooks.clear()
```
