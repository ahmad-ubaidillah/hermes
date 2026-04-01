#!/usr/bin/env python3
"""
Real API Integration Tests for AIAgent

Tests that exercise the actual LLM API endpoints, tool calling roundtrips,
and session persistence.  These tests require valid API credentials and
are skipped automatically when none are configured.

All tests are marked with @pytest.mark.integration so they can be excluded
from the fast unit-test suite:

    python -m pytest tests/ -q              # all tests
    python -m pytest tests/ -q -m "not integration"  # skip slow/real-API tests
    python -m pytest tests/integration/test_real_api.py -v  # run only these

Usage:
    Set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY
    Then run the test suite normally.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _any_api_key_present() -> bool:
    """Return True if at least one supported LLM API key is in the environment."""
    env_keys = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_TOKEN",
        "OPENROUTER_API_KEY",
    )
    return any(os.getenv(k) for k in env_keys)


def _pick_model() -> str:
    """Pick a suitable model based on available API keys."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o-mini"
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_TOKEN"):
        return "anthropic/claude-sonnet-4-20250514"
    # OpenRouter fallback
    return "openai/gpt-4o-mini"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ai_agent(tmp_path_factory):
    """Create a real AIAgent instance with session persistence to a temp dir."""
    if not _any_api_key_present():
        pytest.skip("No LLM API key configured")

    from run_agent import AIAgent

    tmp_home = tmp_path_factory.mktemp("hermes_real_api")
    (tmp_home / "sessions").mkdir()
    (tmp_home / "memories").mkdir()
    (tmp_home / "skills").mkdir()

    with patch.dict(os.environ, {"HERMES_HOME": str(tmp_home)}):
        # Force re-import of hermes_constants so it picks up the patched env
        import importlib
        import core.hermes_constants

        importlib.reload(core.hermes_constants)

        agent = AIAgent(
            model=_pick_model(),
            max_iterations=5,
            quiet_mode=True,
            persist_session=True,
            skip_context_files=True,
            skip_memory=True,
            save_trajectories=False,
        )
        yield agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicChatCompletion:
    """Test basic text chat without tool calls."""

    def test_simple_chat_returns_response(self, ai_agent):
        """AIAgent.chat() returns a non-empty string for a simple question."""
        response = ai_agent.chat("Reply with exactly the word PONG and nothing else.")
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should not be empty"
        assert "PONG" in response.upper(), (
            f"Expected 'PONG' in response, got: {response[:200]}"
        )

    def test_chat_is_deterministic_enough(self, ai_agent):
        """Two identical prompts should produce similar (not necessarily identical) responses."""
        prompt = "What is 2 + 2? Answer with just the number."
        r1 = ai_agent.chat(prompt)
        r2 = ai_agent.chat(prompt)
        # Both should contain '4'
        assert "4" in r1, f"Expected '4' in first response: {r1[:200]}"
        assert "4" in r2, f"Expected '4' in second response: {r2[:200]}"


class TestToolCallRoundtrip:
    """Test that the agent can actually call tools and use their results."""

    def test_terminal_tool_roundtrip(self, ai_agent):
        """Agent should be able to execute a terminal command and use the output."""
        response = ai_agent.chat(
            "Run the command: echo HELLO_FROM_TERMINAL\n"
            "Then tell me exactly what the command output was."
        )
        assert isinstance(response, str), "Response should be a string"
        assert len(response) > 0, "Response should not be empty"
        # The agent should have seen the output and mentioned it
        assert "HELLO_FROM_TERMINAL" in response, (
            f"Agent should have echoed the terminal output. Got: {response[:300]}"
        )

    def test_read_file_tool_roundtrip(self, ai_agent):
        """Agent should be able to read a file we create and report its contents."""
        from core.hermes_constants import get_hermes_home

        test_dir = get_hermes_home() / "test_real_api"
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "secret.txt"
        test_file.write_text("THE_SECRET_IS_42\n", encoding="utf-8")

        response = ai_agent.chat(
            f"Read the file at {test_file} and tell me its exact contents."
        )
        assert isinstance(response, str), "Response should be a string"
        assert "42" in response, (
            f"Agent should have read the file content. Got: {response[:300]}"
        )


class TestSessionPersistence:
    """Test that conversations are persisted across AIAgent.chat() calls."""

    def test_session_remembers_previous_message(self, ai_agent):
        """Agent should remember context from earlier in the conversation."""
        # First message establishes context
        ai_agent.chat(
            "Remember this code: HERMES_TEST_CODE_9876. Acknowledge with just: SAVED"
        )
        # Second message asks about it
        response = ai_agent.chat(
            "What code did I ask you to remember? Reply with the exact code."
        )
        assert "HERMES_TEST_CODE_9876" in response, (
            f"Agent should remember the code from the previous turn. Got: {response[:300]}"
        )

    def test_session_id_is_consistent(self, ai_agent):
        """The session_id should remain the same across multiple chat() calls."""
        session_id_1 = ai_agent.session_id
        ai_agent.chat("Hello")
        session_id_2 = ai_agent.session_id
        assert session_id_1 == session_id_2, (
            f"Session ID changed: {session_id_1} -> {session_id_2}"
        )

    def test_session_file_persisted_to_disk(self, ai_agent):
        """After a conversation, a session JSONL file should exist on disk."""
        from core.hermes_constants import get_hermes_home

        ai_agent.chat("This is a persistence test. Reply with: PERSISTED_OK")

        sessions_dir = get_hermes_home() / "sessions"
        if sessions_dir.exists():
            session_files = list(sessions_dir.glob("*.jsonl")) + list(
                sessions_dir.glob("*.json")
            )
            assert len(session_files) > 0, f"No session files found in {sessions_dir}"
        else:
            pytest.skip(
                "Sessions directory does not exist (session persistence may be disabled)"
            )


class TestErrorHandling:
    """Test graceful error handling with real API."""

    def test_invalid_model_falls_back(self):
        """An invalid model should trigger graceful error handling."""
        from run_agent import AIAgent

        agent = AIAgent(
            model="nonexistent/model-that-does-not-exist-12345",
            max_iterations=2,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        try:
            response = agent.chat("Hello")
            # If it somehow succeeds (e.g. via fallback), it should still be a string
            assert isinstance(response, str)
        except Exception as exc:
            # An exception is also acceptable for a truly invalid model
            assert (
                "model" in str(exc).lower()
                or "api" in str(exc).lower()
                or "not found" in str(exc).lower()
            ), f"Unexpected error message: {exc}"
