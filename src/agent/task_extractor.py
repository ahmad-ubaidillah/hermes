"""
Task Extraction Agent - Extracts tasks from conversation history and tracks their status.

Automatically analyzes conversations to detect task intents, extracts task details,
stores them in a database, and tracks their lifecycle (pending → running → success/failed).
"""

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.aizen_constants import get_aizen_home


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Intent patterns for task detection
TASK_INTENT_PATTERNS = [
    # Explicit task keywords
    r"\b(create|make|build|implement|add)\b.*\b(feature|function|tool|system)\b",
    r"\b(fix|repair|resolve|debug)\b.*\b(bug|issue|error|problem)\b",
    r"\b(refactor|optimize|improve)\b.*\b(code|performance|structure)\b",
    r"\b(write|document|create)\b.*\b(documentation|docs|readme)\b",
    r"\b(test|verify|check)\b.*\b(functionality|behavior|output)\b",
    # Action-oriented phrases
    r"^\s*(?:please|can you|could you|want to|i need to)\s+(.*)",
    r"^\s*(?:task|todo):\s*(.*)",
    r"^\s*\[ \]\s*(.*)",  # Markdown checkbox
    r"^\s*-\s*\[\s*\]\s*(.*)",  # Markdown checkbox variant
    # Goal-oriented
    r"(?:goal|objective|purpose):\s*(.*)",
    r"(?:need to|should|must|have to)\s+(.*)",
]


@dataclass
class ExtractedTask:
    """Extracted task model."""

    id: str
    title: str
    description: str = ""
    steps: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    session_id: Optional[str] = None
    parent_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "status": self.status.value,
            "priority": self.priority.value,
            "session_id": self.session_id,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedTask":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            steps=data.get("steps", []),
            status=TaskStatus(data.get("status", "pending")),
            priority=TaskPriority(data.get("priority", "medium")),
            session_id=data.get("session_id"),
            parent_id=data.get("parent_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            completed_at=data.get("completed_at"),
        )


class TaskExtractorDB:
    """SQLite-backed task extraction and tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            aizen_home = get_aizen_home()
            tasks_dir = aizen_home / "tasks"
            tasks_dir.mkdir(parents=True, exist_ok=True)
            db_path = tasks_dir / "tasks.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    steps TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    session_id TEXT,
                    parent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session ON tasks(session_id)
            """)
            conn.commit()

    def _row_to_task(self, row: tuple) -> ExtractedTask:
        return ExtractedTask(
            id=row[0],
            title=row[1],
            description=row[2],
            steps=json.loads(row[3]),
            status=TaskStatus(row[4]),
            priority=TaskPriority(row[5]),
            session_id=row[6],
            parent_id=row[7],
            created_at=row[8],
            updated_at=row[9],
            completed_at=row[10],
        )

    def create_task(
        self,
        title: str,
        description: str = "",
        steps: Optional[List[str]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        session_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> ExtractedTask:
        """Create a new task."""
        now = datetime.now().isoformat()
        task = ExtractedTask(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            steps=steps or [],
            priority=priority,
            session_id=session_id,
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO tasks 
                   (id, title, description, steps, status, priority, session_id, parent_id, created_at, updated_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.id,
                    task.title,
                    task.description,
                    json.dumps(task.steps),
                    task.status.value,
                    task.priority.value,
                    task.session_id,
                    task.parent_id,
                    task.created_at,
                    task.updated_at,
                    task.completed_at,
                ),
            )
            conn.commit()

        return task

    def get_task(self, task_id: str) -> Optional[ExtractedTask]:
        """Get a task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_task(tuple(row))
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        session_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> List[ExtractedTask]:
        """List tasks with optional filters."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if priority:
            query += " AND priority = ?"
            params.append(priority.value)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if parent_id is not None:
            if parent_id:
                query += " AND parent_id = ?"
                params.append(parent_id)
            else:
                query += " AND parent_id IS NULL"

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_task(tuple(row)) for row in cursor.fetchall()]

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[str]] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> Optional[ExtractedTask]:
        """Update a task."""
        task = self.get_task(task_id)
        if not task:
            return None

        now = datetime.now().isoformat()
        completed_at = task.completed_at

        # Set completed_at when status changes to success/failed/cancelled
        if status and status != task.status:
            if status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED):
                completed_at = now

        with sqlite3.connect(self.db_path) as conn:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if steps is not None:
                updates.append("steps = ?")
                params.append(json.dumps(steps))
            if status is not None:
                updates.append("status = ?")
                params.append(status.value)
            if priority is not None:
                updates.append("priority = ?")
                params.append(priority.value)
            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at)

            updates.append("updated_at = ?")
            params.append(now)
            params.append(task_id)

            conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task and all its subtasks."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete subtasks first
            conn.execute("DELETE FROM tasks WHERE parent_id = ?", (task_id,))
            # Delete the task
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            for status in TaskStatus:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = ?", (status.value,)
                )
                stats[status.value] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            stats["total"] = cursor.fetchone()[0]

            return stats


# Global instance
_db: Optional[TaskExtractorDB] = None


def get_db() -> TaskExtractorDB:
    global _db
    if _db is None:
        _db = TaskExtractorDB()
    return _db


# =============================================================================
# Intent Detection & Task Extraction
# =============================================================================


class TaskExtractor:
    """Extracts tasks from conversation messages."""

    def __init__(self, db: Optional[TaskExtractorDB] = None):
        self.db = db or get_db()
        self.patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in TASK_INTENT_PATTERNS
        ]

    def detect_task_intent(self, message: str) -> bool:
        """Detect if a message contains a task intent."""
        message = message.strip()
        for pattern in self.patterns:
            if pattern.search(message):
                return True
        return False

    def extract_task(
        self, message: str, session_id: Optional[str] = None
    ) -> Optional[ExtractedTask]:
        """Extract a task from a message."""
        message = message.strip()

        # Try each pattern
        for pattern in self.patterns:
            match = pattern.search(message)
            if match:
                # Extract title from match
                if match.groups():
                    title = match.group(1).strip()
                else:
                    title = message[:100].strip()

                # Clean up title
                title = re.sub(
                    r"^(please|can you|could you|i need to|want to)\s+",
                    "",
                    title,
                    flags=re.IGNORECASE,
                )
                title = title[:200]

                if len(title) > 10:  # Minimum meaningful title
                    return self.db.create_task(
                        title=title,
                        description=message[:500],
                        session_id=session_id,
                    )

        # Fallback: use first line as title
        first_line = message.split("\n")[0].strip()[:200]
        if len(first_line) > 10:
            return self.db.create_task(
                title=first_line,
                description=message[:500],
                session_id=session_id,
            )

        return None

    def extract_from_conversation(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> List[ExtractedTask]:
        """Extract tasks from a conversation history."""
        extracted = []

        for msg in messages:
            # Only process user messages
            role = msg.get("role", "")
            if role != "user":
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content if c.get("type") == "text"
                )

            if self.detect_task_intent(content):
                task = self.extract_task(content, session_id)
                if task:
                    extracted.append(task)

        return extracted


# =============================================================================
# Tool Functions
# =============================================================================


def task_extract(message: str, session_id: Optional[str] = None) -> str:
    """Extract task from a message."""
    extractor = TaskExtractor()
    task = extractor.extract_task(message, session_id)
    if not task:
        return json.dumps({"success": False, "error": "No task intent detected"})
    return json.dumps({"success": True, "task": task.to_dict()})


def task_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """List tasks with optional filters."""
    db = get_db()
    status_enum = TaskStatus(status) if status else None
    priority_enum = TaskPriority(priority) if priority else None

    tasks = db.list_tasks(
        status=status_enum,
        priority=priority_enum,
        session_id=session_id,
    )
    return json.dumps(
        {
            "success": True,
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks),
        }
    )


def task_get(task_id: str) -> str:
    """Get a task by ID."""
    db = get_db()
    task = db.get_task(task_id)
    if not task:
        return json.dumps({"success": False, "error": f"Task {task_id} not found"})
    return json.dumps({"success": True, "task": task.to_dict()})


def task_update(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """Update a task."""
    db = get_db()

    status_enum = TaskStatus(status) if status else None
    priority_enum = TaskPriority(priority) if priority else None

    task = db.update_task(
        task_id,
        title=title,
        description=description,
        status=status_enum,
        priority=priority_enum,
    )

    if not task:
        return json.dumps({"success": False, "error": f"Task {task_id} not found"})

    return json.dumps({"success": True, "task": task.to_dict()})


def task_delete(task_id: str) -> str:
    """Delete a task."""
    db = get_db()
    success = db.delete_task(task_id)
    return json.dumps({"success": success})


def task_stats() -> str:
    """Get task statistics."""
    db = get_db()
    stats = db.get_stats()
    return json.dumps({"success": True, "stats": stats})
