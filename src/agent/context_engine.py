"""L0/L1/L2 Context Engine for Aizen Agent.

Hierarchical context management with token budgeting across three levels:
- L0 (Hot): System prompt, current task, recent tool results
- L1 (Warm): Session conversation history
- L2 (Cold): Historical summaries, learned patterns
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ContextLevel:
    """Represents a context level with its budget."""

    name: str
    token_budget: int
    current_tokens: int = 0

    @property
    def usage_ratio(self) -> float:
        """Return the current usage ratio."""
        if self.token_budget == 0:
            return 0.0
        return self.current_tokens / self.token_budget

    @property
    def needs_compaction(self) -> bool:
        """Check if context needs compaction."""
        return self.usage_ratio >= 0.5


@dataclass
class ContextMessage:
    """A message in the context."""

    role: str
    content: str
    level: str
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine:
    """Manages hierarchical context with token budgeting."""

    def __init__(
        self,
        l0_budget: int = 15000,
        l1_budget: int = 50000,
        l2_budget: int = 20000,
        compaction_threshold: float = 0.5,
    ):
        """Initialize context engine.

        Args:
            l0_budget: Token budget for L0 (hot) context
            l1_budget: Token budget for L1 (warm) context
            l2_budget: Token budget for L2 (cold) context
            compaction_threshold: Ratio at which to trigger compaction
        """
        self.l0 = ContextLevel("L0", l0_budget)
        self.l1 = ContextLevel("L1", l1_budget)
        self.l2 = ContextLevel("L2", l2_budget)
        self.compaction_threshold = compaction_threshold

        self._l0_messages: List[ContextMessage] = []
        self._l1_messages: List[ContextMessage] = []
        self._l2_messages: List[ContextMessage] = []

    def add_message(self, role: str, content: str, level: str = "L1") -> ContextMessage:
        """Add a message to the specified context level.

        Args:
            role: Message role (system, user, assistant, tool)
            content: Message content
            level: Context level (L0, L1, L2)

        Returns:
            The created ContextMessage
        """
        tokens = self._estimate_tokens(content)
        message = ContextMessage(role=role, content=content, level=level, tokens=tokens)

        if level == "L0":
            self._l0_messages.append(message)
            self.l0.current_tokens += tokens
        elif level == "L1":
            self._l1_messages.append(message)
            self.l1.current_tokens += tokens
        else:
            self._l2_messages.append(message)
            self.l2.current_tokens += tokens

        return message

    def get_context(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get the full context for the LLM.

        Args:
            max_tokens: Maximum tokens to return (None for unlimited)

        Returns:
            List of message dicts
        """
        context = []

        for msg in self._l0_messages:
            context.append({"role": msg.role, "content": msg.content})

        l1_messages = self._trim_to_budget(
            self._l1_messages, self.l1.token_budget, max_tokens
        )
        for msg in l1_messages:
            context.append({"role": msg.role, "content": msg.content})

        if max_tokens and self._estimate_context_tokens(context) < max_tokens * 0.8:
            l2_messages = self._trim_to_budget(
                self._l2_messages, self.l2.token_budget, max_tokens
            )
            for msg in l2_messages:
                context.append({"role": msg.role, "content": msg.content})

        return context

    def _trim_to_budget(
        self,
        messages: List[ContextMessage],
        budget: int,
        max_tokens: Optional[int] = None,
    ) -> List[ContextMessage]:
        """Trim messages to fit within budget.

        Args:
            messages: List of messages to trim
            budget: Token budget
            max_tokens: Optional token limit

        Returns:
            Trimmed list of messages
        """
        if max_tokens:
            budget = min(budget, max_tokens)

        total_tokens = sum(m.tokens for m in messages)
        if total_tokens <= budget:
            return messages

        trimmed = []
        for msg in reversed(messages):
            if sum(m.tokens for m in trimmed) + msg.tokens <= budget:
                trimmed.insert(0, msg)
            if sum(m.tokens for m in trimmed) >= budget:
                break

        return trimmed

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses rough approximation: 1 token ~= 4 characters.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)

    def _estimate_context_tokens(self, context: List[Dict[str, str]]) -> int:
        """Estimate total tokens in context.

        Args:
            context: List of message dicts

        Returns:
            Estimated token count
        """
        total = 0
        for msg in context:
            total += self._estimate_tokens(msg.get("content", ""))
        return total

    def needs_compaction(self) -> Tuple[bool, str]:
        """Check if any level needs compaction.

        Returns:
            (needs_compaction, reason)
        """
        if self.l0.needs_compaction:
            return True, f"L0 at {self.l0.usage_ratio:.1%} usage"
        if self.l1.needs_compaction:
            return True, f"L1 at {self.l1.usage_ratio:.1%} usage"
        if self.l2.needs_compaction:
            return True, f"L2 at {self.l2.usage_ratio:.1%} usage"
        return False, ""

    def compact(self, distillation_pipeline: Optional[Any] = None) -> Dict[str, int]:
        """Compact context across all levels.

        Args:
            distillation_pipeline: Optional distillation pipeline to use

        Returns:
            Dict with compaction stats
        """
        stats = {
            "l0_before": self.l0.current_tokens,
            "l1_before": self.l1.current_tokens,
            "l2_before": self.l2.current_tokens,
        }

        if distillation_pipeline:
            self._compact_with_distillation(distillation_pipeline)
        else:
            self._compact_basic()

        stats["l0_after"] = self.l0.current_tokens
        stats["l1_after"] = self.l1.current_tokens
        stats["l2_after"] = self.l2.current_tokens
        stats["saved"] = (
            (stats["l0_before"] - stats["l0_after"])
            + (stats["l1_before"] - stats["l1_after"])
            + (stats["l2_before"] - stats["l2_after"])
        )

        return stats

    def _compact_basic(self) -> None:
        """Basic compaction by removing old messages."""
        for _ in range(len(self._l0_messages) // 4):
            if self._l0_messages:
                msg = self._l0_messages.pop(0)
                self.l0.current_tokens -= msg.tokens

        for _ in range(len(self._l1_messages) // 4):
            if self._l1_messages:
                msg = self._l1_messages.pop(0)
                self.l1.current_tokens -= msg.tokens

        for _ in range(len(self._l2_messages) // 4):
            if self._l2_messages:
                msg = self._l2_messages.pop(0)
                self.l2.current_tokens -= msg.tokens

    def _compact_with_distillation(self, pipeline: Any) -> None:
        """Compact using distillation pipeline.

        Args:
            pipeline: Distillation pipeline instance
        """
        for i, msg in enumerate(self._l1_messages):
            if "tool" in msg.role and msg.tokens > 1000:
                try:
                    distilled = pipeline.compose(
                        pipeline.collapse(
                            pipeline.score(pipeline.classify(msg.content))
                        )
                    )
                    old_tokens = msg.tokens
                    msg.content = distilled
                    msg.tokens = self._estimate_tokens(distilled)
                    self.l1.current_tokens += msg.tokens - old_tokens
                except Exception:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """Get context engine statistics.

        Returns:
            Dict with stats
        """
        return {
            "l0": {
                "budget": self.l0.token_budget,
                "used": self.l0.current_tokens,
                "usage": self.l0.usage_ratio,
                "messages": len(self._l0_messages),
            },
            "l1": {
                "budget": self.l1.token_budget,
                "used": self.l1.current_tokens,
                "usage": self.l1.usage_ratio,
                "messages": len(self._l1_messages),
            },
            "l2": {
                "budget": self.l2.token_budget,
                "used": self.l2.current_tokens,
                "usage": self.l2.usage_ratio,
                "messages": len(self._l2_messages),
            },
        }

    def reset(self) -> None:
        """Reset all context levels."""
        self._l0_messages.clear()
        self._l1_messages.clear()
        self._l2_messages.clear()
        self.l0.current_tokens = 0
        self.l1.current_tokens = 0
        self.l2.current_tokens = 0


_default_context_engine: Optional[ContextEngine] = None


def get_context_engine() -> ContextEngine:
    """Get the default context engine instance."""
    global _default_context_engine
    if _default_context_engine is None:
        _default_context_engine = ContextEngine()
    return _default_context_engine


def init_context_engine(
    l0_budget: int = 15000,
    l1_budget: int = 50000,
    l2_budget: int = 20000,
    compaction_threshold: float = 0.5,
) -> ContextEngine:
    """Initialize the default context engine.

    Args:
        l0_budget: Token budget for L0
        l1_budget: Token budget for L1
        l2_budget: Token budget for L2
        compaction_threshold: Ratio to trigger compaction

    Returns:
        Initialized ContextEngine instance
    """
    global _default_context_engine
    _default_context_engine = ContextEngine(
        l0_budget=l0_budget,
        l1_budget=l1_budget,
        l2_budget=l2_budget,
        compaction_threshold=compaction_threshold,
    )
    return _default_context_engine
