"""
Aizen Lifecycle Module - Agent lifecycle and background execution.

This module provides:
- BackgroundAgentPool: Parallel agent execution
- ParallelAgentPool: Enhanced pool with priorities and dependencies
- HookRegistry: 48 lifecycle hooks for fine-grained control

Example:
    >>> from lifecycle import BackgroundAgentPool, hooks, HookEvent
    >>> 
    >>> # Spawn parallel agents
    >>> pool = BackgroundAgentPool()
    >>> task_ids = await pool.spawn_parallel([
    ...     {"agent": "Dev", "prompt": "Implement feature"},
    ...     {"agent": "QA", "prompt": "Write tests"},
    ... ])
    >>> 
    >>> # Register a hook
    >>> @hooks.on(HookEvent.TOOL_BEFORE)
    ... def validate(ctx):
    ...     if "dangerous" in ctx.data.get("tool", ""):
    ...         ctx.stop("Blocked")
    ...     return ctx
"""

from .background_agents import BackgroundAgentPool, BackgroundResult, AgentTask
from .parallel_pool import ParallelAgentPool, TaskPriority, TaskStatus
from .hooks import HookRegistry, HookEvent, HookContext, hooks

__all__ = [
    # Background Agents
    "BackgroundAgentPool",
    "BackgroundResult", 
    "AgentTask",
    
    # Parallel Pool
    "ParallelAgentPool",
    "TaskPriority",
    "TaskStatus",
    
    # Hooks
    "HookRegistry",
    "HookEvent",
    "HookContext",
    "hooks",
]
__version__ = "3.0.0"
