"""
Issue/Kanban System - Issue tracking with status workflow.

Issue model:
- title, description, status, priority, tags
- Status workflow: TODO → IN_PROGRESS → DONE, with BLOCKED transition
- Sub-issues (parent/child relationships)
- Created, updated timestamps

Storage: SQLite in ~/.aizen/kanban/issues.db
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.aizen_constants import get_aizen_home


class IssueStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class IssuePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Valid status transitions
VALID_TRANSITIONS = {
    IssueStatus.TODO: [IssueStatus.IN_PROGRESS, IssueStatus.BLOCKED],
    IssueStatus.IN_PROGRESS: [IssueStatus.DONE, IssueStatus.TODO, IssueStatus.BLOCKED],
    IssueStatus.DONE: [IssueStatus.TODO],  # Can reopen
    IssueStatus.BLOCKED: [IssueStatus.TODO, IssueStatus.IN_PROGRESS],
}


@dataclass
class Issue:
    """Issue model with status workflow."""

    id: str
    title: str
    description: str = ""
    status: IssueStatus = IssueStatus.TODO
    priority: IssuePriority = IssuePriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None  # For sub-issues
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=IssueStatus(data.get("status", "TODO")),
            priority=IssuePriority(data.get("priority", "medium")),
            tags=data.get("tags", []),
            parent_id=data.get("parent_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class KanbanDB:
    """SQLite-backed issue tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            aizen_home = get_aizen_home()
            kanban_dir = aizen_home / "kanban"
            kanban_dir.mkdir(parents=True, exist_ok=True)
            db_path = kanban_dir / "issues.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'TODO',
                    priority TEXT DEFAULT 'medium',
                    tags TEXT DEFAULT '[]',
                    parent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (parent_id) REFERENCES issues(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON issues(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_parent ON issues(parent_id)
            """)
            conn.commit()

    def _row_to_issue(self, row: tuple) -> Issue:
        return Issue(
            id=row[0],
            title=row[1],
            description=row[2],
            status=IssueStatus(row[3]),
            priority=IssuePriority(row[4]),
            tags=json.loads(row[5]),
            parent_id=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: IssuePriority = IssuePriority.MEDIUM,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
    ) -> Issue:
        """Create a new issue."""
        now = datetime.now().isoformat()
        issue = Issue(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO issues 
                   (id, title, description, status, priority, tags, parent_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    issue.id,
                    issue.title,
                    issue.description,
                    issue.status.value,
                    issue.priority.value,
                    json.dumps(issue.tags),
                    issue.parent_id,
                    issue.created_at,
                    issue.updated_at,
                ),
            )
            conn.commit()

        return issue

    def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Get an issue by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_issue(tuple(row))
        return None

    def list_issues(
        self,
        status: Optional[IssueStatus] = None,
        priority: Optional[IssuePriority] = None,
        tag: Optional[str] = None,
        parent_id: Optional[str] = None,
        include_subissues: bool = True,
    ) -> List[Issue]:
        """List issues with optional filters."""
        query = "SELECT * FROM issues WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if priority:
            query += " AND priority = ?"
            params.append(priority.value)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        if parent_id is not None:
            if parent_id:
                query += " AND parent_id = ?"
                params.append(parent_id)
            else:
                query += " AND parent_id IS NULL"
        elif not include_subissues:
            query += " AND parent_id IS NULL"

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_issue(tuple(row)) for row in cursor.fetchall()]

    def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[IssueStatus] = None,
        priority: Optional[IssuePriority] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Issue]:
        """Update an issue. Validates status transitions."""
        issue = self.get_issue(issue_id)
        if not issue:
            return None

        # Validate status transition
        if status and status != issue.status:
            if status not in VALID_TRANSITIONS.get(issue.status, []):
                raise ValueError(
                    f"Invalid transition from {issue.status.value} to {status.value}"
                )

        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if status is not None:
                updates.append("status = ?")
                params.append(status.value)
            if priority is not None:
                updates.append("priority = ?")
                params.append(priority.value)
            if tags is not None:
                updates.append("tags = ?")
                params.append(json.dumps(tags))

            updates.append("updated_at = ?")
            params.append(now)
            params.append(issue_id)

            conn.execute(
                f"UPDATE issues SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

        return self.get_issue(issue_id)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue and all its sub-issues."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete sub-issues first
            conn.execute("DELETE FROM issues WHERE parent_id = ?", (issue_id,))
            # Delete the issue
            cursor = conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_subissues(self, parent_id: str) -> List[Issue]:
        """Get all sub-issues for a parent issue."""
        return self.list_issues(parent_id=parent_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get kanban statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            for status in IssueStatus:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM issues WHERE status = ?", (status.value,)
                )
                stats[status.value] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM issues")
            stats["total"] = cursor.fetchone()[0]

            return stats


# Global instance
_db: Optional[KanbanDB] = None


def get_db() -> KanbanDB:
    global _db
    if _db is None:
        _db = KanbanDB()
    return _db


# =============================================================================
# Tool Functions (for MCP integration)
# =============================================================================


def kanban_create(
    title: str,
    description: str = "",
    priority: str = "medium",
    tags: Optional[List[str]] = None,
) -> str:
    """Create a new issue."""
    db = get_db()
    priority_enum = IssuePriority(priority.lower())
    issue = db.create_issue(
        title=title,
        description=description,
        priority=priority_enum,
        tags=tags,
    )
    return json.dumps({"success": True, "issue": issue.to_dict()})


def kanban_get(issue_id: str) -> str:
    """Get an issue by ID."""
    db = get_db()
    issue = db.get_issue(issue_id)
    if not issue:
        return json.dumps({"success": False, "error": f"Issue {issue_id} not found"})
    return json.dumps({"success": True, "issue": issue.to_dict()})


def kanban_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    include_subissues: bool = True,
) -> str:
    """List issues with optional filters."""
    db = get_db()
    status_enum = IssueStatus(status) if status else None
    priority_enum = IssuePriority(priority) if priority else None

    issues = db.list_issues(
        status=status_enum,
        priority=priority_enum,
        tag=tag,
        include_subissues=include_subissues,
    )
    return json.dumps(
        {
            "success": True,
            "issues": [i.to_dict() for i in issues],
            "count": len(issues),
        }
    )


def kanban_update(
    issue_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """Update an issue."""
    db = get_db()

    try:
        status_enum = IssueStatus(status) if status else None
        priority_enum = IssuePriority(priority) if priority else None

        issue = db.update_issue(
            issue_id,
            title=title,
            description=description,
            status=status_enum,
            priority=priority_enum,
            tags=tags,
        )

        if not issue:
            return json.dumps(
                {"success": False, "error": f"Issue {issue_id} not found"}
            )

        return json.dumps({"success": True, "issue": issue.to_dict()})
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})


def kanban_delete(issue_id: str) -> str:
    """Delete an issue."""
    db = get_db()
    success = db.delete_issue(issue_id)
    return json.dumps({"success": success})


def kanban_subissue(
    parent_id: str,
    title: str,
    description: str = "",
    priority: str = "medium",
) -> str:
    """Create a sub-issue under a parent issue."""
    db = get_db()
    parent = db.get_issue(parent_id)
    if not parent:
        return json.dumps(
            {"success": False, "error": f"Parent issue {parent_id} not found"}
        )

    priority_enum = IssuePriority(priority.lower())
    issue = db.create_issue(
        title=title,
        description=description,
        priority=priority_enum,
        parent_id=parent_id,
    )
    return json.dumps({"success": True, "issue": issue.to_dict()})


def kanban_stats() -> str:
    """Get kanban statistics."""
    db = get_db()
    stats = db.get_stats()
    return json.dumps({"success": True, "stats": stats})
