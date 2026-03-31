"""
Parallel Agent Pool - Enhanced version for 5+ concurrent agents.

Extends BackgroundAgentPool with:
- Priority queues
- Resource limits
- Task dependencies
- Progress tracking
- Result aggregation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor
import multiprocessing


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class TaskStatus(str, Enum):
    """Task status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class AgentTaskSpec:
    """Specification for an agent task."""
    
    id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    agent: str = ""
    prompt: str = ""
    skill: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300
    max_retries: int = 1
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def duration(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        if self.started_at:
            return time.time() - self.started_at
        return 0.0


@dataclass
class PoolStats:
    """Statistics for the agent pool."""
    
    total_tasks: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    
    total_duration: float = 0.0
    avg_duration: float = 0.0
    
    max_concurrent: int = 5
    current_concurrent: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "pending": self.pending,
            "running": self.running,
            "completed": self.completed,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "avg_duration": round(self.avg_duration, 3),
            "current_concurrent": self.current_concurrent,
            "max_concurrent": self.max_concurrent,
        }


@dataclass
class AggregatedResult:
    """Aggregated result from multiple agents."""
    
    success: bool
    total_tasks: int
    successful: int
    failed: int
    duration: float
    results: Dict[str, Any]
    errors: Dict[str, str]
    
    def summary(self) -> str:
        return (
            f"Completed: {self.successful}/{self.total_tasks} | "
            f"Duration: {self.duration:.2f}s | "
            f"Success: {self.success}"
        )


class ParallelAgentPool:
    """
    Enhanced parallel agent pool for 5+ concurrent agents.
    
    Features:
    - Priority queue (high priority tasks first)
    - Resource limits (max concurrent agents)
    - Task dependencies (task B waits for task A)
    - Progress tracking (callbacks for status updates)
    - Result aggregation (combine results from multiple agents)
    - Retry logic (retry failed tasks up to N times)
    
    Usage:
        pool = ParallelAgentPool(max_concurrent=5)
        
        # Submit tasks
        pool.submit("Dev", "Implement auth", priority=TaskPriority.HIGH)
        pool.submit("QA", "Test auth", depends_on=["task_abc123"])
        
        # Execute all
        result = await pool.execute_all()
        print(result.summary())
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: int = 300,
        executor: Optional[ThreadPoolExecutor] = None,
    ):
        self.max_concurrent = min(max_concurrent, multiprocessing.cpu_count() * 2)
        self.default_timeout = default_timeout
        
        # Task storage
        self.tasks: Dict[str, AgentTaskSpec] = {}
        self.pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # State tracking
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Callbacks
        self._progress_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []
        
        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Stats
        self._stats = PoolStats(max_concurrent=self.max_concurrent)
        
        # Executor for CPU-bound work
        self._executor = executor
    
    def submit(
        self,
        agent: str,
        prompt: str,
        skill: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        depends_on: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Submit a new task to the pool.
        
        Args:
            agent: Agent name (Dev, QA, Sec, etc.)
            prompt: Task prompt/instruction
            skill: Optional skill to load
            priority: Task priority (higher = more important)
            depends_on: List of task IDs that must complete first
            timeout: Timeout in seconds
            metadata: Additional metadata
        
        Returns:
            Task ID
        """
        task = AgentTaskSpec(
            agent=agent,
            prompt=prompt,
            skill=skill,
            priority=priority,
            dependencies=depends_on or [],
            timeout=timeout or self.default_timeout,
            metadata=metadata or {},
        )
        
        self.tasks[task.id] = task
        self._stats.total_tasks += 1
        self._stats.pending += 1
        
        # Add to queue with priority (negative for descending order)
        # Format: (-priority, submit_time, task_id)
        self.pending_queue.put_nowait((
            -priority.value,
            time.time(),
            task.id,
        ))
        
        return task.id
    
    def on_progress(self, callback: Callable):
        """Register a progress callback."""
        self._progress_callbacks.append(callback)
    
    def on_completion(self, callback: Callable):
        """Register a completion callback."""
        self._completion_callbacks.append(callback)
    
    async def _notify_progress(self, task: AgentTaskSpec):
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                result = callback(task)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
    
    def _can_run(self, task: AgentTaskSpec) -> bool:
        """Check if task can run (dependencies satisfied)."""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True
    
    async def _execute_task(self, task: AgentTaskSpec) -> AgentTaskSpec:
        """Execute a single task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self.running_tasks.add(task.id)
            self._stats.running += 1
            self._stats.pending -= 1
            self._stats.current_concurrent = len(self.running_tasks)
            
            await self._notify_progress(task)
            
            try:
                # Simulate task execution (in production, call actual agent)
                # This is where we'd spawn the actual agent process
                result = await asyncio.wait_for(
                    self._run_agent(task),
                    timeout=task.timeout,
                )
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                
                self.completed_tasks.add(task.id)
                self._stats.completed += 1
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"Task timed out after {task.timeout}s"
                task.completed_at = time.time()
                
                self.failed_tasks.add(task.id)
                self._stats.failed += 1
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = time.time()
                
                # Retry logic
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    self.pending_queue.put_nowait((
                        -task.priority.value,
                        time.time(),
                        task.id,
                    ))
                else:
                    self.failed_tasks.add(task.id)
                    self._stats.failed += 1
            
            finally:
                self.running_tasks.discard(task.id)
                self._stats.running -= 1
                self._stats.current_concurrent = len(self.running_tasks)
                
                if task.duration() > 0:
                    self._stats.total_duration += task.duration()
                    completed_count = self._stats.completed + self._stats.failed
                    if completed_count > 0:
                        self._stats.avg_duration = (
                            self._stats.total_duration / completed_count
                        )
                
                await self._notify_progress(task)
        
        return task
    
    async def _run_agent(self, task: AgentTaskSpec) -> str:
        """Run the actual agent (placeholder for implementation)."""
        # In production, this would:
        # 1. Spawn a subprocess with hermes CLI
        # 2. Pass the prompt and skill
        # 3. Collect the output
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        # Return mock result
        return f"[{task.agent}] Completed: {task.prompt[:50]}..."
    
    async def execute_all(self) -> AggregatedResult:
        """
        Execute all pending tasks and return aggregated result.
        
        Returns:
            AggregatedResult with all task outcomes
        """
        start_time = time.time()
        results = {}
        errors = {}
        
        running_futures = []
        
        while True:
            # Get tasks from queue
            try:
                priority, submit_time, task_id = await asyncio.wait_for(
                    self.pending_queue.get(),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                # No more tasks in queue
                if not running_futures:
                    break
                # Wait for running tasks
                continue
            
            task = self.tasks.get(task_id)
            if not task:
                continue
            
            # Check dependencies
            if not self._can_run(task):
                # Re-queue task
                self.pending_queue.put_nowait((priority, submit_time, task_id))
                continue
            
            # Start task
            future = asyncio.create_task(self._execute_task(task))
            running_futures.append(future)
        
        # Wait for all running tasks
        if running_futures:
            await asyncio.gather(*running_futures, return_exceptions=True)
        
        # Collect results
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.COMPLETED:
                results[task.agent] = task.result
            elif task.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT):
                errors[task.agent] = task.error or "Unknown error"
        
        duration = time.time() - start_time
        
        return AggregatedResult(
            success=len(errors) == 0,
            total_tasks=len(self.tasks),
            successful=len(results),
            failed=len(errors),
            duration=duration,
            results=results,
            errors=errors,
        )
    
    async def execute_one(self, task_id: str) -> Optional[AgentTaskSpec]:
        """Execute a single task by ID."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        if not self._can_run(task):
            return None
        
        return await self._execute_task(task)
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
            return False
        
        task.status = TaskStatus.CANCELLED
        self._stats.pending -= 1
        self._stats.cancelled += 1
        
        return True
    
    def cancel_all(self):
        """Cancel all pending tasks."""
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                self._stats.pending -= 1
                self._stats.cancelled += 1
    
    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a task."""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        return self._stats
    
    def get_result(self, task_id: str) -> Optional[str]:
        """Get result of a completed task."""
        task = self.tasks.get(task_id)
        return task.result if task and task.status == TaskStatus.COMPLETED else None
    
    def clear(self):
        """Clear all tasks and reset state."""
        self.tasks.clear()
        self.running_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self._stats = PoolStats(max_concurrent=self.max_concurrent)
        
        # Create new queue
        self.pending_queue = asyncio.PriorityQueue()


# Convenience function
def create_pool(max_concurrent: int = 5) -> ParallelAgentPool:
    """Create a new parallel agent pool."""
    return ParallelAgentPool(max_concurrent=max_concurrent)


# CLI test
if __name__ == "__main__":
    async def test():
        print("\n=== Parallel Agent Pool Test ===\n")
        
        pool = ParallelAgentPool(max_concurrent=3)
        
        # Track progress
        def on_progress(task: AgentTaskSpec):
            print(f"  [{task.agent}] Status: {task.status.value}")
        
        pool.on_progress(on_progress)
        
        # Submit tasks with different priorities
        print("Submitting tasks...")
        
        t1 = pool.submit("Dev", "Implement feature A", priority=TaskPriority.HIGH)
        t2 = pool.submit("QA", "Test feature A", priority=TaskPriority.NORMAL, depends_on=[t1])
        t3 = pool.submit("Sec", "Security review", priority=TaskPriority.NORMAL, depends_on=[t1])
        t4 = pool.submit("Dev", "Implement feature B", priority=TaskPriority.LOW)
        t5 = pool.submit("Ops", "Deploy to staging", priority=TaskPriority.HIGH, depends_on=[t2, t3])
        
        print(f"Submitted 5 tasks: {t1}, {t2}, {t3}, {t4}, {t5}")
        print()
        
        # Execute all
        print("Executing...")
        result = await pool.execute_all()
        
        print()
        print(f"Results: {result.summary()}")
        print(f"Stats: {pool.get_stats().to_dict()}")
        
        print("\n=== Test Complete ===")
    
    asyncio.run(test())
