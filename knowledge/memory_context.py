"""
Aizen Memory Context Provider

Automatically injects relevant memories into the agent context
before each request and stores conversations after.

Based on Supermemory's context provider pattern.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from typing import Any, Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass

from knowledge.memory_store import MemoryStore, Memory


@dataclass
class MemoryContextConfig:
    """Configuration for memory context injection."""
    
    # Memory retrieval mode
    mode: str = "full"  # "profile", "query", "full"
    
    # Auto-store conversations
    store_conversations: bool = True
    
    # Custom context prompt
    context_prompt: str = ""
    
    # Verbose logging
    verbose: bool = False
    
    # Max memories to inject
    max_memories: int = 20


class MemoryContextProvider:
    """
    Context provider that injects memories into agent context.
    
    This follows Supermemory's pattern:
    1. Before request: Fetch relevant memories and inject
    2. After request: Store conversation as memory
    
    Usage:
        provider = MemoryContextProvider(
            container_tag="user-ahmad",
            config=MemoryContextConfig(mode="full")
        )
        
        # In agent lifecycle
        context = provider.before_request(user_message)
        # ... agent processes ...
        provider.after_request(conversation)
    """
    
    def __init__(
        self,
        container_tag: str = "default",
        config: MemoryContextConfig = None,
        memory_store: MemoryStore = None,
    ):
        self.container_tag = container_tag
        self.config = config or MemoryContextConfig()
        self.store = memory_store or MemoryStore(container_tag=container_tag)
        self._background_tasks: set = set()
    
    def before_request(
        self,
        user_message: str = "",
        query: Optional[str] = None,
    ) -> str:
        """
        Get memory context to inject before agent request.
        
        Args:
            user_message: Current user message (for query mode)
            query: Optional search query override
        
        Returns:
            Formatted memory context string
        """
        search_query = query or (user_message if self.config.mode != "profile" else "")
        
        return self.store.format_for_injection(
            container_tag=self.container_tag,
            query=search_query if self.config.mode in ("query", "full") else None,
            context_prompt=self.config.context_prompt,
        )
    
    def after_request(
        self,
        conversation: str,
        source: str = "conversation",
        forget_after_days: Optional[int] = None,
    ) -> None:
        """
        Store conversation as memory (non-blocking).
        
        Args:
            conversation: Conversation text to store
            source: Source identifier
            forget_after_days: Optional TTL in days
        """
        if not self.config.store_conversations or not conversation.strip():
            return
        
        # Store in background (don't block)
        self._store_async(conversation, source, forget_after_days)
    
    def _store_async(
        self,
        content: str,
        source: str,
        forget_after_days: Optional[int],
    ) -> None:
        """Store memory asynchronously."""
        try:
            # For simplicity, store synchronously
            # In production, use asyncio.create_task
            self.store.add(
                content=content,
                is_static=False,
                forget_after_days=forget_after_days,
                source=source,
            )
            
            if self.config.verbose:
                print(f"[memory] Stored: {content[:50]}...")
                
        except Exception as e:
            if self.config.verbose:
                print(f"[memory] Error storing: {e}")
    
    def add_memory(
        self,
        content: str,
        is_static: bool = False,
        forget_after_days: Optional[int] = None,
    ) -> Memory:
        """
        Manually add a memory.
        
        Args:
            content: Memory content
            is_static: If True, memory is permanent
            forget_after_days: TTL in days (for dynamic memories)
        
        Returns:
            Created Memory object
        """
        return self.store.add(
            content=content,
            is_static=is_static,
            forget_after_days=forget_after_days,
            source="manual",
        )
    
    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by query."""
        return self.store.search(query, limit=limit, container_tag=self.container_tag)
    
    def get_profile(self) -> dict:
        """Get user profile with static and dynamic memories."""
        profile = self.store.get_profile(self.container_tag)
        return {
            "static": profile.static,
            "dynamic": profile.dynamic,
        }
    
    def forget_memory(self, memory_id: str, reason: str = "manual") -> None:
        """Mark a memory as forgotten."""
        self.store.forget(memory_id, reason)
    
    def update_memory(self, memory_id: str, new_content: str) -> Memory:
        """Update a memory (creates new version)."""
        return self.store.update(memory_id, new_content)
    
    def clear_dynamic_memories(self) -> int:
        """Clear all dynamic memories."""
        return self.store.clear(self.container_tag, include_static=False)
    
    def stats(self) -> dict:
        """Get memory statistics."""
        return self.store.stats(self.container_tag)


# Integration helper for Aizen
def inject_memory_context(
    user_message: str,
    container_tag: str = "default",
    mode: str = "full",
) -> str:
    """
    Convenience function to inject memory context.
    
    Args:
        user_message: Current user message
        container_tag: Memory container tag
        mode: Memory retrieval mode ("profile", "query", "full")
    
    Returns:
        Formatted memory context to prepend to system prompt
    """
    provider = MemoryContextProvider(
        container_tag=container_tag,
        config=MemoryContextConfig(mode=mode),
    )
    return provider.before_request(user_message)


def store_conversation_memory(
    conversation: str,
    container_tag: str = "default",
    forget_after_days: int = 30,
) -> None:
    """
    Convenience function to store conversation as memory.
    
    Args:
        conversation: Conversation text
        container_tag: Memory container tag
        forget_after_days: TTL in days
    """
    provider = MemoryContextProvider(
        container_tag=container_tag,
        config=MemoryContextConfig(store_conversations=True),
    )
    provider.after_request(conversation, forget_after_days=forget_after_days)


# Example usage
if __name__ == "__main__":
    # Create provider
    provider = MemoryContextProvider(
        container_tag="user-ahmad",
        config=MemoryContextConfig(
            mode="full",
            store_conversations=True,
            verbose=True,
        )
    )
    
    # Add some memories
    provider.add_memory("User's name is Ahmad Ubaidillah", is_static=True)
    provider.add_memory("User develops Aizen agent framework", is_static=True)
    provider.add_memory("Currently working on memory integration", forget_after_days=7)
    
    # Get context for injection
    user_message = "What's my name and what am I working on?"
    context = provider.before_request(user_message)
    
    print("\n" + "=" * 60)
    print("MEMORY CONTEXT TO INJECT:")
    print("=" * 60)
    print(context)
    print("=" * 60 + "\n")
    
    # After conversation
    conversation = """
User: What's my name and what am I working on?
Assistant: Based on my memory, your name is Ahmad Ubaidillah. 
You're currently working on memory integration for the Aizen agent framework.
"""
    provider.after_request(conversation, forget_after_days=30)
    
    # Show stats
    stats = provider.stats()
    print(f"\nMemory Stats: {stats}")
