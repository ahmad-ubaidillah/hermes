"""
Background Agents - Parallel agent execution pool.

Run multiple specialists in parallel, keeping context lean.
Results when ready. Inspired by oh-my-openagent.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


@dataclass
class AgentTask:
    """Represents a background agent task."""
    
    id: str
    agent: str
    prompt: str
    skill: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def duration(self) -> float:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        if self.started_at:
            return time.time() - self.started_at
        return 0.0


@dataclass
class BackgroundResult:
    """Result from a background agent task."""
    
    task_id: str
    agent: str
    success: bool
    output: str
    duration: float
    tokens_used: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "success": self.success,
            "output": self.output,
            "duration": self.duration,
            "tokens_used": self.tokens_used,
            "error": self.error,
        }


class BackgroundAgentPool:
    """
    Manages background agent execution.
    
    Fire 5+ specialists in parallel. Context stays lean.
    Results when ready.
    """
    
    MAX_CONCURRENT = 5
    DEFAULT_TIMEOUT = 300
    
    def __init__(self, hermes_path: Optional[str] = None):
        self.tasks: Dict[str, AgentTask] = {}
        self.results: Dict[str, BackgroundResult] = {}
        self._running: Dict[str, asyncio.Task] = {}
        
        # Find Hermes CLI path
        self.hermes_path = hermes_path or self._find_hermes_cli()
    
    def _find_hermes_cli(self) -> str:
        """Find Hermes CLI executable."""
        # Check common locations
        candidates = [
            Path.home() / ".hermes" / "hermes-agent" / "cli.py",
            Path.home() / ".local" / "bin" / "hermes",
            Path("/usr/local/bin/hermes"),
        ]
        
        for path in candidates:
            if path.exists():
                return str(path)
        
        # Fallback to python module
        return "hermes"
    
    async def spawn(
        self,
        agent: str,
        prompt: str,
        skill: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Spawn a background agent task.
        
        Args:
            agent: Agent name (e.g., "Dev", "QA", "Research")
            prompt: Task prompt/instruction
            skill: Optional skill to load
            timeout: Timeout in seconds
        
        Returns:
            Task ID
        """
        task_id = f"bg_{uuid.uuid4().hex[:8]}"
        
        task = AgentTask(
            id=task_id,
            agent=agent,
            prompt=prompt,
            skill=skill,
        )
        
        self.tasks[task_id] = task
        
        # Create async task
        async_task = asyncio.create_task(
            self._execute(task, timeout)
        )
        self._running[task_id] = async_task
        
        return task_id
    
    async def _execute(self, task: AgentTask, timeout: int):
        """Execute agent task."""
        task.status = "running"
        task.started_at = time.time()
        
        try:
            # Build command
            cmd = self._build_command(task)
            
            # Run subprocess with timeout
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise TimeoutError(f"Task timed out after {timeout}s")
            
            task.completed_at = time.time()
            
            if proc.returncode == 0:
                task.result = stdout.decode("utf-8", errors="replace")
                task.status = "completed"
                
                self.results[task.id] = BackgroundResult(
                    task_id=task.id,
                    agent=task.agent,
                    success=True,
                    output=task.result,
                    duration=task.duration(),
                )
            else:
                error_msg = stderr.decode("utf-8", errors="replace")
                task.error = error_msg
                task.status = "failed"
                
                self.results[task.id] = BackgroundResult(
                    task_id=task.id,
                    agent=task.agent,
                    success=False,
                    output="",
                    duration=task.duration(),
                    error=error_msg,
                )
        
        except Exception as e:
            task.completed_at = time.time()
            task.error = str(e)
            task.status = "failed"
            
            self.results[task.id] = BackgroundResult(
                task_id=task.id,
                agent=task.agent,
                success=False,
                output="",
                duration=task.duration(),
                error=str(e),
            )
        
        finally:
            # Cleanup
            if task.id in self._running:
                del self._running[task.id]
    
    def _build_command(self, task: AgentTask) -> List[str]:
        """Build CLI command for task."""
        cmd = [sys.executable, self.hermes_path]
        
        if task.skill:
            cmd.extend(["--skill", task.skill])
        
        # Add agent context if using multi-agent
        cmd.extend(["--agent", task.agent])
        
        # Add prompt
        cmd.append(task.prompt)
        
        return cmd
    
    async def spawn_parallel(
        self,
        tasks: List[Dict[str, Any]],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, str]:
        """
        Spawn multiple agents in parallel.
        
        Args:
            tasks: List of task dicts with 'agent', 'prompt', optional 'skill'
            timeout: Timeout per task
        
        Returns:
            Dict mapping agent name to task ID
        """
        if len(tasks) > self.MAX_CONCURRENT:
            # Batch execution
            results = {}
            for i in range(0, len(tasks), self.MAX_CONCURRENT):
                batch = tasks[i:i + self.MAX_CONCURRENT]
                batch_results = await asyncio.gather(*[
                    self.spawn(
                        t["agent"],
                        t["prompt"],
                        t.get("skill"),
                        timeout,
                    )
                    for t in batch
                ])
                for t, tid in zip(batch, batch_results):
                    results[t["agent"]] = tid
            return results
        
        # All at once
        results = {}
        for t in tasks:
            tid = await self.spawn(
                t["agent"],
                t["prompt"],
                t.get("skill"),
                timeout,
            )
            results[t["agent"]] = tid
        
        return results
    
    async def wait(
        self,
        task_id: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> BackgroundResult:
        """Wait for task completion."""
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            if task_id in self.results:
                return self.results[task_id]
            
            if task_id in self._running:
                try:
                    await asyncio.wait_for(
                        self._running[task_id],
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(0.5)
        
        # Timeout
        return BackgroundResult(
            task_id=task_id,
            agent=self.tasks.get(task_id, AgentTask(id=task_id, agent="unknown", prompt="")).agent,
            success=False,
            output="",
            duration=timeout,
            error="Timeout waiting for result",
        )
    
    async def wait_all(
        self,
        task_ids: List[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> List[BackgroundResult]:
        """Wait for all tasks to complete."""
        results = await asyncio.gather(*[
            self.wait(tid, timeout)
            for tid in task_ids
        ])
        return list(results)
    
    async def wait_for_agents(
        self,
        agent_names: List[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, BackgroundResult]:
        """Wait for results from specific agents."""
        task_ids = []
        for agent in agent_names:
            for tid, task in self.tasks.items():
                if task.agent == agent:
                    task_ids.append(tid)
                    break
        
        results = await self.wait_all(task_ids, timeout)
        return {r.agent: r for r in results}
    
    def status(self) -> Dict[str, Any]:
        """Get pool status."""
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "running": sum(1 for t in self.tasks.values() if t.status == "running"),
            "completed": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "failed": sum(1 for t in self.tasks.values() if t.status == "failed"),
            "max_concurrent": self.MAX_CONCURRENT,
        }
    
    def get_result(self, task_id: str) -> Optional[BackgroundResult]:
        """Get result for a task."""
        return self.results.get(task_id)
    
    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def clear_completed(self):
        """Clear completed/failed tasks and results."""
        to_remove = [
            tid for tid, task in self.tasks.items()
            if task.status in ("completed", "failed")
        ]
        
        for tid in to_remove:
            if tid in self.tasks:
                del self.tasks[tid]
            if tid in self.results:
                del self.results[tid]


# Singleton
_pool: Optional[BackgroundAgentPool] = None


def get_background_pool() -> BackgroundAgentPool:
    """Get singleton BackgroundAgentPool instance."""
    global _pool
    if _pool is None:
        _pool = BackgroundAgentPool()
    return _pool


# Convenience functions
async def spawn_agent(agent: str, prompt: str, skill: Optional[str] = None) -> str:
    """Spawn a single background agent."""
    return await get_background_pool().spawn(agent, prompt, skill)


async def spawn_parallel(tasks: List[Dict[str, Any]]) -> Dict[str, str]:
    """Spawn multiple agents in parallel."""
    return await get_background_pool().spawn_parallel(tasks)


# CLI test
if __name__ == "__main__":
    async def test():
        print("\n=== Background Agent Pool Test ===\n")
        
        pool = BackgroundAgentPool()
        
        # Spawn parallel agents
        print("Spawning 3 agents in parallel...")
        task_ids = await pool.spawn_parallel([
            {"agent": "Dev", "prompt": "Check code style"},
            {"agent": "QA", "prompt": "Run tests"},
            {"agent": "Sec", "prompt": "Security scan"},
        ])
        
        print(f"Task IDs: {task_ids}")
        print(f"Pool status: {pool.status()}")
        
        # Wait for results
        print("\nWaiting for results...")
        results = await pool.wait_all(list(task_ids.values()))
        
        for r in results:
            print(f"\n[{r.agent}] Success: {r.success}")
            print(f"  Duration: {r.duration:.2f}s")
            if r.error:
                print(f"  Error: {r.error[:100]}")
        
        print(f"\nFinal status: {pool.status()}")
    
    asyncio.run(test())
