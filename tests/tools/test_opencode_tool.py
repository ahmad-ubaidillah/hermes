"""Tests for OpenCode collaboration tools."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestOpenCodeBinary:
    def test_find_opencode_binary_not_found(self):
        from tools.opencode_tool import _find_opencode_binary

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1)
            with patch("os.path.isfile", return_value=False):
                result = _find_opencode_binary()
                assert result is None


class TestOpenCodeCommand:
    def test_run_command_no_binary(self):
        from tools.opencode_tool import _run_opencode_command

        with patch("tools.opencode_tool._find_opencode_binary", return_value=None):
            result = _run_opencode_command(["run", "--prompt", "test"])
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_run_command_success(self):
        from tools.opencode_tool import _run_opencode_command

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "result"
        mock_proc.stderr = ""
        with (
            patch(
                "tools.opencode_tool._find_opencode_binary",
                return_value="/usr/bin/opencode",
            ),
            patch("subprocess.run", return_value=mock_proc),
        ):
            result = _run_opencode_command(["run", "--prompt", "test"])
        assert result["success"] is True
        assert result["stdout"] == "result"

    def test_run_command_failure(self):
        from tools.opencode_tool import _run_opencode_command

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "error message"
        with (
            patch(
                "tools.opencode_tool._find_opencode_binary",
                return_value="/usr/bin/opencode",
            ),
            patch("subprocess.run", return_value=mock_proc),
        ):
            result = _run_opencode_command(["run", "--prompt", "test"])
        assert result["success"] is False
        assert result["stderr"] == "error message"

    def test_run_command_timeout(self):
        from tools.opencode_tool import _run_opencode_command

        with (
            patch(
                "tools.opencode_tool._find_opencode_binary",
                return_value="/usr/bin/opencode",
            ),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)),
        ):
            result = _run_opencode_command(["run", "--prompt", "test"])
        assert result["success"] is False
        assert "timed out" in result["error"]


class TestOpenCodeCodingTask:
    def test_coding_task_success(self):
        from tools.opencode_tool import opencode_coding_task

        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "code result"}
            result = json.loads(opencode_coding_task("write a function"))
        assert result["success"] is True
        assert result["result"] == "code result"
        assert result["provider"] == "opencode"

    def test_coding_task_failure(self):
        from tools.opencode_tool import opencode_coding_task

        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": False, "stderr": "something broke"}
            result = json.loads(opencode_coding_task("write a function"))
        assert result["success"] is False
        assert "failed" in result["error"]

    def test_coding_task_with_context(self):
        from tools.opencode_tool import opencode_coding_task

        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "ok"}
            opencode_coding_task("fix bug", context="error: null pointer")
            call_args = mock_cmd.call_args[0][0]
            assert "--prompt" in call_args
            prompt_idx = call_args.index("--prompt")
            prompt = call_args[prompt_idx + 1]
            assert "fix bug" in prompt
            assert "error: null pointer" in prompt


class TestOpenCodeEditFile:
    def test_edit_file_success(self, tmp_path):
        from tools.opencode_tool import opencode_edit_file

        f = tmp_path / "test.py"
        f.write_text("old code")
        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "new code"}
            result = json.loads(opencode_edit_file(str(f), "add comment"))
        assert result["success"] is True
        assert result["file"] == str(f)

    def test_edit_file_not_found(self):
        from tools.opencode_tool import opencode_edit_file

        result = json.loads(opencode_edit_file("/nonexistent/file.py", "edit"))
        assert result["success"] is False
        assert "not found" in result["error"]


class TestOpenCodeReviewCode:
    def test_review_code_success(self, tmp_path):
        from tools.opencode_tool import opencode_review_code

        f = tmp_path / "code.py"
        f.write_text("def foo(): pass")
        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "looks good"}
            result = json.loads(opencode_review_code(file_path=str(f)))
        assert result["success"] is True
        assert "review" in result

    def test_review_code_file_not_found(self):
        from tools.opencode_tool import opencode_review_code

        result = json.loads(opencode_review_code(file_path="/nonexistent.py"))
        assert result["success"] is False


class TestOpenCodeExplainCode:
    def test_explain_code_success(self):
        from tools.opencode_tool import opencode_explain_code

        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "this function does X"}
            result = json.loads(opencode_explain_code("def foo(): pass"))
        assert result["success"] is True
        assert "explanation" in result


class TestOpenCodeGenerateCode:
    def test_generate_code_success(self):
        from tools.opencode_tool import opencode_generate_code

        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {
                "success": True,
                "stdout": "def hello():\n    print('hi')",
            }
            result = json.loads(opencode_generate_code("a hello function"))
        assert result["success"] is True
        assert "code" in result

    def test_generate_code_with_output_file(self, tmp_path):
        from tools.opencode_tool import opencode_generate_code

        output = tmp_path / "generated.py"
        with patch("tools.opencode_tool._run_opencode_command") as mock_cmd:
            mock_cmd.return_value = {"success": True, "stdout": "def hello(): pass"}
            result = json.loads(
                opencode_generate_code("hello", output_file=str(output))
            )
        assert result["success"] is True
        assert result["output_file"] == str(output)
        assert output.exists()


class TestOpenCodeStatus:
    def test_status_not_installed(self):
        from tools.opencode_tool import opencode_status

        with patch("tools.opencode_tool._find_opencode_binary", return_value=None):
            result = json.loads(opencode_status())
        assert result["success"] is True
        assert result["installed"] is False

    def test_status_installed(self):
        from tools.opencode_tool import opencode_status

        with (
            patch(
                "tools.opencode_tool._find_opencode_binary",
                return_value="/usr/bin/opencode",
            ),
            patch(
                "subprocess.run", return_value=MagicMock(stdout="1.0.0", returncode=0)
            ),
        ):
            result = json.loads(opencode_status())
        assert result["success"] is True
        assert result["installed"] is True
        assert result["version"] == "1.0.0"


class TestOpenCodeRegistry:
    def test_tools_registered(self):
        from tools.registry import registry
        from tools import opencode_tool  # triggers registration

        tool_names = list(registry._tools.keys())
        assert "opencode_coding_task" in tool_names
        assert "opencode_edit_file" in tool_names
        assert "opencode_review_code" in tool_names
        assert "opencode_explain_code" in tool_names
        assert "opencode_generate_code" in tool_names
        assert "opencode_status" in tool_names

    def test_opencode_toolset_exists(self):
        from tools.toolsets import TOOLSETS

        assert "opencode" in TOOLSETS
        assert len(TOOLSETS["opencode"]["tools"]) == 6

    def test_opencode_tools_in_core_list(self):
        from tools.toolsets import _AIZEN_CORE_TOOLS

        assert "opencode_coding_task" in _AIZEN_CORE_TOOLS
        assert "opencode_status" in _AIZEN_CORE_TOOLS
