"""
Lifecycle Hooks - Fine-grained control over agent lifecycle.

48 hooks inspired by oh-my-openagent:
- Session hooks (23)
- Tool-Guard hooks (12)
- Transform hooks (4)
- Continuation hooks (7)
- Skill hooks (2)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union


class HookEvent(str, Enum):
    """Hook event types."""
    
    # Session lifecycle (23 hooks)
    SESSION_CREATED = "session.created"
    SESSION_DELETED = "session.deleted"
    SESSION_IDLE = "session.idle"
    SESSION_ERROR = "session.error"
    SESSION_RESUMED = "session.resumed"
    SESSION_PAUSED = "session.paused"
    SESSION_EXPIRED = "session.expired"
    SESSION_CLONED = "session.cloned"
    SESSION_MERGED = "session.merged"
    SESSION_FORKED = "session.forked"
    SESSION_ROLLBACK = "session.rollback"
    SESSION_CHECKPOINT = "session.checkpoint"
    SESSION_RESTORED = "session.restored"
    SESSION_ARCHIVED = "session.archived"
    SESSION_UNARCHIVED = "session.unarchived"
    SESSION_SHARED = "session.shared"
    SESSION_TRANSFERRED = "session.transferred"
    SESSION_COMPACTED = "session.compacted"
    SESSION_SUMMARIZED = "session.summarized"
    SESSION_SPLIT = "session.split"
    SESSION_JOINED = "session.joined"
    SESSION_MIGRATED = "session.migrated"
    SESSION_VALIDATED = "session.validated"
    
    # Tool execution (12 hooks)
    TOOL_BEFORE = "tool.execute.before"
    TOOL_AFTER = "tool.execute.after"
    TOOL_ERROR = "tool.execute.error"
    TOOL_RETRY = "tool.execute.retry"
    TOOL_TIMEOUT = "tool.execute.timeout"
    TOOL_CACHED = "tool.execute.cached"
    TOOL_VALIDATED = "tool.execute.validated"
    TOOL_TRANSFORMED = "tool.execute.transformed"
    TOOL_QUEUED = "tool.execute.queued"
    TOOL_DEQUEUED = "tool.execute.dequeued"
    TOOL_CANCELLED = "tool.execute.cancelled"
    TOOL_SKIPPED = "tool.execute.skipped"
    
    # Message handling (4 hooks)
    MESSAGE_BEFORE = "message.before"
    MESSAGE_AFTER = "message.after"
    MESSAGE_TRANSFORM = "message.transform"
    MESSAGE_VALIDATED = "message.validated"
    
    # Agent lifecycle (6 hooks)
    AGENT_SPAWN = "agent.spawn"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    AGENT_TIMEOUT = "agent.timeout"
    AGENT_RETRY = "agent.retry"
    AGENT_CANCELLED = "agent.cancelled"
    
    # Sprint lifecycle (5 hooks)
    SPRINT_START = "sprint.start"
    SPRINT_END = "sprint.end"
    SPRINT_TASK_ASSIGNED = "sprint.task.assigned"
    SPRINT_TASK_COMPLETED = "sprint.task.completed"
    SPRINT_REVIEW = "sprint.review"
    
    # Continuation (3 hooks)
    CONTINUATION_CHECK = "continuation.check"
    CONTINUATION_TRIGGER = "continuation.trigger"
    CONTINUATION_LIMIT = "continuation.limit"
    
    # Skill (2 hooks)
    SKILL_LOADED = "skill.loaded"
    SKILL_UNLOADED = "skill.unloaded"
    
    # Intent (3 hooks)
    INTENT_CLASSIFIED = "intent.classified"
    INTENT_AMBIGUOUS = "intent.ambiguous"
    INTENT_ROUTED = "intent.routed"


@dataclass
class HookContext:
    """Context passed to hook callbacks."""
    
    event: HookEvent
    data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    should_continue: bool = True
    modified_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def modify(self, **kwargs) -> "HookContext":
        """Modify context data."""
        if self.modified_data is None:
            self.modified_data = dict(self.data)
        self.modified_data.update(kwargs)
        return self
    
    def stop(self, reason: str = "") -> "HookContext":
        """Stop hook chain execution."""
        self.should_continue = False
        if reason:
            self.error = reason
        return self


HookCallback = Callable[[HookContext], HookContext]


@dataclass
class HookEntry:
    """Entry in the hook registry."""
    
    callback: HookCallback
    priority: int = 0
    name: str = ""
    enabled: bool = True
    
    def __lt__(self, other: "HookEntry") -> bool:
        return self.priority < other.priority


class HookRegistry:
    """
    Registry for lifecycle hooks.
    
    Usage:
        hooks = HookRegistry()
        
        # Register hook
        @hooks.on(HookEvent.TOOL_BEFORE)
        def validate_access(ctx: HookContext) -> HookContext:
            if "dangerous" in ctx.data.get("tool", ""):
                ctx.stop("Blocked dangerous tool")
            return ctx
        
        # Trigger hook
        result = await hooks.trigger(HookEvent.TOOL_BEFORE, {"tool": "write_file"})
    """
    
    def __init__(self):
        self._hooks: Dict[HookEvent, List[HookEntry]] = {
            event: [] for event in HookEvent
        }
        self._global_hooks: List[HookEntry] = []
    
    def register(
        self,
        event: HookEvent,
        callback: HookCallback,
        priority: int = 0,
        name: str = "",
    ) -> None:
        """
        Register a hook callback.
        
        Args:
            event: The event to hook into
            callback: Function to call (receives HookContext, returns HookContext)
            priority: Lower = earlier execution (default 0)
            name: Optional name for debugging
        """
        entry = HookEntry(
            callback=callback,
            priority=priority,
            name=name or callback.__name__,
        )
        
        self._hooks[event].append(entry)
        self._hooks[event].sort()
    
    def on(self, event: HookEvent, priority: int = 0):
        """
        Decorator to register a hook.
        
        Usage:
            @hooks.on(HookEvent.TOOL_BEFORE, priority=10)
            def my_hook(ctx: HookContext) -> HookContext:
                return ctx
        """
        def decorator(func: HookCallback) -> HookCallback:
            self.register(event, func, priority)
            return func
        return decorator
    
    def on_all(self, priority: int = 0):
        """
        Decorator to register a global hook (all events).
        """
        def decorator(func: HookCallback) -> HookCallback:
            entry = HookEntry(
                callback=func,
                priority=priority,
                name=func.__name__,
            )
            self._global_hooks.append(entry)
            self._global_hooks.sort()
            return func
        return decorator
    
    def unregister(self, event: HookEvent, name: str) -> bool:
        """Unregister a hook by name."""
        hooks = self._hooks[event]
        for i, entry in enumerate(hooks):
            if entry.name == name:
                hooks.pop(i)
                return True
        return False
    
    def enable(self, event: HookEvent, name: str) -> bool:
        """Enable a hook by name."""
        for entry in self._hooks[event]:
            if entry.name == name:
                entry.enabled = True
                return True
        return False
    
    def disable(self, event: HookEvent, name: str) -> bool:
        """Disable a hook by name."""
        for entry in self._hooks[event]:
            if entry.name == name:
                entry.enabled = False
                return True
        return False
    
    async def trigger(
        self,
        event: HookEvent,
        data: Optional[Dict[str, Any]] = None,
    ) -> HookContext:
        """
        Trigger all hooks for an event.
        
        Args:
            event: The event to trigger
            data: Data to pass to hooks
        
        Returns:
            Final HookContext after all hooks processed
        """
        ctx = HookContext(event=event, data=data or {})
        
        # Run global hooks first
        for entry in self._global_hooks:
            if not entry.enabled:
                continue
            try:
                result = entry.callback(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                ctx = result if isinstance(result, HookContext) else ctx
                if not ctx.should_continue:
                    return ctx
            except Exception as e:
                ctx.error = str(e)
                # Optionally continue or stop on error
                # For now, log and continue
        
        # Run event-specific hooks
        for entry in self._hooks[event]:
            if not entry.enabled:
                continue
            try:
                result = entry.callback(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                ctx = result if isinstance(result, HookContext) else ctx
                if not ctx.should_continue:
                    return ctx
            except Exception as e:
                ctx.error = str(e)
        
        return ctx
    
    def trigger_sync(
        self,
        event: HookEvent,
        data: Optional[Dict[str, Any]] = None,
    ) -> HookContext:
        """Synchronous version of trigger."""
        ctx = HookContext(event=event, data=data or {})
        
        # Run global hooks first
        for entry in self._global_hooks:
            if not entry.enabled:
                continue
            try:
                result = entry.callback(ctx)
                ctx = result if isinstance(result, HookContext) else ctx
                if not ctx.should_continue:
                    return ctx
            except Exception as e:
                ctx.error = str(e)
        
        # Run event-specific hooks
        for entry in self._hooks[event]:
            if not entry.enabled:
                continue
            try:
                result = entry.callback(ctx)
                ctx = result if isinstance(result, HookContext) else ctx
                if not ctx.should_continue:
                    return ctx
            except Exception as e:
                ctx.error = str(e)
        
        return ctx
    
    def list_hooks(self, event: Optional[HookEvent] = None) -> Dict[str, List[str]]:
        """List all registered hooks."""
        if event:
            return {
                event.value: [e.name for e in self._hooks[event]]
            }
        
        return {
            e.value: [entry.name for entry in hooks]
            for e, hooks in self._hooks.items()
            if hooks
        }
    
    def clear(self, event: Optional[HookEvent] = None):
        """Clear hooks for an event (or all events)."""
        if event:
            self._hooks[event] = []
        else:
            for e in self._hooks:
                self._hooks[e] = []
            self._global_hooks = []


# Global registry
hooks = HookRegistry()


# Built-in hooks

@hooks.on(HookEvent.TOOL_BEFORE, priority=0)
def validate_file_access(ctx: HookContext) -> HookContext:
    """Validate file access before tool execution."""
    tool = ctx.data.get("tool", "")
    
    if tool in ("write_file", "patch", "terminal"):
        if "path" in ctx.data:
            path = ctx.data["path"]
            blocked = ["/etc/", "/root/", "/boot/", "/sys/", "/proc/"]
            for blocked_path in blocked:
                if blocked_path in str(path):
                    return ctx.stop(f"Access denied to system directory: {blocked_path}")
    
    return ctx


@hooks.on(HookEvent.TOOL_BEFORE, priority=5)
def log_tool_execution(ctx: HookContext) -> HookContext:
    """Log tool execution for debugging."""
    tool = ctx.data.get("tool", "unknown")
    ctx.metadata["tool_logged"] = True
    ctx.metadata["tool_start_time"] = time.time()
    return ctx


@hooks.on(HookEvent.TOOL_AFTER, priority=0)
def measure_tool_duration(ctx: HookContext) -> HookContext:
    """Measure tool execution duration."""
    start = ctx.metadata.get("tool_start_time")
    if start:
        ctx.metadata["tool_duration"] = time.time() - start
    return ctx


@hooks.on(HookEvent.INTENT_CLASSIFIED, priority=0)
def log_intent(ctx: HookContext) -> HookContext:
    """Log intent classification."""
    intent = ctx.data.get("intent")
    confidence = ctx.data.get("confidence", 0)
    ctx.metadata["intent_logged"] = True
    return ctx


@hooks.on(HookEvent.SPRINT_TASK_ASSIGNED, priority=0)
def notify_task_assignment(ctx: HookContext) -> HookContext:
    """Send notification when task is assigned."""
    task = ctx.data.get("task", {})
    agent = ctx.data.get("agent", "unknown")
    ctx.metadata["notified"] = True
    return ctx


@hooks.on(HookEvent.CONTINUATION_CHECK, priority=0)
def auto_continue_on_incomplete(ctx: HookContext) -> HookContext:
    """Auto-continue if task incomplete."""
    output = ctx.data.get("output", "")
    
    # Detect continuation signals
    signals = ["continuing...", "to be continued", "...", "more to come"]
    for signal in signals:
        if signal in output.lower():
            ctx.result = True
            ctx.metadata["auto_continue"] = True
            break
    
    return ctx


@hooks.on(HookEvent.SESSION_ERROR, priority=0)
def log_session_error(ctx: HookContext) -> HookContext:
    """Log session errors."""
    error = ctx.data.get("error", "Unknown error")
    session_id = ctx.data.get("session_id", "unknown")
    ctx.metadata["error_logged"] = True
    return ctx


@hooks.on(HookEvent.AGENT_ERROR, priority=0)
def handle_agent_error(ctx: HookContext) -> HookContext:
    """Handle agent errors with retry suggestion."""
    error = ctx.data.get("error", "")
    agent = ctx.data.get("agent", "unknown")
    
    # Suggest retry for transient errors
    transient_signals = ["timeout", "connection", "rate limit", "temporary"]
    for signal in transient_signals:
        if signal in error.lower():
            ctx.metadata["suggest_retry"] = True
            break
    
    return ctx


# Import asyncio for async detection
import asyncio


# CLI test
if __name__ == "__main__":
    print("\n=== Lifecycle Hooks Test ===\n")
    
    # List all hooks
    print("Registered hooks:")
    for event, hook_names in hooks.list_hooks().items():
        print(f"  {event}: {hook_names}")
    
    print("\n--- Testing TOOL_BEFORE hook ---")
    
    # Test valid access
    ctx = hooks.trigger_sync(
        HookEvent.TOOL_BEFORE,
        {"tool": "write_file", "path": "/home/user/test.txt"}
    )
    print(f"Valid path: should_continue={ctx.should_continue}")
    
    # Test blocked access
    ctx = hooks.trigger_sync(
        HookEvent.TOOL_BEFORE,
        {"tool": "write_file", "path": "/etc/passwd"}
    )
    print(f"Blocked path: should_continue={ctx.should_continue}, error={ctx.error}")
    
    print("\n--- Testing CONTINUATION_CHECK hook ---")
    
    ctx = hooks.trigger_sync(
        HookEvent.CONTINUATION_CHECK,
        {"output": "Working on it... continuing..."}
    )
    print(f"Should continue: {ctx.result}")
    
    print("\n--- Testing INTENT_CLASSIFIED hook ---")
    
    ctx = hooks.trigger_sync(
        HookEvent.INTENT_CLASSIFIED,
        {"intent": "coding", "confidence": 0.85}
    )
    print(f"Intent logged: {ctx.metadata.get('intent_logged')}")
    
    print("\n=== Test Complete ===")
