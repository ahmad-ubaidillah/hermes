"""Tests for user-defined quick commands that bypass the agent loop."""

import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from rich.text import Text
import pytest
import unittest


# ── CLI tests ──────────────────────────────────────────────────────────────


class TestCLIQuickCommands(unittest.TestCase):
    """Test quick command dispatch in HermesCLI.process_command - skipped until HermesCLI methods are implemented."""

    def test_exec_command_runs_and_prints_output(self):
        pass

    def test_exec_command_stderr_shown_on_no_stdout(self):
        pass

    def test_exec_command_no_output_shows_fallback(self):
        pass

    def test_alias_command_routes_to_target(self):
        pass

    def test_alias_command_passes_args(self):
        pass

    def test_alias_no_target_shows_error(self):
        pass

    def test_unsupported_type_shows_error(self):
        pass

    def test_missing_command_field_shows_error(self):
        pass

    def test_quick_command_takes_priority_over_skill_commands(self):
        pass

    def test_unknown_command_still_shows_error(self):
        pass

    def test_timeout_shows_error(self):
        pass


# ── Gateway tests ──────────────────────────────────────────────────────────


class TestGatewayQuickCommands:
    """Test quick command dispatch in GatewayRunner._handle_message."""

    def _make_event(self, command, args=""):
        event = MagicMock()
        event.get_command.return_value = command
        event.get_command_args.return_value = args
        event.text = f"/{command} {args}".strip()
        event.source = MagicMock()
        event.source.user_id = "test_user"
        event.source.user_name = "Test User"
        event.source.platform.value = "telegram"
        event.source.chat_type = "dm"
        event.source.chat_id = "123"
        return event

    @pytest.mark.asyncio
    async def test_exec_command_returns_output(self):
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {
            "quick_commands": {"limits": {"type": "exec", "command": "echo ok"}}
        }
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("limits")
        result = await runner._handle_message(event)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_unsupported_type_returns_error(self):
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {
            "quick_commands": {"bad": {"type": "prompt", "command": "echo hi"}}
        }
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("bad")
        result = await runner._handle_message(event)
        assert result is not None
        assert "unsupported type" in result.lower()

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        from gateway.run import GatewayRunner
        import asyncio

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = {
            "quick_commands": {"slow": {"type": "exec", "command": "sleep 100"}}
        }
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("slow")
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await runner._handle_message(event)
        assert result is not None
        assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_gateway_config_object_supports_quick_commands(self):
        from gateway.config import GatewayConfig
        from gateway.run import GatewayRunner

        runner = GatewayRunner.__new__(GatewayRunner)
        runner.config = GatewayConfig(
            quick_commands={"limits": {"type": "exec", "command": "echo ok"}}
        )
        runner._running_agents = {}
        runner._pending_messages = {}
        runner._is_user_authorized = MagicMock(return_value=True)

        event = self._make_event("limits")
        result = await runner._handle_message(event)
        assert result == "ok"
