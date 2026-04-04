"""
Wisdom Accumulation - Extracts and stores lessons learned from completed tasks.

Analyzes completed tasks, extracts valuable lessons, categorizes them,
stores in a database, and provides context injection for future similar tasks.

Storage: SQLite in ~/.aizen/wisdom/lessons.db
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


class LessonCategory(str, Enum):
    GENERAL = "general"
    CODE_PATTERNS = "code_patterns"
    ERROR_RECOVERY = "error_recovery"
    TOOL_USAGE = "tool_usage"
    PROMPT_ENGINEERING = "prompt_engineering"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class Lesson:
    """A learned lesson from task execution."""

    id: str
    title: str
    content: str
    category: LessonCategory = LessonCategory.GENERAL
    task_type: str = ""  # Type of task this lesson applies to
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    effectiveness_score: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "task_type": self.task_type,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "effectiveness_score": self.effectiveness_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            category=LessonCategory(data.get("category", "general")),
            task_type=data.get("task_type", ""),
            tags=data.get("tags", []),
            usage_count=data.get("usage_count", 0),
            effectiveness_score=data.get("effectiveness_score", 0.0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# Patterns for extracting lessons from conversations
LESSON_EXTRACTION_PATTERNS = {
    # Error recovery lessons
    r"(?:error|exception|failed).*?([Ff]ix| resolution| workaround).*?:\s*(.+?)(?:\n\n|\n##|\Z)": LessonCategory.ERROR_RECOVERY,
    r"(?:solved|fixed|resolved).*?by (?:using|with) (.+?)(?:\n\n|\n##|\Z)": LessonCategory.ERROR_RECOVERY,
    # Tool usage lessons
    r"(?:better|prefer|use) (?:tool|function) (.+?) (?:instead|for) (.+?)(?:\n\n|\n##|\Z)": LessonCategory.TOOL_USAGE,
    r"(?:use|invoke|call) (.+?) (?:to|for) (.+?)(?:\n\n|\n##|\Z)": LessonCategory.TOOL_USAGE,
    # Code patterns
    r"(?:pattern|idiom|best practice):\s*(.+?)(?:\n\n|\n##|\Z)": LessonCategory.CODE_PATTERNS,
    r"(?:recommended|suggested) (?:approach|way|pattern):\s*(.+?)(?:\n\n|\n##|\Z)": LessonCategory.CODE_PATTERNS,
    # Architecture lessons
    r"(?:architecture|design|structure):\s*(.+?)(?:\n\n|\n##|\Z)": LessonCategory.ARCHITECTURE,
    # Testing lessons
    r"(?:test|verify).*?should (?:be|do)\s*(.+?)(?:\n\n|\n##|\Z)": LessonCategory.TESTING,
}


class WisdomDB:
    """SQLite-backed wisdom/lesson storage."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            aizen_home = get_aizen_home()
            wisdom_dir = aizen_home / "wisdom"
            wisdom_dir.mkdir(parents=True, exist_ok=True)
            db_path = wisdom_dir / "lessons.db"
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    task_type TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    usage_count INTEGER DEFAULT 0,
                    effectiveness_score REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category ON lessons(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_type ON lessons(task_type)
            """)

            # Table for tracking lesson usage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lesson_usage (
                    id TEXT PRIMARY KEY,
                    lesson_id TEXT NOT NULL,
                    context TEXT,
                    helpful BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
                )
            """)
            conn.commit()

    def _row_to_lesson(self, row: tuple) -> Lesson:
        return Lesson(
            id=row[0],
            title=row[1],
            content=row[2],
            category=LessonCategory(row[3]),
            task_type=row[4],
            tags=json.loads(row[5]),
            usage_count=row[6],
            effectiveness_score=row[7],
            created_at=row[8],
            updated_at=row[9],
        )

    def add_lesson(
        self,
        title: str,
        content: str,
        category: LessonCategory = LessonCategory.GENERAL,
        task_type: str = "",
        tags: Optional[List[str]] = None,
    ) -> Lesson:
        """Add a new lesson."""
        now = datetime.now().isoformat()
        lesson = Lesson(
            id=uuid.uuid4().hex[:8],
            title=title,
            content=content,
            category=category,
            task_type=task_type,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO lessons 
                   (id, title, content, category, task_type, tags, usage_count, effectiveness_score, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    lesson.id,
                    lesson.title,
                    lesson.content,
                    lesson.category.value,
                    lesson.task_type,
                    json.dumps(lesson.tags),
                    lesson.usage_count,
                    lesson.effectiveness_score,
                    lesson.created_at,
                    lesson.updated_at,
                ),
            )
            conn.commit()

        return lesson

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_lesson(tuple(row))
        return None

    def find_relevant(
        self,
        task_type: str = "",
        category: Optional[LessonCategory] = None,
        query: str = "",
        limit: int = 5,
    ) -> List[Lesson]:
        """Find relevant lessons for a task."""
        query_sql = "SELECT * FROM lessons WHERE 1=1"
        params = []

        if task_type:
            query_sql += " AND (task_type = ? OR task_type = '')"
            params.append(task_type)

        if category:
            query_sql += " AND category = ?"
            params.append(category.value)

        if query:
            query_sql += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        query_sql += " ORDER BY usage_count DESC, effectiveness_score DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query_sql, params)
            return [self._row_to_lesson(tuple(row)) for row in cursor.fetchall()]

    def list_lessons(
        self,
        category: Optional[LessonCategory] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Lesson]:
        """List lessons with optional filters."""
        query = "SELECT * FROM lessons WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY usage_count DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_lesson(tuple(row)) for row in cursor.fetchall()]

    def record_usage(
        self,
        lesson_id: str,
        context: str = "",
        helpful: bool = True,
    ) -> bool:
        """Record that a lesson was used."""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Update lesson usage count
            conn.execute(
                "UPDATE lessons SET usage_count = usage_count + 1, updated_at = ? WHERE id = ?",
                (now, lesson_id),
            )

            # Record the usage event
            usage_id = uuid.uuid4().hex[:8]
            conn.execute(
                """INSERT INTO lesson_usage (id, lesson_id, context, helpful, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (usage_id, lesson_id, context, helpful, now),
            )
            conn.commit()

        return True

    def update_effectiveness(
        self,
        lesson_id: str,
        helpful: bool,
    ) -> Optional[Lesson]:
        """Update effectiveness score based on user feedback."""
        # Calculate new score: simple moving average
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return None

        # Simple update: if helpful, increase score; if not, decrease
        delta = 0.1 if helpful else -0.1
        new_score = max(0.0, min(1.0, lesson.effectiveness_score + delta))

        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE lessons SET effectiveness_score = ?, updated_at = ? WHERE id = ?",
                (new_score, now, lesson_id),
            )
            conn.commit()

        return self.get_lesson(lesson_id)

    def delete_lesson(self, lesson_id: str) -> bool:
        """Delete a lesson."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get wisdom statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Lessons by category
            for cat in LessonCategory:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM lessons WHERE category = ?", (cat.value,)
                )
                stats[cat.value] = cursor.fetchone()[0]

            # Overall stats
            cursor = conn.execute("SELECT COUNT(*) FROM lessons")
            stats["total_lessons"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT SUM(usage_count) FROM lessons")
            stats["total_usages"] = cursor.fetchone()[0] or 0

            cursor = conn.execute(
                "SELECT AVG(effectiveness_score) FROM lessons WHERE usage_count > 0"
            )
            stats["avg_effectiveness"] = cursor.fetchone()[0] or 0.0

            return stats


# Global instance
_db: Optional[WisdomDB] = None


def get_db() -> WisdomDB:
    global _db
    if _db is None:
        _db = WisdomDB()
    return _db


# =============================================================================
# Lesson Extraction
# =============================================================================


class WisdomExtractor:
    """Extracts lessons from task completions."""

    def __init__(self, db: Optional[WisdomDB] = None):
        self.db = db or get_db()
        self.patterns = {
            re.compile(k, re.IGNORECASE | re.DOTALL): v
            for k, v in LESSON_EXTRACTION_PATTERNS.items()
        }

    def extract_from_completion(
        self,
        task_result: str,
        task_type: str = "",
    ) -> List[Lesson]:
        """Extract lessons from a task completion."""
        extracted = []

        for pattern, category in self.patterns.items():
            matches = pattern.finditer(task_result)
            for match in matches:
                if match.groups():
                    content = match.group(1).strip()
                    if len(content) > 20:  # Minimum meaningful content
                        title = content[:100]
                        lesson = self.db.add_lesson(
                            title=title,
                            content=content[:500],
                            category=category,
                            task_type=task_type,
                        )
                        extracted.append(lesson)

        return extracted

    def inject_context(
        self,
        task_type: str = "",
        query: str = "",
    ) -> str:
        """Get contextual wisdom for a task."""
        lessons = self.db.find_relevant(
            task_type=task_type,
            query=query,
            limit=3,
        )

        if not lessons:
            return ""

        lines = [
            "## Relevant Wisdom from Past Tasks",
            "",
        ]

        for lesson in lessons:
            lines.append(f"### {lesson.title}")
            lines.append(lesson.content)
            lines.append("")

        # Record usage
        for lesson in lessons:
            self.db.record_usage(lesson.id, context=f"task_type={task_type}")

        return "\n".join(lines)


# =============================================================================
# Tool Functions
# =============================================================================


def wisdom_add(
    title: str,
    content: str,
    category: str = "general",
    task_type: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """Add a new lesson."""
    db = get_db()
    try:
        cat = LessonCategory(category.lower())
    except ValueError:
        cat = LessonCategory.GENERAL

    lesson = db.add_lesson(
        title=title,
        content=content,
        category=cat,
        task_type=task_type,
        tags=tags,
    )
    return json.dumps({"success": True, "lesson": lesson.to_dict()})


def wisdom_find(
    task_type: str = "",
    category: Optional[str] = None,
    query: str = "",
    limit: int = 5,
) -> str:
    """Find relevant lessons."""
    db = get_db()
    cat = LessonCategory(category) if category else None

    lessons = db.find_relevant(
        task_type=task_type,
        category=cat,
        query=query,
        limit=limit,
    )
    return json.dumps(
        {
            "success": True,
            "lessons": [l.to_dict() for l in lessons],
            "count": len(lessons),
        }
    )


def wisdom_list(
    category: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 50,
) -> str:
    """List lessons."""
    db = get_db()
    cat = LessonCategory(category) if category else None

    lessons = db.list_lessons(
        category=cat,
        task_type=task_type,
        limit=limit,
    )
    return json.dumps(
        {
            "success": True,
            "lessons": [l.to_dict() for l in lessons],
            "count": len(lessons),
        }
    )


def wisdom_record_usage(lesson_id: str, context: str = "") -> str:
    """Record lesson usage."""
    db = get_db()
    success = db.record_usage(lesson_id, context)
    return json.dumps({"success": success})


def wisdom_feedback(lesson_id: str, helpful: bool) -> str:
    """Submit feedback on lesson effectiveness."""
    db = get_db()
    lesson = db.update_effectiveness(lesson_id, helpful)
    if not lesson:
        return json.dumps({"success": False, "error": f"Lesson {lesson_id} not found"})
    return json.dumps({"success": True, "lesson": lesson.to_dict()})


def wisdom_delete(lesson_id: str) -> str:
    """Delete a lesson."""
    db = get_db()
    success = db.delete_lesson(lesson_id)
    return json.dumps({"success": success})


def wisdom_stats() -> str:
    """Get wisdom statistics."""
    db = get_db()
    stats = db.get_stats()
    return json.dumps({"success": True, "stats": stats})


def wisdom_inject(task_type: str = "", query: str = "") -> str:
    """Get contextual wisdom injection for a task."""
    extractor = WisdomExtractor()
    context = extractor.inject_context(task_type, query)
    return json.dumps(
        {
            "success": True,
            "injection": context,
            "has_content": bool(context),
        }
    )
