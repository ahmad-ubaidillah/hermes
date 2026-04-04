"""Vector memory system for Aizen Agent.

Provides ChromaDB integration for semantic memory search,
enabling context-aware responses based on past conversations.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A memory entry in the vector store."""

    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class VectorMemory:
    """Vector memory using ChromaDB for semantic search."""

    def __init__(
        self,
        collection_name: str = "aizen_memory",
        persist_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize vector memory.

        Args:
            collection_name: Name of the Chroma collection
            persist_directory: Directory to persist Chroma data
            embedding_model: Sentence transformer model name
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None

    def _init_client(self) -> None:
        """Initialize ChromaDB client."""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.warning("chromadb not installed. Vector memory unavailable.")
            return

        self._client = chromadb.Client(
            Settings(
                persist_directory=self.persist_directory, anonymized_telemetry=False
            )
        )

        try:
            self._collection = self._client.get_collection(self.collection_name)
        except Exception:
            self._collection = self._client.create_collection(
                self.collection_name, metadata={"hnsw:space": "cosine"}
            )

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """Add a memory to the vector store.

        Args:
            content: Memory content
            metadata: Associated metadata
            memory_id: Optional ID (generated if not provided)

        Returns:
            Memory ID
        """
        if self._client is None:
            self._init_client()

        if self._collection is None:
            return ""

        import uuid

        memory_id = memory_id or str(uuid.uuid4())
        metadata = metadata or {}

        try:
            self._collection.add(
                documents=[content], metadatas=[metadata], ids=[memory_id]
            )
            logger.debug(f"Added memory: {memory_id}")
        except Exception as e:
            logger.warning(f"Failed to add memory: {e}")

        return memory_id

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """Search for similar memories.

        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Filter by metadata

        Returns:
            List of MemoryEntry
        """
        if self._client is None:
            self._init_client()

        if self._collection is None:
            return []

        try:
            results = self._collection.query(
                query_texts=[query], n_results=n_results, where=filter_metadata
            )

            memories = []
            if results and results.get("ids"):
                for i, mem_id in enumerate(results["ids"][0]):
                    entry = MemoryEntry(
                        id=mem_id,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i]
                        if results.get("metadatas")
                        else {},
                    )
                    memories.append(entry)

            return memories

        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            MemoryEntry or None
        """
        if self._client is None:
            self._init_client()

        if self._collection is None:
            return None

        try:
            result = self._collection.get(memory_id)
            if result and result.get("documents"):
                return MemoryEntry(
                    id=memory_id,
                    content=result["documents"][0],
                    metadata=result.get("metadatas", [{}])[0],
                )
        except Exception:
            pass

        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted
        """
        if self._client is None:
            self._init_client()

        if self._collection is None:
            return False

        try:
            self._collection.delete(memory_id)
            return True
        except Exception:
            return False

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a memory.

        Args:
            memory_id: Memory ID
            content: New content
            metadata: New metadata

        Returns:
            True if updated
        """
        if self._client is None:
            self._init_client()

        if self._collection is None:
            return False

        try:
            update_data = {"ids": [memory_id]}
            if content:
                update_data["documents"] = [content]
            if metadata:
                update_data["metadatas"] = [metadata]

            self._collection.update(**update_data)
            return True
        except Exception:
            return False

    def get_count(self) -> int:
        """Get total number of memories.

        Returns:
            Memory count
        """
        if self._collection is None:
            return 0

        try:
            return self._collection.count()
        except Exception:
            return 0

    def clear(self) -> None:
        """Clear all memories."""
        if self._client is None:
            return

        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.create_collection(
                self.collection_name, metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.warning(f"Failed to clear memories: {e}")


_default_vector_memory: Optional[VectorMemory] = None


def get_vector_memory() -> VectorMemory:
    """Get the default vector memory instance."""
    global _default_vector_memory
    if _default_vector_memory is None:
        _default_vector_memory = VectorMemory()
    return _default_vector_memory


def init_vector_memory(
    collection_name: str = "aizen_memory",
    persist_directory: Optional[str] = None,
    embedding_model: str = "all-MiniLM-L6-v2",
) -> VectorMemory:
    """Initialize the default vector memory.

    Args:
        collection_name: Name of the collection
        persist_directory: Directory to persist data
        embedding_model: Embedding model name

    Returns:
        Initialized VectorMemory instance
    """
    global _default_vector_memory
    _default_vector_memory = VectorMemory(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_model=embedding_model,
    )
    return _default_vector_memory


def search_memories(query: str, n_results: int = 5) -> List[MemoryEntry]:
    """Quick search function using default vector memory.

    Args:
        query: Search query
        n_results: Number of results

    Returns:
        List of MemoryEntry
    """
    return get_vector_memory().search(query, n_results)
