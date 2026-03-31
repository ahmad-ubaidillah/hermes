"""
Hermes v3.0 Integration - Connects IntentGate, BackgroundAgents, and Hooks.

Main orchestration module that routes requests through the intelligence pipeline:
    IntentGate → Planning → Execution → Review → Report
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Import routing
from routing.intent_gate import IntentGate, IntentType, IntentResult

# Import lifecycle
from lifecycle.background_agents import BackgroundAgentPool, BackgroundResult
from lifecycle.hooks import HookRegistry, HookEvent, HookContext, hooks


@dataclass
class PipelineResult:
    """Result from the intelligence pipeline."""
    
    success: bool
    intent: IntentResult
    output: str
    agent_results: Dict[str, BackgroundResult] = None
    duration: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.agent_results is None:
            self.agent_results = {}


class HermesPipeline:
    """
    Main intelligence pipeline for Hermes v3.0.
    
    Flow:
        1. IntentGate - classify user intent
        2. Hooks - pre-processing
        3. Execution - direct or parallel agents
        4. Hooks - post-processing
        5. Report - return results
    """
    
    def __init__(self):
        self.intent_gate = IntentGate()
        self.agent_pool = BackgroundAgentPool()
        self.hooks = hooks
    
    async def process(self, user_input: str, context: str = "") -> PipelineResult:
        """
        Process user input through the intelligence pipeline.
        
        Args:
            user_input: User's request/message
            context: Optional additional context
        
        Returns:
            PipelineResult with outcome
        """
        import time
        start_time = time.time()
        
        # 1. Intent classification
        intent = self.intent_gate.analyze(user_input, context)
        
        # Trigger intent hook
        hook_ctx = await self.hooks.trigger(
            HookEvent.INTENT_CLASSIFIED,
            {"intent": intent.intent.value, "confidence": intent.confidence}
        )
        
        # 2. Check if needs confirmation
        if intent.requires_confirmation:
            return PipelineResult(
                success=True,
                intent=intent,
                output=f"{intent.verbalize()}\n\nAwaiting your confirmation to proceed.",
                duration=time.time() - start_time,
            )
        
        # 3. Route based on intent
        try:
            if intent.is_flash_task:
                # Quick execution
                result = await self._flash_execute(user_input, intent)
            elif intent.requires_planning:
                # Planning workflow
                result = await self._planning_workflow(user_input, intent)
            else:
                # Standard routing
                result = await self._standard_route(user_input, intent)
            
            # Trigger completion hook
            await self.hooks.trigger(
                HookEvent.AGENT_COMPLETE,
                {"agent": intent.suggested_agent, "result": result}
            )
            
            return PipelineResult(
                success=True,
                intent=intent,
                output=result,
                duration=time.time() - start_time,
            )
        
        except Exception as e:
            # Trigger error hook
            await self.hooks.trigger(
                HookEvent.AGENT_ERROR,
                {"agent": intent.suggested_agent, "error": str(e)}
            )
            
            return PipelineResult(
                success=False,
                intent=intent,
                output="",
                error=str(e),
                duration=time.time() - start_time,
            )
    
    async def _flash_execute(self, user_input: str, intent: IntentResult) -> str:
        """Execute flash task immediately."""
        # For flash tasks, return intent verbalization
        # In production, this would call the actual Flash agent
        return f"[Flash] {intent.verbalize()}\nExecuting: {user_input}"
    
    async def _planning_workflow(self, user_input: str, intent: IntentResult) -> str:
        """Execute planning workflow."""
        # Trigger sprint start hook
        await self.hooks.trigger(
            HookEvent.SPRINT_START,
            {"task": user_input, "agent": intent.suggested_agent}
        )
        
        # In production, this would:
        # 1. Call Prometheus for planning
        # 2. Delegate to appropriate agents
        # 3. Collect results
        
        return f"[{intent.suggested_agent}] Planning workflow for: {user_input}"
    
    async def _standard_route(self, user_input: str, intent: IntentResult) -> str:
        """Route to standard agent workflow."""
        agent = intent.suggested_agent
        
        # Trigger assignment hook
        await self.hooks.trigger(
            HookEvent.SPRINT_TASK_ASSIGNED,
            {"task": user_input, "agent": agent}
        )
        
        # In production, spawn background agent
        # task_id = await self.agent_pool.spawn(agent, user_input)
        # result = await self.agent_pool.wait(task_id)
        
        return f"[{agent}] {intent.suggested_workflow}: {user_input}"
    
    async def parallel_execute(
        self,
        tasks: List[Dict[str, str]],
    ) -> Dict[str, BackgroundResult]:
        """
        Execute multiple tasks in parallel with background agents.
        
        Args:
            tasks: List of {"agent": "...", "prompt": "...", "skill": "..."}
        
        Returns:
            Dict mapping agent name to result
        """
        # Trigger spawn hook
        await self.hooks.trigger(
            HookEvent.AGENT_SPAWN,
            {"tasks": tasks}
        )
        
        # Spawn all agents
        task_ids = await self.agent_pool.spawn_parallel(tasks)
        
        # Wait for all
        results = await self.agent_pool.wait_all(list(task_ids.values()))
        
        # Map back to agent names
        return {
            tasks[i]["agent"]: results[i]
            for i in range(len(tasks))
        }


# Singleton
_pipeline: Optional[HermesPipeline] = None


def get_pipeline() -> HermesPipeline:
    """Get singleton HermesPipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = HermesPipeline()
    return _pipeline


async def process_request(user_input: str, context: str = "") -> PipelineResult:
    """Convenience function to process a request."""
    return await get_pipeline().process(user_input, context)


# Integration with Hermes CLI

def integrate_with_cli():
    """
    Integration point for Hermes CLI.
    
    Add to hermes_cli/main.py:
        from orchestration import process_request, get_pipeline
        
        async def handle_message(user_input: str) -> str:
            result = await process_request(user_input)
            return result.output
    """
    pass


# CLI test
if __name__ == "__main__":
    async def test():
        print("\n=== Hermes v3.0 Pipeline Test ===\n")
        
        pipeline = HermesPipeline()
        
        test_cases = [
            "quick show me the files",
            "implement user authentication",
            "what do you think about this architecture?",
            "fix the login bug",
        ]
        
        for case in test_cases:
            print(f"Input: {case}")
            result = await pipeline.process(case)
            print(f"  Intent: {result.intent.intent.value}")
            print(f"  Agent: {result.intent.suggested_agent}")
            print(f"  Flash: {result.intent.is_flash_task}")
            print(f"  Output: {result.output[:100]}...")
            print(f"  Duration: {result.duration:.3f}s")
            print()
        
        # Test parallel execution
        print("--- Parallel Execution Test ---")
        results = await pipeline.parallel_execute([
            {"agent": "Dev", "prompt": "Check code"},
            {"agent": "QA", "prompt": "Run tests"},
            {"agent": "Sec", "prompt": "Security scan"},
        ])
        
        for agent, result in results.items():
            print(f"  [{agent}] Success: {result.success}")
        
        print("\n=== Test Complete ===")
    
    asyncio.run(test())
