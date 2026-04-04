"""
Collapser for Distillation Pipeline.

Compresses repetitive patterns and removes redundancy from content.
"""

import re
from typing import List, Tuple
from .scorer import SignalTier


class ContentCollapser:
    """Collapses repetitive patterns in content to reduce token usage."""

    def __init__(self):
        # Patterns for line-based compression
        self.line_patterns = [
            # Horizontal rules
            (r"^([-*_=~#])\1{2,}$", lambda m: f"{m.group(1)} x{len(m.group(0))}"),
            # Repeated characters
            (r"^(.)\1{2,}$", lambda m: f"{m.group(1)} x{len(m.group(0))}"),
            # Numbered lists with same prefix
            (r"^(\s*)\d+\.(.*)$", self._collapse_numbered_list),
            # Lettered lists
            (r"^(\s*)[a-zA-Z]\.(.*)$", self._collapse_lettered_list),
            # Roman numeral lists
            (r"^(\s*)[ivxlcdm]+\.(.*)$", self._collapse_roman_list, re.IGNORECASE),
            # Bullet points
            (r"^(\s*)[-*+]\s(.*)$", self._collapse_bullet_list),
            # Table rows
            (r"^\s*\|.*\|\s*$", self._collapse_table_row),
            # JSON arrays/objects (simple case)
            (r"^\s*[\[\]{}],?\s*$", self._collapse_json_brackets),
        ]

        # Compile regex patterns
        self.compiled_line_patterns = []
        for pattern, replacement, *flags in self.line_patterns:
            flag = flags[0] if flags else 0
            self.compiled_line_patterns.append((re.compile(pattern, flag), replacement))

        # Block-level patterns for larger compression
        self.block_patterns = [
            # Repeated identical lines
            (r"^(.*?)\n(\1\n?)+$", self._collapse_repeated_lines),
            # Indented blocks with same pattern
            (r"^(\s*)(.*?)\n(\1\2\n?)+$", self._collapse_indented_block),
        ]

        self.compiled_block_patterns = []
        for pattern, replacement, *flags in self.block_patterns:
            flag = flags[0] if flags else 0
            self.compiled_block_patterns.append(
                (re.compile(pattern, flag | re.DOTALL), replacement)
            )

    def collapse_line(self, line: str) -> str:
        """
        Collapse a single line if it matches compressible patterns.

        Args:
            line: The line to potentially collapse

        Returns:
            str: The collapsed line or original if no compression applies
        """
        if not line:
            return line

        for pattern, replacement in self.compiled_line_patterns:
            match = pattern.match(line)
            if match:
                if callable(replacement):
                    return replacement(match)
                else:
                    return replacement

        return line

    def collapse_content(
        self, content: str, score_lines: List[Tuple[str, SignalTier]] = None
    ) -> str:
        """
        Collapse content based on importance tiers.

        Args:
            content: The content to collapse
            score_lines: Optional pre-scored lines [(line, tier), ...]

        Returns:
            str: The collapsed content
        """
        if not content:
            return content

        # If we have pre-scored lines, use them for tier-aware collapsing
        if score_lines is not None:
            return self._collapse_by_tiers(score_lines)

        # Otherwise, apply general collapsing
        lines = content.split("\n")
        if not lines:
            return content

        # Collapse each line
        collapsed_lines = [self.collapse_line(line) for line in lines]

        # Join and try block-level compression
        collapsed_content = "\n".join(collapsed_lines)

        # Apply block-level patterns
        for pattern, replacement in self.compiled_block_patterns:
            match = pattern.search(collapsed_content)
            if match:
                if callable(replacement):
                    collapsed_content = replacement(match)
                else:
                    collapsed_content = replacement
                # Try again in case of nested patterns
                return self.collapse_content(collapsed_content)

        return collapsed_content

    def _collapse_by_tiers(self, score_lines: List[Tuple[str, SignalTier]]) -> str:
        """
        Collapse content based on signal tiers - more aggressive for noise.

        Args:
            score_lines: List of (line, tier) tuples

        Returns:
            str: The collapsed content
        """
        if not score_lines:
            return ""

        result_lines = []
        i = 0

        while i < len(score_lines):
            line, tier = score_lines[i]

            # For noise content, be more aggressive with compression
            if tier == SignalTier.NOISE:
                # Look ahead for consecutive noise lines
                j = i + 1
                while j < len(score_lines) and score_lines[j][1] == SignalTier.NOISE:
                    j += 1

                # Collapse the noise block
                noise_block = "\n".join([score_lines[k][0] for k in range(i, j)])
                collapsed_noise = self.collapse_content(noise_block)
                result_lines.append(collapsed_noise)
                i = j
            else:
                # For non-noise, collapse line normally
                collapsed_line = self.collapse_line(line)
                result_lines.append(collapsed_line)
                i += 1

        return "\n".join(result_lines)

    def _collapse_numbered_list(self, match: re.Match) -> str:
        """Collapse numbered list items."""
        indent, content = match.groups()
        # This is simplified - in practice we'd need to look at consecutive lines
        return f"{indent}{content}"

    def _collapse_lettered_list(self, match: re.Match) -> str:
        """Collapse lettered list items."""
        indent, content = match.groups()
        return f"{indent}{content}"

    def _collapse_roman_list(self, match: re.Match) -> str:
        """Collapse roman numeral list items."""
        indent, content = match.groups()
        return f"{indent}{content}"

    def _collapse_bullet_list(self, match: re.Match) -> str:
        """Collapse bullet point items."""
        indent, content = match.groups()
        return f"{indent}- {content}"

    def _collapse_table_row(self, match: re.Match) -> str:
        """Collapse table rows."""
        line = match.group(0)
        # Simplified - just return as-is for now
        return line

    def _collapse_json_brackets(self, match: re.Match) -> str:
        """Collapse JSON brackets."""
        return match.group(0)

    def _collapse_repeated_lines(self, match: re.Match) -> str:
        """Collapse blocks of identical lines."""
        line = match.group(1)
        # Count how many times it repeats
        full_match = match.group(0)
        count = full_count("\n" + line, full_match)
        return f"{line} [x{count + 1}]"

    def _collapse_indented_block(self, match: re.Match) -> str:
        """Collapse indented blocks with same content pattern."""
        indent, content = match.group(1, 2)
        # Simplified
        return f"{indent}{content} [repeated]"


def full_count(sub: str, full: str) -> int:
    """Count overlapping occurrences of sub in full."""
    count = start = 0
    while True:
        start = full.find(sub, start) + 1
        if start > 0:
            count += 1
        else:
            return count
