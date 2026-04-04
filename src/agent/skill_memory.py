"""
Skill Memory Layer - Learning system that stores and recalls skills based on successful task patterns.

Two-phase learning:
1. Distillation: Extract patterns from successful task executions
2. Skill Agent: Convert patterns into reusable skill YAMLs

Storage: SQLite in ~/.aizen/skills_memory/patterns.db
"""

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.aizen_constants import get_aizen_home


@dataclass
class TaskPattern:
    """A learned pattern from successful task execution."""

    id: str
    pattern_type: str  # "tool_sequence", "prompt_structure", "error_recovery"
    signature: str  # Hash of the pattern
    description: str
    steps: List[str] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    last_used: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "signature": self.signature,
            "description": self.description,
            "steps": self.steps,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SkillMemoryDB:
    """SQLite-backed skill memory."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            aizen_home = get_aizen_home()
            memory_dir = aizen_home / "skills_memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            db_path = memory_dir / "patterns.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    steps TEXT DEFAULT '[]',
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signature ON patterns(signature)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON patterns(pattern_type)
            """)

            # Table for generated skills from patterns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generated_skills (
                    id TEXT PRIMARY KEY,
                    pattern_id TEXT,
                    name TEXT NOT NULL,
                    content TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (pattern_id) REFERENCES patterns(id)
                )
            """)
            conn.commit()

    def _row_to_pattern(self, row: tuple) -> TaskPattern:
        return TaskPattern(
            id=row[0],
            pattern_type=row[1],
            signature=row[2],
            description=row[3],
            steps=json.loads(row[4]),
            success_count=row[5],
            failure_count=row[6],
            last_used=row[7] or "",
            created_at=row[8],
            updated_at=row[9],
        )

    def _compute_signature(self, pattern_type: str, steps: List[str]) -> str:
        """Compute a signature hash for a pattern."""
        content = f"{pattern_type}:{':'.join(steps)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def record_pattern(
        self,
        pattern_type: str,
        steps: List[str],
        description: str = "",
    ) -> TaskPattern:
        """Record a new pattern or update existing."""
        now = datetime.now().isoformat()
        signature = self._compute_signature(pattern_type, steps)

        # Check if pattern exists
        existing = self.find_by_signature(signature)
        if existing:
            # Update existing
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """UPDATE patterns 
                       SET success_count = success_count + 1, 
                           last_used = ?, updated_at = ?
                       WHERE signature = ?""",
                    (now, now, signature),
                )
                conn.commit()
            return self.find_by_signature(signature)

        # Create new
        pattern = TaskPattern(
            id=uuid.uuid4().hex[:8],
            pattern_type=pattern_type,
            signature=signature,
            description=description,
            steps=steps,
            success_count=1,
            last_used=now,
            created_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO patterns 
                   (id, pattern_type, signature, description, steps, success_count, failure_count, last_used, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pattern.id,
                    pattern.pattern_type,
                    pattern.signature,
                    pattern.description,
                    json.dumps(pattern.steps),
                    pattern.success_count,
                    pattern.failure_count,
                    pattern.last_used,
                    pattern.created_at,
                    pattern.updated_at,
                ),
            )
            conn.commit()

        return pattern

    def record_failure(self, signature: str) -> bool:
        """Record a failed attempt for a pattern."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """UPDATE patterns 
                   SET failure_count = failure_count + 1, 
                       updated_at = ?
                   WHERE signature = ?""",
                (now, signature),
            )
            conn.commit()
            return cursor.rowcount > 0

    def find_by_signature(self, signature: str) -> Optional[TaskPattern]:
        """Find a pattern by its signature."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM patterns WHERE signature = ?", (signature,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_pattern(tuple(row))
        return None

    def find_similar(
        self, steps: List[str], min_rate: float = 0.5
    ) -> List[TaskPattern]:
        """Find patterns similar to the given steps."""
        # Compute signature for the steps
        signature = self._compute_signature("tool_sequence", steps)

        # Find by signature prefix match
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM patterns 
                   WHERE signature LIKE ? AND success_count >= 2
                   ORDER BY success_count DESC
                   LIMIT 10""",
                (signature[:8] + "%",),
            )
            patterns = [self._row_to_pattern(tuple(row)) for row in cursor.fetchall()]

        # Filter by success rate
        return [p for p in patterns if p.success_rate >= min_rate]

    def list_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50,
    ) -> List[TaskPattern]:
        """List patterns with optional filters."""
        query = "SELECT * FROM patterns WHERE 1=1"
        params = []

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)

        if min_success_rate > 0:
            # Compute success rate in SQL
            query += " AND success_count * 1.0 / (success_count + failure_count) >= ?"
            params.append(min_success_rate)

        query += " ORDER BY success_count DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_pattern(tuple(row)) for row in cursor.fetchall()]

    def generate_skill(
        self,
        pattern_id: str,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate a skill from a pattern."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM patterns WHERE id = ?", (pattern_id,))
            row = cursor.fetchone()
            if not row:
                return None

            pattern = self._row_to_pattern(tuple(row))

            # Generate skill content
            skill_content = self._generate_skill_content(pattern)

            # Save generated skill
            now = datetime.now().isoformat()
            skill_id = uuid.uuid4().hex[:8]

            conn.execute(
                """INSERT INTO generated_skills (id, pattern_id, name, content, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (skill_id, pattern_id, name, skill_content, now),
            )
            conn.commit()

            return {
                "id": skill_id,
                "pattern_id": pattern_id,
                "name": name,
                "content": skill_content,
                "created_at": now,
            }

    def _generate_skill_content(self, pattern: TaskPattern) -> str:
        """Generate skill YAML content from a pattern."""
        lines = [
            f"# Skill: {pattern.description or 'Auto-generated Skill'}",
            f"# Pattern Type: {pattern.pattern_type}",
            f"# Success Rate: {pattern.success_rate:.1%}",
            f"# Times Used: {pattern.success_count}",
            "",
            "## Instructions",
            "",
        ]

        for i, step in enumerate(pattern.steps, 1):
            lines.append(f"{i}. {step}")

        lines.extend(
            [
                "",
                "## When to Use",
                "",
                f"Use this pattern when you need to: {pattern.description or 'accomplish the target task'}",
                "",
                "## Notes",
                "",
                f"- Pattern signature: `{pattern.signature}`",
                f"- Success rate: {pattern.success_rate:.1%}",
                f"- Last used: {pattern.last_used or 'Never'}",
            ]
        )

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get skill memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            # Pattern stats by type
            stats = {}
            cursor = conn.execute(
                """SELECT pattern_type, COUNT(*) as count, SUM(success_count) as successes
                   FROM patterns GROUP BY pattern_type"""
            )
            for row in cursor.fetchall():
                stats[row[0]] = {
                    "count": row[1],
                    "successes": row[2] or 0,
                }

            # Overall stats
            cursor = conn.execute("SELECT COUNT(*) FROM patterns")
            stats["total_patterns"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT SUM(success_count) FROM patterns")
            stats["total_successes"] = cursor.fetchone()[0] or 0

            cursor = conn.execute("SELECT COUNT(*) FROM generated_skills")
            stats["generated_skills"] = cursor.fetchone()[0]

            return stats


# Global instance
_db: Optional[SkillMemoryDB] = None


def get_db() -> SkillMemoryDB:
    global _db
    if _db is None:
        _db = SkillMemoryDB()
    return _db


# =============================================================================
# Tool Functions
# =============================================================================


def skill_memory_record(
    pattern_type: str,
    steps: List[str],
    description: str = "",
) -> str:
    """Record a successful task pattern."""
    db = get_db()
    pattern = db.record_pattern(pattern_type, steps, description)
    return json.dumps({"success": True, "pattern": pattern.to_dict()})


def skill_memory_record_failure(signature: str) -> str:
    """Record a failed attempt for a pattern."""
    db = get_db()
    success = db.record_failure(signature)
    return json.dumps({"success": success})


def skill_memory_find_similar(
    steps: List[str],
    min_rate: float = 0.5,
) -> str:
    """Find similar patterns."""
    db = get_db()
    patterns = db.find_similar(steps, min_rate)
    return json.dumps(
        {
            "success": True,
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns),
        }
    )


def skill_memory_list(
    pattern_type: Optional[str] = None,
    min_rate: float = 0.0,
    limit: int = 50,
) -> str:
    """List patterns."""
    db = get_db()
    patterns = db.list_patterns(pattern_type, min_rate, limit)
    return json.dumps(
        {
            "success": True,
            "patterns": [p.to_dict() for p in patterns],
            "count": len(patterns),
        }
    )


def skill_memory_generate(
    pattern_id: str,
    name: str,
) -> str:
    """Generate a skill from a pattern."""
    db = get_db()
    skill = db.generate_skill(pattern_id, name)
    if not skill:
        return json.dumps(
            {"success": False, "error": f"Pattern {pattern_id} not found"}
        )
    return json.dumps({"success": True, "skill": skill})


def skill_memory_stats() -> str:
    """Get skill memory statistics."""
    db = get_db()
    stats = db.get_stats()
    return json.dumps({"success": True, "stats": stats})
