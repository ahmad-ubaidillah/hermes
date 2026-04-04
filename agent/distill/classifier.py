"""
Content Classifier for Distillation Pipeline.

Classifies content into types to enable targeted compression strategies.
"""

import re
from typing import List, Dict, Any
from enum import Enum


class ContentType(Enum):
    """Content types for distillation classification."""

    CODE = "code"
    LOG = "log"
    GIT_DIFF = "git_diff"
    JSON = "json"
    TEXT = "text"
    TABLE = "table"
    OUTPUT = "output"
    ERROR = "error"


class ContentClassifier:
    """Classifies content into types for targeted distillation strategies."""

    def __init__(self):
        # Patterns for content type detection
        self.patterns = {
            ContentType.GIT_DIFF: [
                r"^diff --git ",
                r"^index [0-9a-f]+\.\.[0-9a-f]+",
                r"^--- /dev/null",
                r"^\+\+\+ /dev/null",
                r"^@@ -[0-9,]+ \+[0-9,]+ @@",
                r"^[-+]{3} ",
            ],
            ContentType.LOG: [
                r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
                r"^\$\s",  # Shell prompt
                r"^[A-Z]+:\s",  # LEVEL: message
                r"\[\d{2}:\d{2}:\d{2}\]",  # [HH:MM:SS]
                r"^\s*at\s+",  # Stack trace
            ],
            ContentType.JSON: [
                r"^\s*\{",
                r"^\s*\[",
                r'":\s*',  # JSON key-value
            ],
            ContentType.CODE: [
                r"^\s*(def|class|function|const|let|var)\s+",
                r"^\s*(import|from|#include|package)\s+",
                r"^\s*(public|private|protected|static)\s+",
                r"[{}]\s*$",  # Line with just braces
                r";\s*$",  # Line ending with semicolon
            ],
            ContentType.TABLE: [
                r"^\s*\|.*\|\s*$",  # Markdown table
                r"^\s*\+[-+]+\+\s*$",  # ASCII table border
                r"^\s*[+-]+[+-]*[+-]+\s*$",  # Another ASCII table pattern
            ],
            ContentType.ERROR: [
                r"(?i)error:",
                r"(?i)exception:",
                r"(?i)failed:",
                r"(?i)not found",
                r"(?i)permission denied",
                r"^\s*[Ee]rror\s*:",
                r"Traceback \(most recent call last\):",
            ],
            ContentType.OUTPUT: [
                r"^\s*[0-9]+\s+",  # Numbered output
                r"^\s*[-*+]\s+",  # Bulleted list
                r"^\s*[a-zA-Z]\)\s+",  # Lettered list
            ],
        }

        # Compile regex patterns
        self.compiled_patterns = {}
        for content_type, patterns in self.patterns.items():
            self.compiled_patterns[content_type] = [
                re.compile(pattern, re.MULTILINE) for pattern in patterns
            ]

    def classify(self, content: str) -> ContentType:
        """
        Classify content into a type.

        Args:
            content: The content to classify

        Returns:
            ContentType: The detected content type
        """
        if not content or not content.strip():
            return ContentType.TEXT

        lines = content.split("\n")
        if not lines:
            return ContentType.TEXT

        # Score each content type based on pattern matches
        scores = {content_type: 0 for content_type in ContentType}

        for line in lines:
            line = line.rstrip()
            if not line:
                continue

            for content_type, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(line):
                        scores[content_type] += 1
                        break  # Only count one match per line per type

        # Find the content type with the highest score
        max_score = max(scores.values())
        if max_score == 0:
            return ContentType.TEXT

        # In case of tie, prefer more specific types
        preferred_order = [
            ContentType.GIT_DIFF,
            ContentType.JSON,
            ContentType.CODE,
            ContentType.LOG,
            ContentType.ERROR,
            ContentType.TABLE,
            ContentType.OUTPUT,
            ContentType.TEXT,
        ]

        for content_type in preferred_order:
            if scores[content_type] == max_score:
                return content_type

        return ContentType.TEXT

    def classify_lines(self, content: str) -> List[tuple[str, ContentType]]:
        """
        Classify each line of content separately.

        Args:
            content: The content to classify line-by-line

        Returns:
            List of (line, content_type) tuples
        """
        if not content:
            return []

        lines = content.split("\n")
        result = []

        for line in lines:
            content_type = self.classify(line)
            result.append((line, content_type))

        return result
