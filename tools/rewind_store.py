"""
RewindStore - Store original output for later retrieval.

When output is distilled, the original content is stored with a SHA-256 hash.
The agent can retrieve the original content if needed.

Usage:
    from tools.rewind_store import RewindStore
    
    store = RewindStore()
    hash_key = store.store(large_output)
    original = store.retrieve(hash_key)
"""

import hashlib
import sqlite3
import gzip
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class RewindStore:
    """
    Store original output for later retrieval.
    
    Data is stored in SQLite with gzip compression.
    """
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / ".hermes" / "rewind.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rewind_store (
                hash TEXT PRIMARY KEY,
                content BLOB NOT NULL,
                command TEXT,
                original_size INTEGER,
                compressed_size INTEGER,
                created_at TEXT,
                retrieval_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON rewind_store(created_at DESC)
        """)
        conn.commit()
        conn.close()
    
    def store(self, content: str, command: str = "") -> str:
        """
        Store content and return hash key.
        
        Args:
            content: Original output to store
            command: Command that produced the output
        
        Returns:
            Short hash key for retrieval
        """
        if not content:
            return ""
        
        # Create hash
        hash_key = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Compress content
        compressed = gzip.compress(content.encode())
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO rewind_store 
                (hash, content, command, original_size, compressed_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hash_key,
                compressed,
                command[:200],
                len(content),
                len(compressed),
                datetime.now().isoformat(),
            ))
            conn.commit()
        finally:
            conn.close()
        
        return hash_key
    
    def retrieve(self, hash_key: str) -> Optional[str]:
        """
        Retrieve original content by hash.
        
        Args:
            hash_key: Hash returned from store()
        
        Returns:
            Original content or None if not found
        """
        if not hash_key:
            return None
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT content FROM rewind_store WHERE hash = ?",
                (hash_key,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update retrieval count
                conn.execute(
                    "UPDATE rewind_store SET retrieval_count = retrieval_count + 1 WHERE hash = ?",
                    (hash_key,)
                )
                conn.commit()
                
                # Decompress and return
                return gzip.decompress(row[0]).decode()
            
            return None
        finally:
            conn.close()
    
    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent stored outputs.
        
        Returns:
            List of metadata dicts with hash, command, size, time
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT hash, command, original_size, compressed_size, created_at, retrieval_count
                FROM rewind_store
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor:
                results.append({
                    "hash": row[0],
                    "command": row[1],
                    "original_size": row[2],
                    "compressed_size": row[3],
                    "created_at": row[4],
                    "retrieval_count": row[5],
                    "compression_ratio": f"{100 - (row[3] / row[2] * 100):.0f}%",
                })
            
            return results
        finally:
            conn.close()
    
    def delete_old(self, days: int = 7) -> int:
        """
        Delete entries older than specified days.
        
        Returns:
            Number of deleted entries
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                DELETE FROM rewind_store
                WHERE datetime(created_at) < datetime('now', ?)
            """, (f"-{days} days",))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    def stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(original_size) as total_original,
                    SUM(compressed_size) as total_compressed,
                    SUM(retrieval_count) as total_retrievals
                FROM rewind_store
            """)
            row = cursor.fetchone()
            
            if row and row[0]:
                return {
                    "total_entries": row[0],
                    "total_original_size": row[1] or 0,
                    "total_compressed_size": row[2] or 0,
                    "total_retrievals": row[3] or 0,
                    "compression_ratio": f"{100 - ((row[2] or 0) / (row[1] or 1) * 100):.0f}%",
                }
            
            return {
                "total_entries": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "total_retrievals": 0,
                "compression_ratio": "0%",
            }
        finally:
            conn.close()


# CLI interface
def main():
    """CLI for RewindStore."""
    import sys
    
    store = RewindStore()
    
    if len(sys.argv) < 2:
        print("Usage: python rewind_store.py <command> [args]")
        print("Commands:")
        print("  list              List recent entries")
        print("  show <hash>       Show content by hash")
        print("  stats             Show statistics")
        print("  clean [days]      Delete old entries (default: 7 days)")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        entries = store.list_recent()
        print(f"\nRecent stored outputs ({len(entries)}):\n")
        for e in entries:
            print(f"  {e['hash'][:8]}... | {e['command'][:30]:<30} | {e['original_size']:>6} bytes | {e['created_at'][:10]}")
        print()
    
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: python rewind_store.py show <hash>")
            return
        content = store.retrieve(sys.argv[2])
        if content:
            print(content)
        else:
            print(f"Not found: {sys.argv[2]}")
    
    elif cmd == "stats":
        stats = store.stats()
        print(f"\nRewindStore Statistics:")
        print(f"  Entries: {stats['total_entries']}")
        print(f"  Original size: {stats['total_original_size']:,} bytes")
        print(f"  Compressed size: {stats['total_compressed_size']:,} bytes")
        print(f"  Compression: {stats['compression_ratio']}")
        print(f"  Total retrievals: {stats['total_retrievals']}")
        print()
    
    elif cmd == "clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        deleted = store.delete_old(days)
        print(f"Deleted {deleted} entries older than {days} days")
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
