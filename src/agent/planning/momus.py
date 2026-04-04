"""
Momus - Plan Review Agent.

Reviews execution plans for quality, completeness, and potential issues.
Suggests improvements and validates plan coherence.

This is part of the OMO-style planning system.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReviewSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    PRAISE = "praise"


class ReviewCategory(str, Enum):
    COMPLETENESS = "completeness"
    COHERENCE = "coherence"
    FEASIBILITY = "feasibility"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


@dataclass
class ReviewItem:
    """A single review item."""

    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    message: str
    suggestion: str = ""
    related_step_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "related_step_id": self.related_step_id,
        }


@dataclass
class ReviewResult:
    """Result of reviewing an execution plan."""

    plan_title: str
    items: List[ReviewItem] = field(default_factory=list)
    score: float = 0.0  # 0-100

    @property
    def errors(self) -> List[ReviewItem]:
        return [i for i in self.items if i.severity == ReviewSeverity.ERROR]

    @property
    def warnings(self) -> List[ReviewItem]:
        return [i for i in self.items if i.severity == ReviewSeverity.WARNING]

    @property
    def suggestions(self) -> List[ReviewItem]:
        return [i for i in self.items if i.severity == ReviewSeverity.SUGGESTION]

    @property
    def is_approved(self) -> bool:
        """Whether the plan is approved (no errors)."""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_title": self.plan_title,
            "items": [i.to_dict() for i in self.items],
            "score": self.score,
            "stats": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "suggestions": len(self.suggestions),
                "is_approved": self.is_approved,
            },
        }


class Momus:
    """
    Plan review agent that validates execution plans.

    Responsibilities:
    - Check plan completeness
    - Validate step coherence
    - Assess feasibility
    - Identify security/performance issues
    - Suggest improvements
    """

    def __init__(self):
        self.review_counter = 0
        self._base_score = 100

    def _next_id(self) -> str:
        self.review_counter += 1
        return f"review_{self.review_counter}"

    def _calculate_score(self, items: List[ReviewItem]) -> float:
        """Calculate plan score based on review items."""
        score = self._base_score

        for item in items:
            if item.severity == ReviewSeverity.ERROR:
                score -= 20
            elif item.severity == ReviewSeverity.WARNING:
                score -= 10
            elif item.severity == ReviewSeverity.SUGGESTION:
                score -= 5

        return max(0.0, min(100.0, score))

    def review_plan(
        self,
        plan_data: Dict[str, Any],
    ) -> ReviewResult:
        """Review an execution plan."""
        plan_title = plan_data.get("title", "Untitled Plan")
        steps = plan_data.get("steps", [])
        complexity = plan_data.get("complexity", "simple")

        items = []

        # Check plan metadata
        if not plan_title or plan_title == "Untitled Plan":
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.WARNING,
                    message="Plan lacks a descriptive title",
                    suggestion="Add a clear, descriptive title.",
                )
            )

        if not steps:
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.ERROR,
                    message="Plan has no steps",
                    suggestion="Break down the task into actionable steps.",
                )
            )

        # Check step coherence
        step_ids = set()
        for step in steps:
            step_id = step.get("id")
            if step_id:
                if step_id in step_ids:
                    items.append(
                        ReviewItem(
                            id=self._next_id(),
                            category=ReviewCategory.COHERENCE,
                            severity=ReviewSeverity.ERROR,
                            message=f"Duplicate step ID: {step_id}",
                            suggestion="Ensure each step has a unique ID.",
                            related_step_id=step_id,
                        )
                    )
                step_ids.add(step_id)

        # Check dependencies
        for step in steps:
            deps = step.get("dependencies", [])
            for dep_id in deps:
                if dep_id not in step_ids:
                    items.append(
                        ReviewItem(
                            id=self._next_id(),
                            category=ReviewCategory.COHERENCE,
                            severity=ReviewSeverity.ERROR,
                            message=f"Step depends on non-existent step: {dep_id}",
                            suggestion="Fix dependency references.",
                            related_step_id=step.get("id"),
                        )
                    )

        # Check for circular dependencies
        if self._has_circular_dependency(steps):
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.COHERENCE,
                    severity=ReviewSeverity.ERROR,
                    message="Circular dependency detected in steps",
                    suggestion="Remove circular references in dependencies.",
                )
            )

        # Check step order
        for i, step in enumerate(steps):
            deps = step.get("dependencies", [])
            if deps:
                # Find highest dependency index
                max_dep_idx = -1
                for dep_id in deps:
                    for j, s in enumerate(steps):
                        if s.get("id") == dep_id:
                            max_dep_idx = max(max_dep_idx, j)

                if max_dep_idx >= i:
                    items.append(
                        ReviewItem(
                            id=self._next_id(),
                            category=ReviewCategory.COHERENCE,
                            severity=ReviewSeverity.WARNING,
                            message=f"Step {i + 1} may execute before its dependency",
                            suggestion="Ensure dependencies are met before execution.",
                            related_step_id=step.get("id"),
                        )
                    )

        # Check for missing test step
        has_test_step = any("test" in s.get("description", "").lower() for s in steps)
        if not has_test_step and len(steps) > 2:
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.TESTING,
                    severity=ReviewSeverity.SUGGESTION,
                    message="No explicit testing step found",
                    suggestion="Consider adding a test/verification step.",
                )
            )

        # Check for missing verification step
        has_verify_step = any(
            "verif" in s.get("description", "").lower() for s in steps
        )
        if not has_verify_step:
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.SUGGESTION,
                    message="No explicit verification step found",
                    suggestion="Add a step to verify the result.",
                )
            )

        # Check complexity match
        estimated_time = plan_data.get("total_estimated_minutes", 0)
        if complexity == "epic" and estimated_time < 60:
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.FEASIBILITY,
                    severity=ReviewSeverity.WARNING,
                    message="Epic complexity but short estimated time",
                    suggestion="Epic tasks typically take 8+ hours. Review estimates.",
                )
            )

        # Security checks for certain task types
        plan_title_lower = plan_title.lower()
        if any(
            w in plan_title_lower for w in ["auth", "login", "password", "security"]
        ):
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.SECURITY,
                    severity=ReviewSeverity.WARNING,
                    message="Security-related task - ensure secure practices",
                    suggestion="Follow security best practices: no hardcoded credentials, proper validation.",
                )
            )

        # Performance checks
        if any(w in plan_title_lower for w in ["scale", "performance", "optimize"]):
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.PERFORMANCE,
                    severity=ReviewSeverity.WARNING,
                    message="Performance-related task - consider benchmarks",
                    suggestion="Define performance metrics and include testing.",
                )
            )

        # Calculate score
        score = self._calculate_score(items)

        # Add praise for good patterns
        if not items or all(
            i.severity in (ReviewSeverity.SUGGESTION, ReviewSeverity.PRAISE)
            for i in items
        ):
            items.append(
                ReviewItem(
                    id=self._next_id(),
                    category=ReviewCategory.COMPLETENESS,
                    severity=ReviewSeverity.PRAISE,
                    message="Plan looks well-structured!",
                    suggestion="Good job planning this task.",
                )
            )

        return ReviewResult(
            plan_title=plan_title,
            items=items,
            score=score,
        )

    def _has_circular_dependency(self, steps: List[Dict]) -> bool:
        """Check for circular dependencies using DFS."""
        step_map = {
            s.get("id"): s.get("dependencies", []) for s in steps if s.get("id")
        }

        def has_cycle(step_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            for dep in step_map.get(step_id, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(step_id)
            return False

        for step_id in step_map:
            if has_cycle(step_id, set(), set()):
                return True

        return False

    def to_markdown(self, review: ReviewResult) -> str:
        """Convert review to markdown."""
        lines = [
            f"# Plan Review: {review.plan_title}",
            "",
            f"**Score:** {review.score:.0f}/100",
            f"**Status:** {'✅ Approved' if review.is_approved else '❌ Needs Work'}",
            "",
        ]

        if not review.items:
            lines.append("No issues found.")
            return "\n".join(lines)

        # Group by severity
        for severity in [
            ReviewSeverity.ERROR,
            ReviewSeverity.WARNING,
            ReviewSeverity.SUGGESTION,
            ReviewSeverity.PRAISE,
        ]:
            severity_items = [i for i in review.items if i.severity == severity]
            if not severity_items:
                continue

            severity_icon = {
                ReviewSeverity.ERROR: "❌",
                ReviewSeverity.WARNING: "⚠️",
                ReviewSeverity.SUGGESTION: "💡",
                ReviewSeverity.PRAISE: "✅",
            }[severity]

            lines.append(f"## {severity_icon} {severity.value.upper()}")
            lines.append("")

            for item in severity_items:
                lines.append(f"**{item.category.value}:** {item.message}")
                if item.suggestion:
                    lines.append(f"   → {item.suggestion}")
                if item.related_step_id:
                    lines.append(f"   → Step: `{item.related_step_id}`")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# Tool Functions
# =============================================================================


def momus_review_plan(plan_json: str) -> str:
    """Review an execution plan."""
    import json

    try:
        plan_data = json.loads(plan_json)
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid plan JSON"})

    momus = Momus()
    review = momus.review_plan(plan_data)
    return json.dumps(
        {
            "success": True,
            "review": review.to_dict(),
        }
    )


def momus_to_markdown(plan_json: str) -> str:
    """Get plan review as markdown."""
    import json

    try:
        plan_data = json.loads(plan_json)
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid plan JSON"})

    momus = Momus()
    review = momus.review_plan(plan_data)
    markdown = momus.to_markdown(review)
    return json.dumps(
        {
            "success": True,
            "markdown": markdown,
        }
    )
