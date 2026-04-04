"""
Prometheus - Task Planning Agent.

Breaks down complex tasks into actionable steps with clear dependencies,
estimates complexity, and creates execution plans.

This is part of the OMO-style planning system.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"  # < 10 min, single step
    SIMPLE = "simple"  # 10-30 min, few steps
    MODERATE = "moderate"  # 30-120 min, multiple steps
    COMPLEX = "complex"  # 2-8 hours, many steps, some dependencies
    EPIC = "epic"  # 8+ hours, complex dependencies, multiple sub-tasks


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in the execution plan."""

    id: str
    description: str
    status: StepStatus = StepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    estimated_minutes: int = 0
    actual_minutes: Optional[int] = None
    notes: str = ""
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "notes": self.notes,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan for a task."""

    id: str
    title: str
    description: str
    complexity: TaskComplexity
    steps: List[PlanStep] = field(default_factory=list)
    total_estimated_minutes: int = 0
    prerequisites: List[str] = field(default_factory=list)  # External deps
    created_at: str = ""
    updated_at: str = ""

    @property
    def pending_steps(self) -> List[PlanStep]:
        return [s for s in self.steps if s.status == StepStatus.PENDING]

    @property
    def completed_steps(self) -> List[PlanStep]:
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    @property
    def blocked_steps(self) -> List[PlanStep]:
        return [s for s in self.steps if s.status == StepStatus.BLOCKED]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "complexity": self.complexity.value,
            "steps": [s.to_dict() for s in self.steps],
            "total_estimated_minutes": self.total_estimated_minutes,
            "prerequisites": self.prerequisites,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stats": {
                "pending": len(self.pending_steps),
                "completed": len(self.completed_steps),
                "blocked": len(self.blocked_steps),
            },
        }


class Prometheus:
    """
    Task planning agent that breaks down complex tasks.

    Responsibilities:
    - Analyze task description
    - Break into sequential steps with dependencies
    - Estimate complexity and time
    - Identify prerequisites
    """

    def __init__(self):
        self.task_keywords = {
            "create": ["implement", "build", "add", "make"],
            "modify": ["update", "change", "refactor", "improve"],
            "fix": ["fix", "repair", "resolve", "debug"],
            "analyze": ["analyze", "review", "inspect", "check"],
            "configure": ["setup", "configure", "install", "deploy"],
        }

    def analyze_complexity(
        self,
        title: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskComplexity:
        """Analyze task to determine complexity."""
        text = f"{title} {description}".lower()

        # Epic indicators
        epic_indicators = [
            "architecture",
            "redesign",
            "migrate",
            "rebuild",
            "multiple services",
            "distributed",
            "complex",
            "research",
            "investigate",
        ]
        if any(ind in text for ind in epic_indicators):
            return TaskComplexity.EPIC

        # Complex indicators
        complex_indicators = [
            "refactor",
            "optimize",
            "scale",
            "integrate",
            "multiple",
            "several",
            "various",
        ]
        if any(ind in text for ind in complex_indicators):
            return TaskComplexity.COMPLEX

        # Moderate indicators
        moderate_indicators = [
            "feature",
            "enhancement",
            "improve",
            "add support",
            "handle errors",
            "validation",
        ]
        if any(ind in text for ind in moderate_indicators):
            return TaskComplexity.MODERATE

        # Simple indicators
        simple_indicators = [
            "fix typo",
            "update comment",
            "rename",
            "small fix",
            "simple",
            "quick",
        ]
        if any(ind in text for ind in simple_indicators):
            return TaskComplexity.SIMPLE

        return TaskComplexity.TRIVIAL

    def _estimate_step_time(self, step_description: str) -> int:
        """Estimate time for a single step in minutes."""
        text = step_description.lower()

        # High effort indicators
        if any(w in text for w in ["research", "analyze", "investigate", "design"]):
            return 30
        if any(w in text for w in ["implement", "create", "build", "write"]):
            return 20
        if any(w in text for w in ["test", "verify", "check"]):
            return 15
        if any(w in text for w in ["fix", "update", "modify", "change"]):
            return 10
        if any(w in text for w in ["read", "review", "inspect"]):
            return 5

        return 10  # Default

    def create_plan(
        self,
        title: str,
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Create an execution plan from a task description."""
        now = datetime.now().isoformat()

        # Analyze complexity
        complexity = self.analyze_complexity(title, description, context)

        # Generate steps based on complexity
        steps = self._generate_steps(title, description, complexity)

        # Calculate total time
        total_time = sum(s.estimated_minutes for s in steps)

        plan = ExecutionPlan(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            complexity=complexity,
            steps=steps,
            total_estimated_minutes=total_time,
            created_at=now,
            updated_at=now,
        )

        return plan

    def _generate_steps(
        self,
        title: str,
        description: str,
        complexity: TaskComplexity,
    ) -> List[PlanStep]:
        """Generate steps based on task type and complexity."""
        steps = []
        text = f"{title} {description}".lower()

        # Generic workflow for most tasks
        step_templates = []

        # Analyze task type
        if any(w in text for w in ["fix", "bug", "error", "issue"]):
            step_templates = [
                ("Investigate and reproduce the issue", 15),
                ("Identify root cause", 10),
                ("Implement fix", 20),
                ("Test the fix", 10),
                ("Verify no regressions", 5),
            ]
        elif any(w in text for w in ["create", "implement", "build", "add"]):
            step_templates = [
                ("Understand requirements and scope", 10),
                ("Design solution approach", 15),
                ("Implement the feature", 30),
                ("Add tests", 15),
                ("Test thoroughly", 10),
            ]
        elif any(w in text for w in ["refactor", "improve", "optimize"]):
            step_templates = [
                ("Analyze current implementation", 10),
                ("Identify improvement areas", 10),
                ("Implement changes", 20),
                ("Verify correctness", 10),
            ]
        elif any(w in text for w in ["review", "analyze", "check"]):
            step_templates = [
                ("Gather relevant context", 10),
                ("Review code/implementation", 20),
                ("Document findings", 10),
                ("Suggest improvements", 10),
            ]
        else:
            # Generic fallback
            step_templates = [
                ("Understand the task", 5),
                ("Plan approach", 10),
                ("Execute", 20),
                ("Verify result", 5),
            ]

        # Adjust based on complexity
        if complexity == TaskComplexity.TRIVIAL:
            step_templates = step_templates[:2]
        elif complexity == TaskComplexity.SIMPLE:
            step_templates = step_templates[:3]
        elif complexity == TaskComplexity.EPIC:
            # Add more detailed steps for epic tasks
            step_templates = [
                ("Understand requirements fully", 15),
                ("Research approaches and best practices", 20),
                ("Design architecture", 30),
                ("Plan sub-tasks", 10),
                *step_templates,
                ("Comprehensive testing", 20),
                ("Documentation", 15),
                ("Performance testing", 15),
            ]

        # Create steps with IDs and dependencies
        for i, (desc, minutes) in enumerate(step_templates):
            step = PlanStep(
                id=uuid.uuid4().hex[:8],
                description=desc,
                estimated_minutes=minutes,
                created_at=datetime.now().isoformat(),
            )

            # First step has no dependencies, others depend on previous
            if i > 0:
                step.dependencies = [steps[i - 1].id]

            steps.append(step)

        return steps

    def update_step_status(
        self,
        plan: ExecutionPlan,
        step_id: str,
        status: StepStatus,
    ) -> Optional[PlanStep]:
        """Update status of a step in the plan."""
        for step in plan.steps:
            if step.id == step_id:
                now = datetime.now().isoformat()

                if (
                    status == StepStatus.IN_PROGRESS
                    and step.status != StepStatus.IN_PROGRESS
                ):
                    step.started_at = now
                elif status == StepStatus.COMPLETED:
                    step.completed_at = now

                step.status = status
                plan.updated_at = now

                # Check for blocked steps
                self._check_blocked_steps(plan)

                return step
        return None

    def _check_blocked_steps(self, plan: ExecutionPlan) -> None:
        """Check and update blocked steps based on dependencies."""
        completed_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}

        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                # Check if all dependencies are completed
                deps_met = all(dep_id in completed_ids for dep_id in step.dependencies)
                if not deps_met:
                    step.status = StepStatus.BLOCKED

    def get_next_steps(self, plan: ExecutionPlan, limit: int = 3) -> List[PlanStep]:
        """Get next executable steps (not blocked, dependencies met)."""
        ready = []
        completed_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}

        for step in plan.steps:
            if step.status == StepStatus.PENDING:
                # Check dependencies
                deps_met = all(dep_id in completed_ids for dep_id in step.dependencies)
                if deps_met:
                    ready.append(step)

        return ready[:limit]

    def to_markdown(self, plan: ExecutionPlan) -> str:
        """Convert plan to markdown for display."""
        lines = [
            f"# Plan: {plan.title}",
            "",
            f"**Complexity:** {plan.complexity.value}",
            f"**Estimated Time:** {plan.total_estimated_minutes} minutes",
            "",
            "## Steps",
            "",
        ]

        for i, step in enumerate(plan.steps, 1):
            status_icon = {
                StepStatus.PENDING: "⬜",
                StepStatus.IN_PROGRESS: "🔄",
                StepStatus.BLOCKED: "⛔",
                StepStatus.COMPLETED: "✅",
                StepStatus.SKIPPED: "⏭️",
            }.get(step.status, "⬜")

            lines.append(f"{status_icon} **{i}. {step.description}**")

            if step.dependencies:
                lines.append(f"   ↳ Depends on: {', '.join(step.dependencies[:2])}")

            if step.estimated_minutes:
                lines.append(f"   ↳ Est. {step.estimated_minutes} min")

            if step.notes:
                lines.append(f"   ↳ Note: {step.notes}")

            lines.append("")

        return "\n".join(lines)


# =============================================================================
# Tool Functions
# =============================================================================


def prometheus_create_plan(
    title: str,
    description: str = "",
) -> str:
    """Create an execution plan for a task."""
    prometheus = Prometheus()
    plan = prometheus.create_plan(title, description)
    return json.dumps(
        {
            "success": True,
            "plan": plan.to_dict(),
        }
    )


def prometheus_get_next_steps(
    plan_json: str,
    limit: int = 3,
) -> str:
    """Get next executable steps from a plan."""
    import json

    try:
        plan_data = json.loads(plan_json)
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid plan JSON"})

    # Reconstruct plan
    steps = []
    for step_data in plan_data.get("steps", []):
        step = PlanStep(
            id=step_data["id"],
            description=step_data["description"],
            status=StepStatus(step_data.get("status", "pending")),
            dependencies=step_data.get("dependencies", []),
            estimated_minutes=step_data.get("estimated_minutes", 0),
        )
        steps.append(step)

    plan = ExecutionPlan(
        id=plan_data.get("id", ""),
        title=plan_data.get("title", ""),
        description=plan_data.get("description", ""),
        complexity=TaskComplexity(plan_data.get("complexity", "simple")),
        steps=steps,
    )

    prometheus = Prometheus()
    next_steps = prometheus.get_next_steps(plan, limit)

    return json.dumps(
        {
            "success": True,
            "next_steps": [s.to_dict() for s in next_steps],
        }
    )


def prometheus_to_markdown(plan_json: str) -> str:
    """Convert plan to markdown."""
    import json

    try:
        plan_data = json.loads(plan_json)
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid plan JSON"})

    # Reconstruct plan (simplified)
    plan = ExecutionPlan(
        id=plan_data.get("id", ""),
        title=plan_data.get("title", ""),
        description=plan_data.get("description", ""),
        complexity=TaskComplexity(plan_data.get("complexity", "simple")),
        total_estimated_minutes=plan_data.get("total_estimated_minutes", 0),
    )

    prometheus = Prometheus()
    markdown = prometheus.to_markdown(plan)

    return json.dumps(
        {
            "success": True,
            "markdown": markdown,
        }
    )
