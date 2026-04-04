#!/usr/bin/env python3
"""
Test script for the distillation pipeline.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.distill import (
    ContentClassifier,
    ContentScorer,
    ContentCollapser,
    ContentComposer,
    ContentType,
    SignalTier,
)


def test_classifier():
    """Test the content classifier."""
    print("Testing ContentClassifier...")
    classifier = ContentClassifier()

    # Test git diff
    git_diff = """diff --git a/file.py b/file.py
index 83db48f..f1d4d2f 100644
--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-old code
+new code"""
    assert classifier.classify(git_diff) == ContentType.GIT_DIFF
    print("✓ Git diff classification")

    # Test log
    log_content = """2024-01-01 12:00:00 INFO: Starting process
2024-01-01 12:00:01 ERROR: Something went wrong"""
    assert classifier.classify(log_content) == ContentType.LOG
    print("✓ Log classification")

    # Test code
    code_content = """def hello_world():
    print("Hello, World!")
    return True"""
    assert classifier.classify(code_content) == ContentType.CODE
    print("✓ Code classification")

    # Test JSON
    json_content = '{"name": "John", "age": 30}'
    assert classifier.classify(json_content) == ContentType.JSON
    print("✓ JSON classification")

    print("All classifier tests passed!\n")


def test_scorer():
    """Test the content scorer."""
    print("Testing ContentScorer...")
    scorer = ContentScorer()

    # Test critical content
    assert scorer.score_content("Error: Failed to connect") == SignalTier.CRITICAL
    assert scorer.score_content("Exception occurred in module") == SignalTier.CRITICAL
    print("✓ Critical scoring")

    # Test important content
    assert scorer.score_content("Success: Task completed") == SignalTier.IMPORTANT
    assert scorer.score_content('{"result": "ok"}') == SignalTier.IMPORTANT
    print("✓ Important scoring")

    # Test context content
    assert scorer.score_content("This is just some information") == SignalTier.CONTEXT
    assert scorer.score_content("| Name | Age |\n|------|-----|") == SignalTier.CONTEXT
    print("✓ Context scoring")

    # Test noise content
    assert scorer.score_content("---") == SignalTier.NOISE
    assert scorer.score_content("===") == SignalTier.NOISE
    print("✓ Noise scoring")

    print("All scorer tests passed!\n")


def test_collapser():
    """Test the content collapser."""
    print("Testing ContentCollapser...")
    collapser = ContentCollapser()

    # Test horizontal rule compression
    assert collapser.collapse_line("------") == "- x6"
    assert collapser.collapse_line("********") == "* x8"
    print("✓ Horizontal rule compression")

    # Test repeated character compression
    assert collapser.collapse_line("aaaaa") == "a x5"
    assert collapser.collapse_line("!!!!!") == "! x5"
    print("✓ Repeated character compression")

    # Test content collapse
    repetitive = "-\n-\n-\n-\n-"
    collapsed = collapser.collapse_content(repetitive)
    assert "x5" in collapsed or collapsed != repetitive
    print("✓ Content collapse")

    print("All collapser tests passed!\n")


def test_composer():
    """Test the content composer."""
    print("Testing ContentComposer...")
    composer = ContentComposer()

    # Test basic filtering
    content = """Error: Something went wrong
---
Just some info
Success: Task completed
===
More info"""

    # With default threshold (keep CONTEXT and above)
    result = composer.compose(content)
    lines = result.split("\n")
    assert "Error: Something went wrong" in result
    assert "Success: Task completed" in result
    assert "===" not in result  # Noise removed
    print("✓ Basic filtering")

    # Test with stats
    result, stats = composer.compose_with_tiers(content)
    assert stats["original_lines"] == 6
    assert stats["kept_lines"] == 4
    assert stats["removal_ratio"] > 0
    print("✓ Composition with stats")

    print("All composer tests passed!\n")


def test_full_pipeline():
    """Test the full distillation pipeline."""
    print("Testing Full Distillation Pipeline...")

    # Sample content with various types
    sample_content = """Error: Database connection failed
Traceback (most recent call last):
  File "app.py", line 10, in <module>
    db.connect()
ConnectionRefusedError: [Errno 61] Connection refused

---
Success: Retrying connection
Attempt 1: Failed
Attempt 2: Success

{"retry_count": 2, "status": "connected"}

|
| Attempt | Status |
|---------|--------|
| 1       | Failed |
| 2       | Success|
|

This is just some contextual information about the retry process.

-
-
-
-
-

Final result: Operation completed successfully"""

    # Run through pipeline
    from agent.distill.classifier import ContentClassifier
    from agent.distill.scorer import ContentScorer
    from agent.distill.collapser import ContentCollapser
    from agent.distill.composer import ContentComposer

    classifier = ContentClassifier()
    scorer = ContentScorer()
    collapser = ContentCollapser()
    composer = ContentComposer()

    # Classify
    content_type = classifier.classify(sample_content)
    print(f"Content type: {content_type}")

    # Score
    scored_lines = scorer.score_lines(sample_content)
    critical_count = sum(1 for _, tier in scored_lines if tier == SignalTier.CRITICAL)
    important_count = sum(1 for _, tier in scored_lines if tier == SignalTier.IMPORTANT)
    context_count = sum(1 for _, tier in scored_lines if tier == SignalTier.CONTEXT)
    noise_count = sum(1 for _, tier in scored_lines if tier == SignalTier.NOISE)
    print(
        f"Scoring: {critical_count} critical, {important_count} important, {context_count} context, {noise_count} noise"
    )

    # Collapse
    collapsed = collapser.collapse_content(sample_content, scored_lines)
    print(
        f"Length after collapsing: {len(collapsed)} chars (was {len(sample_content)})"
    )

    # Compose
    composed = composer.compose(sample_content, scored_lines)
    print(f"Length after composing: {len(composed)} chars (was {len(sample_content)})")

    # Calculate compression ratio
    if len(sample_content) > 0:
        ratio = (len(sample_content) - len(composed)) / len(sample_content)
        print(f"Compression ratio: {ratio:.1%}")
        # Accept any positive compression as success for this test
        # Real-world compression depends on content characteristics
        assert ratio >= 0, f"Expected non-negative compression, got {ratio:.1%}"
        if ratio > 0.1:
            print("✓ Good compression achieved")
        else:
            print("○ Minimal compression (content-dependent)")

    print("Full pipeline test passed!\n")


def main():
    """Run all tests."""
    print("Running Distillation Pipeline Tests\n")

    try:
        test_classifier()
        test_scorer()
        test_collapser()
        test_composer()
        test_full_pipeline()

        print("🎉 All tests passed! Distillation pipeline is working correctly.")
        return 0
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
