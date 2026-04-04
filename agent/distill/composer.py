"""
Composer for Distillation Pipeline.

Filters and composes content based on signal tiers and importance thresholds.
"""

from typing import List, Tuple, Optional
from .scorer import SignalTier


class ContentComposer:
    """Composes filtered content based on signal tiers and thresholds."""

    def __init__(
        self,
        keep_threshold: SignalTier = SignalTier.CONTEXT,
        compress_noise: bool = True,
        remove_noise: bool = False,
    ):
        """
        Initialize the composer.

        Args:
            keep_threshold: Minimum tier to keep (default: keep CONTEXT and above)
            compress_noise: Whether to compress noise content (default: True)
            remove_noise: Whether to remove noise content entirely (default: False)
        """
        self.keep_threshold = keep_threshold
        self.compress_noise = compress_noise
        self.remove_noise = remove_noise

    def compose(
        self,
        content: str,
        scored_lines: List[Tuple[str, SignalTier]] = None,
        classifier=None,
        scorer=None,
    ) -> str:
        """
        Compose content by filtering and optionally compressing based on tiers.

        Args:
            content: The content to compose
            scored_lines: Optional pre-scored lines [(line, tier), ...]
            classifier: Optional ContentClassifier instance
            scorer: Optional ContentScorer instance

        Returns:
            str: The composed content
        """
        if not content:
            return content

        # Score content if not provided
        if scored_lines is None:
            if classifier is None:
                from .classifier import ContentClassifier

                classifier = ContentClassifier()
            if scorer is None:
                from .scorer import ContentScorer

                scorer = ContentScorer()
            scored_lines = scorer.score_lines(content)

        # Filter and process lines based on tiers
        kept_lines = []
        for line, tier in scored_lines:
            if self._should_keep_line(tier):
                if tier == SignalTier.NOISE and self.compress_noise:
                    # Apply compression to noise lines
                    from .collapser import ContentCollapser

                    collapser = ContentCollapser()
                    compressed_line = collapser.collapse_line(line)
                    kept_lines.append(compressed_line)
                else:
                    kept_lines.append(line)
            # If remove_noise is True and tier is NOISE, skip the line entirely

        return "\n".join(kept_lines)

    def compose_with_tiers(
        self, content: str, keep_threshold: SignalTier = None
    ) -> Tuple[str, dict]:
        """
        Compose content and return stats about what was kept/removed.

        Args:
            content: The content to compose
            keep_threshold: Override the instance threshold

        Returns:
            Tuple of (composed_content, stats_dict)
        """
        if keep_threshold is None:
            keep_threshold = self.keep_threshold

        if not content:
            return content, {"original_lines": 0, "kept_lines": 0, "removed_lines": 0}

        # Score the content
        from .classifier import ContentClassifier
        from .scorer import ContentScorer

        classifier = ContentClassifier()
        scorer = ContentScorer()
        scored_lines = scorer.score_lines(content)

        # Count by tier
        tier_counts = {}
        for _, tier in scored_lines:
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Filter lines
        kept_lines = []
        removed_lines = []
        for line, tier in scored_lines:
            if self._should_keep_line(tier, keep_threshold):
                kept_lines.append(line)
            else:
                removed_lines.append(line)

        composed_content = "\n".join(kept_lines)

        stats = {
            "original_lines": len(scored_lines),
            "kept_lines": len(kept_lines),
            "removed_lines": len(removed_lines),
            "tier_counts": {tier.name: count for tier, count in tier_counts.items()},
            "removal_ratio": len(removed_lines) / len(scored_lines)
            if scored_lines
            else 0,
        }

        return composed_content, stats

    def _should_keep_line(self, tier: SignalTier, threshold: SignalTier = None) -> bool:
        """
        Determine if a line should be kept based on its tier.

        Args:
            tier: The line's signal tier
            threshold: The threshold tier (uses instance threshold if not provided)

        Returns:
            bool: True if the line should be kept
        """
        if threshold is None:
            threshold = self.keep_threshold

        if self.remove_noise and tier == SignalTier.NOISE:
            return False

        # Compare tiers: NOISE < CONTEXT < IMPORTANT < CRITICAL
        tier_order = {
            SignalTier.NOISE: 0,
            SignalTier.CONTEXT: 1,
            SignalTier.IMPORTANT: 2,
            SignalTier.CRITICAL: 3,
        }

        return tier_order.get(tier, -1) >= tier_order.get(threshold, -1)
