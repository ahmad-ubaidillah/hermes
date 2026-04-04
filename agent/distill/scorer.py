"""
Scoring System for Distillation Pipeline.

Assigns signal tiers to classified content based on importance.
"""

import re
from enum import Enum
from typing import Dict, Any, List, Tuple, Union
from .classifier import ContentClassifier, ContentType


class SignalTier(Enum):
    """Signal tiers for content importance."""

    CRITICAL = "critical"  # Must keep (errors, key info)
    IMPORTANT = "important"  # Should keep (key outputs, decisions)
    CONTEXT = "context"  # Nice to have (details, examples)
    NOISE = "noise"  # Can discard (boilerplate, filler)


class ContentScorer:
    """Scores content by importance for distillation decisions."""

    def __init__(self):
        # Define scoring rules per content type
        self.type_scores = {
            ContentType.GIT_DIFF: SignalTier.CRITICAL,  # Changes are critical
            ContentType.ERROR: SignalTier.CRITICAL,  # Errors need attention
            ContentType.OUTPUT: SignalTier.IMPORTANT,  # Command outputs
            ContentType.CODE: SignalTier.IMPORTANT,  # Code snippets
            ContentType.LOG: SignalTier.CONTEXT,  # Logs are context
            ContentType.TABLE: SignalTier.CONTEXT,  # Data tables
            ContentType.TEXT: SignalTier.CONTEXT,  # Regular text
            ContentType.JSON: SignalTier.IMPORTANT,  # Structured data
        }

        # Override rules for specific patterns
        self.pattern_overrides = [
            # Critical patterns
            (r"(?i)error", SignalTier.CRITICAL),
            (r"(?i)exception", SignalTier.CRITICAL),
            (r"(?i)failed", SignalTier.CRITICAL),
            (r"(?i)fatal", SignalTier.CRITICAL),
            (r"(?i)panic", SignalTier.CRITICAL),
            (r"(?i)segfault", SignalTier.CRITICAL),
            (r"(?i)segmentation fault", SignalTier.CRITICAL),
            (r"Traceback \(most recent call last\)", SignalTier.CRITICAL),
            (r"(?i)exit code [1-9]", SignalTier.CRITICAL),  # Non-zero exit
            # Important patterns
            (r"(?i)success", SignalTier.IMPORTANT),
            (r"(?i)completed", SignalTier.IMPORTANT),
            (r"(?i)done", SignalTier.IMPORTANT),
            (r"(?i)created", SignalTier.IMPORTANT),
            (r"(?i)updated", SignalTier.IMPORTANT),
            (r"(?i)saved", SignalTier.IMPORTANT),
            (r"(?i)generated", SignalTier.IMPORTANT),
            # Noise patterns (can be compressed more aggressively)
            (r"^\s*[-*_]{3,}\s*$", SignalTier.NOISE),  # Horizontal rules
            (r"^\s*=+\s*$", SignalTier.NOISE),  # Underlines
            (r"^\s*\d+\.\s*$", SignalTier.NOISE),  # List numbers alone
            (r"^\s*[a-zA-Z]\.\s*$", SignalTier.NOISE),  # Lettered list alone
            (
                r"^\s*[ivxlcdm]+\.\s*$",
                SignalTier.NOISE,
                re.IGNORECASE,
            ),  # Roman numerals
            (r"^\s*\|[\s\-]+\|\s*$", SignalTier.NOISE),  # Empty table rows
            (r"^\s*\+[-+]+\+\s*$", SignalTier.NOISE),  # Table borders
            (r"^\s*[=_-]{3,}\s*$", SignalTier.NOISE),  # Separators
            (r"^\s*\.{3,}\s*$", SignalTier.NOISE),  # Ellipsis lines
            (r"^\s*[-*+]\s{3,}[-*+]\s*$", SignalTier.NOISE),  # Spaced bullets
        ]

        # Compile pattern overrides
        self.compiled_overrides = []
        for pattern, tier, *flags in self.pattern_overrides:
            flag = flags[0] if flags else 0
            self.compiled_overrides.append((re.compile(pattern, flag), tier))

    def score_content(
        self, content: str, content_type: ContentType = None
    ) -> SignalTier:
        """
        Score content by importance tier.

        Args:
            content: The content to score
            content_type: Optional pre-classified content type

        Returns:
            SignalTier: The importance tier
        """
        if not content or not content.strip():
            return SignalTier.NOISE

        # Get base score from content type
        if content_type is None:
            classifier = ContentClassifier()
            content_type = classifier.classify(content)

        base_tier = self.type_scores.get(content_type, SignalTier.CONTEXT)

        # Check for pattern overrides
        for pattern, override_tier in self.compiled_overrides:
            if pattern.search(content):
                # Override with pattern-specific tier (always takes precedence)
                base_tier = override_tier

        return base_tier

    def score_lines(self, content: str) -> List[Tuple[str, SignalTier]]:
        """
        Score each line of content separately.

        Args:
            content: The content to score line-by-line

        Returns:
            List of (line, signal_tier) tuples
        """
        if not content:
            return []

        lines = content.split("\n")
        result = []

        for line in lines:
            tier = self.score_content(line)
            result.append((line, tier))

        return result

    def _tier_priority(self, tier: SignalTier) -> int:
        """Convert tier to numeric priority for comparison."""
        priority_map = {
            SignalTier.NOISE: 0,
            SignalTier.CONTEXT: 1,
            SignalTier.IMPORTANT: 2,
            SignalTier.CRITICAL: 3,
        }
        return priority_map.get(tier, 0)

    def should_keep(
        self, tier: SignalTier, threshold: SignalTier = SignalTier.CONTEXT
    ) -> bool:
        """
        Determine if content should be kept based on threshold.

        Args:
            tier: The content's signal tier
            threshold: Minimum tier to keep (default: keep CONTEXT and above)

        Returns:
            bool: True if content should be kept
        """
        return self._tier_priority(tier) >= self._tier_priority(threshold)
