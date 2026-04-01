"""
Signal Distillation for Aizen - Save 80-90% tokens on terminal output.

This module implements OMNI-style signal distillation:
1. Classify content type (git, test, build, etc)
2. Score each line by importance
3. Filter out noise
4. Return distilled output

Usage:
    from lifecycle.distillation import distill_output
    
    distilled = distill_output(raw_output, command="pytest")
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class SignalTier(Enum):
    """Importance level of output line."""
    CRITICAL = 0.9   # Errors, failures - always keep
    IMPORTANT = 0.7  # Warnings, changes - usually keep
    CONTEXT = 0.4    # Default - keep if space
    NOISE = 0.1      # Progress, debug - drop


class ContentType(Enum):
    """Type of output content."""
    GIT_DIFF = "git_diff"
    GIT_STATUS = "git_status"
    BUILD = "build"
    TEST = "test"
    INFRA = "infra"
    LOG = "log"
    UNKNOWN = "unknown"


@dataclass
class Segment:
    """A scored line segment."""
    line: str
    tier: SignalTier
    score: float
    num: int


# === PATTERNS ===

CRITICAL = [
    r"error\[", r"ERROR:", r"Error:", r"FAILED", r"FAIL:",
    r"panic:", r"Traceback", r"exception:", r"fatal:", r"FATAL:",
    r"✗", r"×", r"AssertionError", r"Error:", r"error:",
]

IMPORTANT = [
    r"warning\[", r"WARNING:", r"Warning:", r"WARN:",
    r"modified:", r"deleted:", r"new file:", r"renamed:",
    r"diff --git", r"^@@ -", r"^--- a/", r"^\+\+\+ b/",
    r"test result:", r"Tests:", r"PASSED", r"passed", r"✓",
    r"Successfully", r"Finished", r"^\s*[MADRC]\s",
]

NOISE = [
    r"^\s*Compiling ", r"^\s*Downloading ", r"^\s*Fetching ",
    r"^\s*Checking ", r"^\s*Blocking", r"^\s*Locking ",
    r"^\s*Unpacking ", r"^\s*Installing ", r"npm warn",
    r"\[DEBUG\]", r"\[TRACE\]", r"DEBUG:", r"TRACE:",
    r" PASSED$", r"^=+ test session", r"^platform ",
    r"^rootdir:", r"^plugins:", r"^collected ",
    r"^\s*\d+%$", r"^\s*\.\.\.\s*$",
]


def classify_line(line: str) -> SignalTier:
    """Classify line into signal tier."""
    s = line.strip()
    if not s:
        return SignalTier.NOISE
    
    for p in CRITICAL:
        if re.search(p, s, re.I):
            return SignalTier.CRITICAL
    
    for p in IMPORTANT:
        if re.search(p, s):
            return SignalTier.IMPORTANT
    
    for p in NOISE:
        if re.search(p, s):
            return SignalTier.NOISE
    
    return SignalTier.CONTEXT


def detect_content_type(output: str, command: str = "") -> ContentType:
    """Detect content type from command and output."""
    cmd = command.lower() if command else ""
    
    if "git diff" in cmd or "git show" in cmd:
        return ContentType.GIT_DIFF
    if "git status" in cmd:
        return ContentType.GIT_STATUS
    if "git log" in cmd:
        return ContentType.GIT_DIFF
    if any(x in cmd for x in ["pytest", "cargo test", "npm test", "go test", "vitest", "jest"]):
        return ContentType.TEST
    if any(x in cmd for x in ["cargo", "make", "npm run build", "gradle", "mvn", "cmake"]):
        return ContentType.BUILD
    if any(x in cmd for x in ["kubectl", "docker", "terraform", "helm", "ansible"]):
        return ContentType.INFRA
    
    # Heuristics from output
    if "diff --git" in output:
        return ContentType.GIT_DIFF
    if "test session" in output.lower() or "passed" in output.lower():
        return ContentType.TEST
    if "Compiling" in output or "Building" in output:
        return ContentType.BUILD
    
    return ContentType.UNKNOWN


def score_output(output: str) -> List[Segment]:
    """Score all lines in output."""
    lines = output.split("\n")
    segments = []
    
    for i, line in enumerate(lines):
        tier = classify_line(line)
        segments.append(Segment(
            line=line,
            tier=tier,
            score=tier.value,
            num=i + 1,
        ))
    
    return segments


def distill_output(
    output: str,
    command: str = "",
    threshold: float = 0.3,
    max_lines: int = 100,
) -> str:
    """
    Distill noisy output into essential signal.
    
    Args:
        output: Raw command output
        command: Command that produced output
        threshold: Minimum score to keep (0.0-1.0)
        max_lines: Maximum lines in output
    
    Returns:
        Distilled output with reduced tokens
    """
    if not output or len(output) < 200:
        return output
    
    # Score all lines
    segments = score_output(output)
    
    # Filter by threshold
    kept = [s for s in segments if s.score >= threshold]
    
    if not kept:
        # All noise - return summary
        content_type = detect_content_type(output, command)
        return _success_message(content_type)
    
    # Sort by line number for readability
    kept.sort(key=lambda s: s.num)
    
    # Limit lines
    if len(kept) > max_lines:
        # Keep critical/important first
        kept.sort(key=lambda s: (-s.score, s.num))
        kept = kept[:max_lines]
        kept.sort(key=lambda s: s.num)
    
    # Build output
    lines = []
    prev_num = 0
    
    for seg in kept:
        if seg.num > prev_num + 1:
            lines.append("...")  # Indicate skipped lines
        lines.append(seg.line)
        prev_num = seg.num
    
    result = "\n".join(lines)
    
    # Add savings info
    original_size = len(output)
    distilled_size = len(result)
    savings = 100 - (distilled_size / original_size * 100)
    
    if savings > 20:
        result += f"\n\n[Distilled: {savings:.0f}% token savings]"
    
    return result


def _success_message(content_type: ContentType) -> str:
    """Message when all output is noise (success)."""
    messages = {
        ContentType.TEST: "✓ All tests passed",
        ContentType.BUILD: "✓ Build successful",
        ContentType.GIT_STATUS: "✓ Working tree clean",
        ContentType.GIT_DIFF: "✓ No changes",
        ContentType.INFRA: "✓ Operation successful",
    }
    return messages.get(content_type, "✓ Completed successfully")


# === TESTS ===

if __name__ == "__main__":
    # Test pytest
    pytest_out = """
============================= test session starts ==============================
platform linux -- Python 3.12.0, pytest-8.0.0
rootdir: /home/user/project
collected 100 items

tests/test_api.py::test_create_user PASSED
tests/test_api.py::test_delete_user PASSED
tests/test_api.py::test_update_user PASSED

============================== 100 passed in 5.42s =============================
"""
    
    # Test cargo
    cargo_out = """
   Compiling serde v1.0.197
   Compiling serde_derive v1.0.197
   Compiling my-crate v0.1.0
error[E0308]: mismatched types
 --> src/main.rs:10:5
  |
10|     "hello"
  |     ^^^^^^^ expected `i32`, found `&str`
error: aborting due to previous error
"""
    
    # Test git status
    git_out = """
On branch main
Changes to be committed:
        modified:   src/main.rs
        modified:   src/lib.rs
        new file:   src/utils.rs
Changes not staged for commit:
        modified:   README.md
Untracked files:
        tests/test_new.py
"""
    
    print("=" * 60)
    print("PYTEST OUTPUT:")
    print(distill_output(pytest_out, "pytest"))
    print()
    
    print("=" * 60)
    print("CARGO OUTPUT:")
    print(distill_output(cargo_out, "cargo build"))
    print()
    
    print("=" * 60)
    print("GIT STATUS:")
    print(distill_output(git_out, "git status"))
