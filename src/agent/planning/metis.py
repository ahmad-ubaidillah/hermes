"""
Metis - Gap Analysis Agent.

Identifies missing information, ambiguities, and potential issues in task descriptions.
Provides feedback on what's unclear before execution begins.

This is part of the OMO-style planning system.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class GapSeverity(str, Enum):
    BLOCKER = "blocker"  # Cannot proceed without this
    CRITICAL = "critical"  # Should clarify before proceeding
    WARNING = "warning"  # May cause issues, worth noting
    INFO = "info"  # Nice to know, not urgent


class GapCategory(str, Enum):
    MISSING_CONTEXT = "missing_context"
    AMBIGUITY = "ambiguity"
    ASSUMPTION = "assumption"
    DEPENDENCY = "dependency"
    REQUIREMENT = "requirement"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"


@dataclass
class Gap:
    """A gap or issue identified in the task description."""

    id: str
    category: GapCategory
    severity: GapSeverity
    description: str
    question: str = ""  # Question to clarify
    suggestion: str = ""  # Suggested resolution
    related_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "question": self.question,
            "suggestion": self.suggestion,
            "related_keywords": self.related_keywords,
        }


@dataclass
class GapAnalysisResult:
    """Result of gap analysis on a task."""

    task_title: str
    task_description: str
    gaps: List[Gap] = field(default_factory=list)

    @property
    def blockers(self) -> List[Gap]:
        return [g for g in self.gaps if g.severity == GapSeverity.BLOCKER]

    @property
    def criticals(self) -> List[Gap]:
        return [g for g in self.gaps if g.severity == GapSeverity.CRITICAL]

    @property
    def can_proceed(self) -> bool:
        """Whether execution can proceed despite gaps."""
        return len(self.blockers) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_title": self.task_title,
            "task_description": self.task_description,
            "gaps": [g.to_dict() for g in self.gaps],
            "stats": {
                "total": len(self.gaps),
                "blockers": len(self.blockers),
                "criticals": len(self.criticals),
                "can_proceed": self.can_proceed,
            },
        }


class Metis:
    """
    Gap analysis agent that identifies missing information and ambiguities.

    Responsibilities:
    - Analyze task description for gaps
    - Identify missing context
    - Detect ambiguities
    - Find unstated dependencies
    - Highlight security/performance concerns
    """

    def __init__(self):
        self.gap_counter = 0

        # Patterns for detecting gaps
        self.context_patterns = {
            # Missing who/what/where/when/why
            r"\bimplement\b.*?\bwithout\b": GapCategory.MISSING_CONTEXT,
            r"\bfix\b.*?\bbut\b": GapCategory.MISSING_CONTEXT,
            r"\buse\b.*?\bfor\b": GapCategory.REQUIREMENT,
        }

        self.ambiguity_patterns = {
            # Vague terms
            r"\bgood\b": (
                GapSeverity.WARNING,
                "What does 'good' mean? Specify criteria.",
            ),
            r"\bbetter\b": (GapSeverity.WARNING, "Better than what? Define baseline."),
            r"\bfast\b": (GapSeverity.CRITICAL, "What performance target?"),
            r"\bsecure\b": (GapSeverity.CRITICAL, "What security requirements?"),
            r"\bsimple\b": (GapSeverity.INFO, "Define simplicity criteria."),
            r"\boptimize\b": (GapSeverity.CRITICAL, "What to optimize for?"),
            r"\bquickly?\b": (GapSeverity.WARNING, "What's the deadline?"),
            r"\bmodern\b": (GapSeverity.INFO, "Define modern technology stack."),
            r"\breliable\b": (GapSeverity.WARNING, "What reliability metrics?"),
        }

        self.assumption_patterns = {
            # Assumed things
            r"\bas expected\b": (GapSeverity.CRITICAL, "What's the expected behavior?"),
            r"\bcorrectly\b": (GapSeverity.WARNING, "Define correct behavior."),
            r"\bobviously\b": (GapSeverity.INFO, "Nothing is obvious. Spell it out."),
            r"\bclearly\b": (GapSeverity.INFO, "Make it explicit."),
        }

        self.security_patterns = {
            # Security concerns
            r"\bpassword\b": (GapSeverity.BLOCKER, "How will credentials be handled?"),
            r"\bsecret\b": (GapSeverity.BLOCKER, "How will secrets be stored?"),
            r"\bapi[_-]?key\b": (GapSeverity.BLOCKER, "API key security?"),
            r"\btoken\b": (GapSeverity.CRITICAL, "Token storage and expiration?"),
            r"\bencrypt\b": (GapSeverity.CRITICAL, "Encryption requirements?"),
            r"\buser[_-]?input\b": (GapSeverity.CRITICAL, "Input validation plan?"),
            r"\bsql\b.*?\binject\b": (GapSeverity.BLOCKER, "SQL injection prevention?"),
        }

        self.performance_patterns = {
            # Performance concerns
            r"\blarge\b.*?\bdata\b": (
                GapSeverity.CRITICAL,
                "Data volume and handling?",
            ),
            r"\bmany\b.*?\busers?\b": (
                GapSeverity.CRITICAL,
                "Concurrency requirements?",
            ),
            r"\bcomplex\b.*?\bquery\b": (GapSeverity.WARNING, "Query optimization?"),
            r"\bcache\b": (GapSeverity.WARNING, "Cache strategy?"),
            r"\basync\b": (GapSeverity.WARNING, "Async error handling?"),
        }

    def _next_id(self) -> str:
        self.gap_counter += 1
        return f"gap_{self.gap_counter}"

    def analyze(
        self,
        task_title: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GapAnalysisResult:
        """Analyze a task description for gaps."""
        text = f"{task_title} {task_description}".lower()
        gaps = []

        # Check for ambiguity patterns
        for pattern, (severity, question) in self.ambiguity_patterns.items():
            if re.search(pattern, text):
                gaps.append(
                    Gap(
                        id=self._next_id(),
                        category=GapCategory.AMBIGUITY,
                        severity=severity,
                        description=f"Vague term detected: '{pattern}'",
                        question=question,
                        suggestion="Provide specific criteria or metrics.",
                        related_keywords=[pattern],
                    )
                )

        # Check for assumption patterns
        for pattern, (severity, question) in self.assumption_patterns.items():
            if re.search(pattern, text):
                gaps.append(
                    Gap(
                        id=self._next_id(),
                        category=GapCategory.ASSUMPTION,
                        severity=severity,
                        description=f"Implicit assumption: '{pattern}'",
                        question=question,
                        suggestion="Make assumptions explicit.",
                        related_keywords=[pattern],
                    )
                )

        # Check for security patterns
        for pattern, (severity, question) in self.security_patterns.items():
            if re.search(pattern, text):
                gaps.append(
                    Gap(
                        id=self._next_id(),
                        category=GapCategory.SECURITY,
                        severity=severity,
                        description=f"Security consideration: '{pattern}'",
                        question=question,
                        suggestion="Address security requirement explicitly.",
                        related_keywords=[pattern],
                    )
                )

        # Check for performance patterns
        for pattern, (severity, question) in self.performance_patterns.items():
            if re.search(pattern, text):
                gaps.append(
                    Gap(
                        id=self._next_id(),
                        category=GapCategory.PERFORMANCE,
                        severity=severity,
                        description=f"Performance consideration: '{pattern}'",
                        question=question,
                        suggestion="Define performance requirements.",
                        related_keywords=[pattern],
                    )
                )

        # Check for missing context
        if len(task_description) < 50:
            gaps.append(
                Gap(
                    id=self._next_id(),
                    category=GapCategory.MISSING_CONTEXT,
                    severity=GapSeverity.CRITICAL,
                    description="Task description is very brief",
                    question="Provide more details about the task?",
                    suggestion="Include purpose, expected output, constraints.",
                )
            )

        # Check for missing dependencies
        if "integrate" in text or "connect" in text:
            gaps.append(
                Gap(
                    id=self._next_id(),
                    category=GapCategory.DEPENDENCY,
                    severity=GapSeverity.CRITICAL,
                    description="Integration mentioned but external service not specified",
                    question="Which external service/API to integrate with?",
                    suggestion="Specify the integration target.",
                )
            )

        # Check for testing gaps
        if "implement" in text or "add" in text or "create" in text:
            gaps.append(
                Gap(
                    id=self._next_id(),
                    category=GapCategory.TESTING,
                    severity=GapSeverity.WARNING,
                    description="Implementation without test specification",
                    question="What tests should pass?",
                    suggestion="Define acceptance criteria.",
                )
            )

        # Sort by severity
        severity_order = {
            GapSeverity.BLOCKER: 0,
            GapSeverity.CRITICAL: 1,
            GapSeverity.WARNING: 2,
            GapSeverity.INFO: 3,
        }
        gaps.sort(key=lambda g: severity_order[g.severity])

        return GapAnalysisResult(
            task_title=task_title,
            task_description=task_description,
            gaps=gaps,
        )

    def to_markdown(self, analysis: GapAnalysisResult) -> str:
        """Convert analysis to markdown."""
        lines = [
            f"# Gap Analysis: {analysis.task_title}",
            "",
        ]

        if not analysis.gaps:
            lines.append("✅ No significant gaps detected.")
            return "\n".join(lines)

        lines.append(f"**Can Proceed:** {'Yes' if analysis.can_proceed else 'No'}")
        lines.append("")

        # Group by severity
        for severity in [
            GapSeverity.BLOCKER,
            GapSeverity.CRITICAL,
            GapSeverity.WARNING,
            GapSeverity.INFO,
        ]:
            severity_gaps = [g for g in analysis.gaps if g.severity == severity]
            if not severity_gaps:
                continue

            severity_icon = {
                GapSeverity.BLOCKER: "⛔",
                GapSeverity.CRITICAL: "🔴",
                GapSeverity.WARNING: "🟡",
                GapSeverity.INFO: "ℹ️",
            }[severity]

            lines.append(f"## {severity_icon} {severity.value.upper()}")
            lines.append("")

            for gap in severity_gaps:
                lines.append(f"### {gap.category.value}")
                lines.append(f"**Description:** {gap.description}")
                if gap.question:
                    lines.append(f"**Question:** {gap.question}")
                if gap.suggestion:
                    lines.append(f"**Suggestion:** {gap.suggestion}")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# Tool Functions
# =============================================================================


def metis_analyze(
    task_title: str,
    task_description: str = "",
) -> str:
    """Analyze a task for gaps."""
    metis = Metis()
    analysis = metis.analyze(task_title, task_description)
    return json.dumps(
        {
            "success": True,
            "analysis": analysis.to_dict(),
        }
    )


def metis_to_markdown(
    task_title: str,
    task_description: str = "",
) -> str:
    """Get gap analysis as markdown."""
    metis = Metis()
    analysis = metis.analyze(task_title, task_description)
    markdown = metis.to_markdown(analysis)
    return json.dumps(
        {
            "success": True,
            "markdown": markdown,
        }
    )
