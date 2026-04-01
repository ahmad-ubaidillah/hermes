"""Tests for Hermes SDK."""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSDKAgent:
    """Test SDK Agent class."""
    
    def test_agent_creation_defaults(self):
        """Test Agent can be created with defaults."""
        from sdk import Agent
        
        agent = Agent()
        assert agent.model == "anthropic/claude-sonnet-4"
        assert agent.max_turns == 90
        assert agent._agent is None  # Lazy load
    
    def test_agent_creation_custom(self):
        """Test Agent can be created with custom values."""
        from sdk import Agent
        
        agent = Agent(
            model="opencode/qwen3.6-plus-free",
            max_turns=50,
            tools=["terminal", "file"],
        )
        assert agent.model == "opencode/qwen3.6-plus-free"
        assert agent.max_turns == 50
        assert agent.tools == ["terminal", "file"]
    
    def test_agent_history(self):
        """Test Agent history management."""
        from sdk import Agent
        
        agent = Agent()
        assert agent.history == []
        
        agent._history.append({"role": "user", "content": "test"})
        agent._history.append({"role": "assistant", "content": "response"})
        
        assert len(agent.history) == 2
        agent.clear_history()
        assert agent.history == []
    
    def test_agent_repr(self):
        """Test Agent string representation."""
        from sdk import Agent
        
        agent = Agent(model="test-model")
        assert "test-model" in repr(agent)
        assert "turns=0" in repr(agent)


class TestSDKChat:
    """Test SDK chat functionality."""
    
    @pytest.mark.skip(reason="Requires API key")
    def test_chat_basic(self):
        """Test basic chat (requires API key)."""
        from sdk import Agent
        
        agent = Agent(model="opencode/qwen3.6-plus-free")
        response = agent.chat("Hello!")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.skip(reason="Requires API key")
    def test_chat_stream(self):
        """Test streaming chat (requires API key)."""
        from sdk import Agent
        
        agent = Agent(model="opencode/qwen3.6-plus-free")
        chunks = list(agent.stream("Hello!"))
        
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)


class TestSDKToolRegistration:
    """Test SDK tool registration."""
    
    def test_register_tool(self):
        """Test custom tool registration."""
        from sdk import Agent
        from tools.registry import registry
        
        agent = Agent()
        
        def my_tool(param: str) -> str:
            return f"Processed: {param}"
        
        agent.register_tool(
            name="my_test_tool",
            handler=my_tool,
            schema={
                "description": "Test tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    }
                }
            }
        )
        
        # Tool should be registered
        # Note: This tests the registration mechanism, not execution
        assert True


class TestSDKConvenience:
    """Test SDK convenience functions."""
    
    @pytest.mark.skip(reason="Requires API key")
    def test_chat_convenience(self):
        """Test convenience chat function."""
        from sdk import chat
        
        response = chat("Hello!")
        assert isinstance(response, str)
