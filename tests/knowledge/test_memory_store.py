"""
Tests for Hermes Memory Store

Tests for:
- Memory creation (static/dynamic)
- Memory versioning
- Auto-forget (TTL)
- Deduplication
- Context injection
- Search functionality
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from knowledge.memory_store import (
    MemoryStore, Memory, MemoryType, Profile, DeduplicatedMemories
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memories.db"
        yield db_path


@pytest.fixture
def store(temp_db):
    """Create a memory store with temporary database."""
    return MemoryStore(db_path=temp_db, container_tag="test")


class TestMemoryCreation:
    """Tests for memory creation."""
    
    def test_add_static_memory(self, store):
        """Test adding a static (permanent) memory."""
        memory = store.add(
            content="User's name is Ahmad",
            is_static=True,
        )
        
        assert memory.id is not None
        assert memory.content == "User's name is Ahmad"
        assert memory.memory_type == MemoryType.STATIC
        assert memory.is_latest is True
        assert memory.is_forgotten is False
        assert memory.forget_after is None
    
    def test_add_dynamic_memory(self, store):
        """Test adding a dynamic (temporary) memory."""
        memory = store.add(
            content="Working on project X",
            is_static=False,
            forget_after_days=7,
        )
        
        assert memory.id is not None
        assert memory.content == "Working on project X"
        assert memory.memory_type == MemoryType.DYNAMIC
        assert memory.is_latest is True
        assert memory.forget_after is not None
    
    def test_add_dynamic_without_ttl(self, store):
        """Test adding dynamic memory without TTL."""
        memory = store.add(
            content="Session context",
            is_static=False,
        )
        
        assert memory.memory_type == MemoryType.DYNAMIC
        assert memory.forget_after is None
    
    def test_add_with_source_and_confidence(self, store):
        """Test adding memory with source and confidence."""
        memory = store.add(
            content="User prefers dark mode",
            source="conversation",
            confidence=0.9,
        )
        
        assert memory.source == "conversation"
        assert memory.confidence == 0.9


class TestMemoryRetrieval:
    """Tests for memory retrieval."""
    
    def test_get_memory_by_id(self, store):
        """Test retrieving a memory by ID."""
        created = store.add("Test content")
        retrieved = store.get(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.content == "Test content"
    
    def test_get_nonexistent_memory(self, store):
        """Test retrieving a nonexistent memory."""
        result = store.get("nonexistent-id")
        assert result is None
    
    def test_get_profile(self, store):
        """Test getting user profile."""
        store.add("Static fact 1", is_static=True)
        store.add("Static fact 2", is_static=True)
        store.add("Dynamic context 1", is_static=False)
        store.add("Dynamic context 2", is_static=False)
        
        profile = store.get_profile()
        
        assert len(profile.static) == 2
        assert len(profile.dynamic) == 2
        assert "Static fact 1" in profile.static
        assert "Dynamic context 1" in profile.dynamic
    
    def test_list_all_memories(self, store):
        """Test listing all memories."""
        store.add("Memory 1")
        store.add("Memory 2")
        store.add("Memory 3")
        
        memories = store.list_all()
        
        assert len(memories) == 3


class TestMemoryVersioning:
    """Tests for memory versioning."""
    
    def test_update_creates_new_version(self, store):
        """Test that updating creates a new version."""
        original = store.add("Original content")
        updated = store.update(original.id, "Updated content")
        
        assert updated.id != original.id
        assert updated.content == "Updated content"
        assert updated.version == 2
        assert updated.parent_id == original.id
        assert updated.root_id == original.id
        
        # Check original is no longer latest
        original_check = store.get(original.id)
        assert original_check.is_latest is False
    
    def test_version_chain(self, store):
        """Test version chain across multiple updates."""
        v1 = store.add("Version 1")
        v2 = store.update(v1.id, "Version 2")
        v3 = store.update(v2.id, "Version 3")
        
        assert v1.version == 1
        assert v2.version == 2
        assert v3.version == 3
        assert v3.parent_id == v2.id
        assert v3.root_id == v1.id
    
    def test_update_nonexistent_memory(self, store):
        """Test updating a nonexistent memory."""
        with pytest.raises(ValueError):
            store.update("nonexistent-id", "New content")


class TestMemoryForgetting:
    """Tests for memory forgetting."""
    
    def test_forget_memory(self, store):
        """Test forgetting a memory."""
        memory = store.add("To be forgotten")
        store.forget(memory.id, reason="manual")
        
        forgotten = store.get(memory.id)
        assert forgotten.is_forgotten is True
        assert forgotten.forget_reason == "manual"
    
    def test_forgotten_not_in_profile(self, store):
        """Test that forgotten memories don't appear in profile."""
        store.add("Active memory")
        to_forget = store.add("To forget")
        store.forget(to_forget.id)
        
        profile = store.get_profile()
        assert "Active memory" in profile.dynamic
        assert "To forget" not in profile.dynamic
    
    def test_auto_forget_expired(self, temp_db):
        """Test that expired memories are auto-forgotten."""
        store = MemoryStore(db_path=temp_db)
        
        # Add memory with past expiration
        memory = store.add(
            content="Expired memory",
            forget_after_days=-1,  # Already expired
        )
        
        # Trigger cleanup by getting profile
        profile = store.get_profile()
        
        # Check memory is forgotten
        forgotten = store.get(memory.id)
        assert forgotten.is_forgotten is True


class TestDeduplication:
    """Tests for memory deduplication."""
    
    def test_deduplicate_no_duplicates(self, store):
        """Test deduplication with no duplicates."""
        result = store.deduplicate(
            static=["A", "B"],
            dynamic=["C", "D"],
            search_results=["E", "F"],
        )
        
        assert result.static == ["A", "B"]
        assert result.dynamic == ["C", "D"]
        assert result.search_results == ["E", "F"]
    
    def test_deduplicate_with_duplicates(self, store):
        """Test deduplication removes duplicates."""
        result = store.deduplicate(
            static=["A", "B"],
            dynamic=["B", "C"],  # B is duplicate
            search_results=["C", "D"],  # C is duplicate
        )
        
        assert result.static == ["A", "B"]
        assert result.dynamic == ["C"]  # B already in static
        assert result.search_results == ["D"]  # C already in dynamic
    
    def test_deduplicate_case_insensitive(self, store):
        """Test deduplication is case-insensitive."""
        result = store.deduplicate(
            static=["User name is ahmad"],
            dynamic=["User Name Is Ahmad"],  # Same content, different case
            search_results=[],
        )
        
        assert len(result.static) == 1
        assert len(result.dynamic) == 0  # Deduplicated


class TestSearch:
    """Tests for memory search."""
    
    def test_search_by_content(self, store):
        """Test searching by content."""
        store.add("User likes Python")
        store.add("User dislikes Java")
        store.add("Python is great")
        
        results = store.search("Python")
        
        assert len(results) >= 2
        contents = [r.content for r in results]
        assert any("Python" in c for c in contents)
    
    def test_search_empty_results(self, store):
        """Test search with no matches."""
        store.add("Some content")
        
        results = store.search("nonexistent")
        
        assert len(results) == 0
    
    def test_search_excludes_forgotten(self, store):
        """Test that search excludes forgotten memories."""
        store.add("Active memory with keyword")
        forgotten = store.add("Forgotten memory with keyword")
        store.forget(forgotten.id)
        
        results = store.search("keyword")
        
        assert len(results) == 1
        assert "Active" in results[0].content


class TestContextInjection:
    """Tests for context injection."""
    
    def test_format_for_injection(self, store):
        """Test formatting memories for injection."""
        store.add("User's name is Ahmad", is_static=True)
        store.add("Working on Hermes", is_static=False)
        
        context = store.format_for_injection()
        
        assert "<hermes-memory" in context
        assert "</hermes-memory>" in context
        assert "readonly" in context
        assert "User's name is Ahmad" in context
        assert "Working on Hermes" in context
    
    def test_format_with_query(self, store):
        """Test formatting with search query."""
        store.add("User prefers dark mode", is_static=True)
        store.add("Current project is Hermes", is_static=False)
        
        context = store.format_for_injection(query="project")
        
        assert "Current project" in context
    
    def test_format_empty_memories(self, store):
        """Test formatting when no memories exist."""
        context = store.format_for_injection()
        
        assert context == ""


class TestStatistics:
    """Tests for memory statistics."""
    
    def test_stats(self, store):
        """Test getting memory statistics."""
        store.add("Static 1", is_static=True)
        store.add("Static 2", is_static=True)
        store.add("Dynamic 1", is_static=False)
        forgotten = store.add("To forget")
        store.forget(forgotten.id)
        
        stats = store.stats()
        
        assert stats["total"] == 4
        assert stats["static"] == 2
        assert stats["dynamic"] == 2
        assert stats["forgotten"] == 1


class TestClear:
    """Tests for clearing memories."""
    
    def test_clear_dynamic_only(self, store):
        """Test clearing only dynamic memories."""
        store.add("Static", is_static=True)
        store.add("Dynamic 1", is_static=False)
        store.add("Dynamic 2", is_static=False)
        
        deleted = store.clear(include_static=False)
        
        assert deleted == 2
        profile = store.get_profile()
        assert len(profile.static) == 1
        assert len(profile.dynamic) == 0
    
    def test_clear_all(self, store):
        """Test clearing all memories."""
        store.add("Static", is_static=True)
        store.add("Dynamic", is_static=False)
        
        deleted = store.clear(include_static=True)
        
        assert deleted == 2
        profile = store.get_profile()
        assert len(profile.static) == 0
        assert len(profile.dynamic) == 0


class TestContainerTags:
    """Tests for container tags."""
    
    def test_different_containers(self, temp_db):
        """Test that different containers are isolated."""
        store1 = MemoryStore(db_path=temp_db, container_tag="user1")
        store2 = MemoryStore(db_path=temp_db, container_tag="user2")
        
        store1.add("User 1 memory")
        store2.add("User 2 memory")
        
        profile1 = store1.get_profile()
        profile2 = store2.get_profile()
        
        assert "User 1 memory" in profile1.dynamic
        assert "User 2 memory" not in profile1.dynamic
        assert "User 2 memory" in profile2.dynamic
        assert "User 1 memory" not in profile2.dynamic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
