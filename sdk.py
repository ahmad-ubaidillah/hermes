"""Hermes Agent SDK - Simple embedding API.

Usage:
    from sdk import Agent
    
    agent = Agent(model="anthropic/claude-sonnet-4")
    response = agent.chat("Hello!")
    
    # Async
    response = await agent.achat("Hello!")
    
    # Streaming
    for chunk in agent.stream("Hello!"):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional


class Agent:
    """Simple Hermes Agent wrapper for embedding.
    
    Example:
        agent = Agent(model="anthropic/claude-sonnet-4")
        response = agent.chat("What is 2+2?")
        print(response)  # "4"
    """

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4",
        system: Optional[str] = None,
        max_turns: int = 90,
        tools: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        hermes_home: Optional[Path] = None,
    ):
        """Initialize Agent.
        
        Args:
            model: Model identifier (e.g., "anthropic/claude-sonnet-4")
            system: Optional system prompt
            max_turns: Maximum conversation turns
            tools: List of enabled toolsets (None = all available)
            api_key: API key (uses env var if not provided)
            base_url: Optional API base URL override
            hermes_home: Optional HERMES_HOME path override
        """
        self.model = model
        self.system = system
        self.max_turns = max_turns
        self.tools = tools
        self.api_key = api_key
        self.base_url = base_url
        self.hermes_home = hermes_home
        
        self._agent = None
        self._history: List[Dict[str, str]] = []

    def _get_agent(self):
        """Lazy-load AIAgent to avoid import overhead."""
        if self._agent is None:
            from run_agent import AIAgent
            
            kwargs = {
                "model": self.model,
                "max_iterations": self.max_turns,
            }
            if self.system:
                kwargs["system_message"] = self.system
            if self.tools:
                kwargs["enabled_toolsets"] = self.tools
            if self.api_key:
                os.environ["ANTHROPIC_API_KEY"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            if self.hermes_home:
                os.environ["HERMES_HOME"] = str(self.hermes_home)
            
            self._agent = AIAgent(**kwargs)
        return self._agent

    def chat(self, message: str) -> str:
        """Send a message and get a response.
        
        Args:
            message: User message
            
        Returns:
            Agent response string
        """
        agent = self._get_agent()
        response = agent.chat(message)
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "assistant", "content": response})
        return response

    async def achat(self, message: str) -> str:
        """Async version of chat.
        
        Args:
            message: User message
            
        Returns:
            Agent response string
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat, message)

    def stream(self, message: str) -> Iterator[str]:
        """Stream response chunks.
        
        Note: Current implementation returns full response at once,
        then yields it in chunks for compatibility.
        
        Args:
            message: User message
            
        Yields:
            Response chunks
        """
        response = self.chat(message)
        # Yield in chunks of ~50 chars for streaming feel
        chunk_size = 50
        for i in range(0, len(response), chunk_size):
            yield response[i:i + chunk_size]

    async def astream(self, message: str):
        """Async version of stream."""
        for chunk in self.stream(message):
            yield chunk
            await asyncio.sleep(0)  # Yield control

    def register_tool(self, name: str, handler: Callable, schema: Dict[str, Any]):
        """Register a custom tool.
        
        Args:
            name: Tool name
            handler: Tool handler function
            schema: JSON schema for tool parameters
        """
        from tools.registry import registry
        
        registry.register(
            name=name,
            toolset="custom",
            schema={
                "name": name,
                "description": schema.get("description", f"Custom tool: {name}"),
                "parameters": schema.get("parameters", {}),
            },
            handler=lambda args, **kw: handler(**args),
        )

    @property
    def history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._history.copy()

    def clear_history(self):
        """Clear conversation history."""
        self._history.clear()

    def __repr__(self) -> str:
        turns = len(self._history) // 2
        return f"Agent(model={self.model!r}, turns={turns})"


# Convenience exports
__all__ = ["Agent"]
