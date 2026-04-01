"""OpenCode Collaboration Tool for Aizen Agent

Enables bidirectional collaboration between Aizen Agent and OpenCode:
- Delegate coding tasks to OpenCode
- Share tool results and context
- Switch models between Aizen and OpenCode providers
- Real-time collaboration via MCP bridge
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import registry

from aizen_logging import get_logger, get_request_id

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# OpenCode CLI Integration
# ---------------------------------------------------------------------------


def _find_opencode_binary() -> Optional[str]:
    """Find the opencode CLI binary."""
    for path in [
        os.path.expanduser("~/.opencode/bin/opencode"),
        os.path.expanduser("~/.local/bin/opencode"),
        "/usr/local/bin/opencode",
        "/usr/bin/opencode",
    ]:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return (
        subprocess.run(
            ["which", "opencode"], capture_output=True, text=True
        ).stdout.strip()
        or None
    )


def _run_opencode_command(
    args: list, input_text: Optional[str] = None, timeout: int = 120
) -> Dict[str, Any]:
    """Run an opencode CLI command and return the result."""
    binary = _find_opencode_binary()
    if not binary:
        return {
            "success": False,
            "error": "OpenCode CLI not found. Install with: npm install -g @opencode-ai/opencode",
        }

    cmd = [binary] + args
    env = os.environ.copy()
    env["OPENCODE_NON_INTERACTIVE"] = "1"
    env["AIZEN_REQUEST_ID"] = get_request_id()

    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"OpenCode command timed out after {timeout}s",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# OpenCode Tool Functions
# ---------------------------------------------------------------------------


def opencode_coding_task(
    task: str,
    context: str = "",
    model: str = "",
    working_dir: str = "",
    task_id: str = None,
) -> str:
    """Delegate a coding task to OpenCode.

    OpenCode will execute the task using its own toolset and return results.
    This is useful for tasks that benefit from OpenCode's specialized coding capabilities.

    Args:
        task: The coding task description.
        context: Additional context (file contents, error messages, etc.).
        model: Optional model to use (e.g., 'opencode/qwen3.6-plus-free').
        working_dir: Working directory for the task.
    """
    logger.info("Delegating coding task to OpenCode: %s", task[:100])

    full_prompt = task
    if context:
        full_prompt = f"{task}\n\n--- Context ---\n{context}"

    args = ["run", "--prompt", full_prompt]
    if model:
        args.extend(["--model", model])

    workdir = working_dir or os.getcwd()
    result = _run_opencode_command(args, timeout=300)

    if not result["success"]:
        error_msg = result.get("error") or result.get("stderr", "Unknown error")
        return json.dumps(
            {
                "success": False,
                "error": f"OpenCode coding task failed: {error_msg}",
                "hint": "Make sure OpenCode is installed and configured. Run 'opencode login' to authenticate.",
            }
        )

    return json.dumps(
        {
            "success": True,
            "result": result.get("stdout", ""),
            "provider": "opencode",
            "model": model or "default",
        }
    )


def opencode_edit_file(
    file_path: str,
    instructions: str,
    model: str = "",
    task_id: str = None,
) -> str:
    """Ask OpenCode to edit a specific file.

    OpenCode will read the file, apply the requested changes, and return the result.

    Args:
        file_path: Path to the file to edit.
        instructions: What changes to make.
        model: Optional model to use.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        return json.dumps({"success": False, "error": f"File not found: {abs_path}"})

    logger.info("OpenCode editing file: %s", abs_path)

    prompt = (
        f"Edit the file at {abs_path} according to these instructions:\n{instructions}"
    )
    args = ["run", "--prompt", prompt]
    if model:
        args.extend(["--model", model])

    result = _run_opencode_command(args, timeout=300)

    if not result["success"]:
        error_msg = result.get("error") or result.get("stderr", "Unknown error")
        return json.dumps(
            {
                "success": False,
                "error": f"OpenCode file edit failed: {error_msg}",
            }
        )

    return json.dumps(
        {
            "success": True,
            "file": abs_path,
            "result": result.get("stdout", ""),
            "provider": "opencode",
        }
    )


def opencode_review_code(
    file_path: str = "",
    diff: str = "",
    instructions: str = "",
    model: str = "",
    task_id: str = None,
) -> str:
    """Ask OpenCode to review code or a diff.

    Args:
        file_path: Optional path to a file to review.
        diff: Optional diff to review.
        instructions: Specific review instructions (e.g., 'focus on security').
        model: Optional model to use.
    """
    prompt_parts = ["Please review the following code:"]

    if file_path:
        abs_path = os.path.abspath(file_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r") as f:
                prompt_parts.append(f"\n--- File: {abs_path} ---\n{f.read()}")
        else:
            return json.dumps(
                {"success": False, "error": f"File not found: {abs_path}"}
            )

    if diff:
        prompt_parts.append(f"\n--- Diff ---\n{diff}")

    if instructions:
        prompt_parts.append(f"\n--- Review Instructions ---\n{instructions}")

    prompt = "\n".join(prompt_parts)
    args = ["run", "--prompt", prompt]
    if model:
        args.extend(["--model", model])

    logger.info("OpenCode reviewing code")
    result = _run_opencode_command(args, timeout=300)

    if not result["success"]:
        error_msg = result.get("error") or result.get("stderr", "Unknown error")
        return json.dumps(
            {
                "success": False,
                "error": f"OpenCode code review failed: {error_msg}",
            }
        )

    return json.dumps(
        {
            "success": True,
            "review": result.get("stdout", ""),
            "provider": "opencode",
        }
    )


def opencode_explain_code(
    code: str,
    language: str = "",
    model: str = "",
    task_id: str = None,
) -> str:
    """Ask OpenCode to explain a piece of code.

    Args:
        code: The code to explain.
        language: Optional language hint (e.g., 'python', 'rust').
        model: Optional model to use.
    """
    prompt = f"Explain this code{' in ' + language if language else ''}:\n\n```{language}\n{code}\n```"
    args = ["run", "--prompt", prompt]
    if model:
        args.extend(["--model", model])

    logger.info("OpenCode explaining code")
    result = _run_opencode_command(args, timeout=120)

    if not result["success"]:
        error_msg = result.get("error") or result.get("stderr", "Unknown error")
        return json.dumps(
            {
                "success": False,
                "error": f"OpenCode code explanation failed: {error_msg}",
            }
        )

    return json.dumps(
        {
            "success": True,
            "explanation": result.get("stdout", ""),
            "provider": "opencode",
        }
    )


def opencode_generate_code(
    description: str,
    language: str = "python",
    output_file: str = "",
    model: str = "",
    task_id: str = None,
) -> str:
    """Ask OpenCode to generate code from a description.

    Args:
        description: What to generate.
        language: Target programming language.
        output_file: Optional file to write the generated code to.
        model: Optional model to use.
    """
    prompt = f"Generate {language} code for: {description}"
    args = ["run", "--prompt", prompt]
    if model:
        args.extend(["--model", model])

    logger.info("OpenCode generating code: %s", description[:100])
    result = _run_opencode_command(args, timeout=300)

    if not result["success"]:
        error_msg = result.get("error") or result.get("stderr", "Unknown error")
        return json.dumps(
            {
                "success": False,
                "error": f"OpenCode code generation failed: {error_msg}",
            }
        )

    generated = result.get("stdout", "")

    if output_file:
        abs_path = os.path.abspath(output_file)
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(generated)
            return json.dumps(
                {
                    "success": True,
                    "generated": True,
                    "output_file": abs_path,
                    "provider": "opencode",
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "success": True,
                    "generated": True,
                    "output_file": None,
                    "error": f"Could not write to {output_file}: {e}",
                    "code": generated,
                    "provider": "opencode",
                }
            )

    return json.dumps(
        {
            "success": True,
            "code": generated,
            "provider": "opencode",
        }
    )


def opencode_status(task_id: str = None) -> str:
    """Check OpenCode availability and configuration.

    Returns the current status of OpenCode integration.
    """
    binary = _find_opencode_binary()
    is_installed = binary is not None

    version = "unknown"
    if is_installed:
        try:
            result = subprocess.run(
                [binary, "--version"], capture_output=True, text=True, timeout=5
            )
            version = result.stdout.strip() or "unknown"
        except Exception:
            pass

    # Check OpenCode providers
    providers = []
    for key in ["OPENCODE_ZEN_API_KEY", "OPENCODE_GO_API_KEY"]:
        if os.getenv(key):
            providers.append(
                key.replace("_API_KEY", "").replace("OPENCODE_", "opencode-").lower()
            )

    return json.dumps(
        {
            "success": True,
            "installed": is_installed,
            "binary": binary,
            "version": version,
            "providers": providers,
            "available_models": [
                "opencode/qwen3.6-plus-free",
                "opencode/mimo-v2-omni-free",
                "opencode/minimax-m2.5-free",
                "opencode/kimi-k2-free",
                "opencode/glm-5-free",
            ],
        }
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def check_opencode_requirements() -> bool:
    """Check if OpenCode CLI is available."""
    return _find_opencode_binary() is not None


registry.register(
    name="opencode_coding_task",
    toolset="opencode",
    schema={
        "name": "opencode_coding_task",
        "description": "Delegate a coding task to OpenCode. OpenCode will execute the task using its own specialized toolset and return results. Use this for complex coding tasks that benefit from OpenCode's capabilities.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The coding task description",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context (file contents, error messages, etc.)",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model to use (e.g., 'opencode/qwen3.6-plus-free')",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for the task",
                },
            },
            "required": ["task"],
        },
    },
    handler=lambda args, **kw: opencode_coding_task(
        task=args.get("task", ""),
        context=args.get("context", ""),
        model=args.get("model", ""),
        working_dir=args.get("working_dir", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_opencode_requirements,
    requires_env=[],
    description="Delegate coding tasks to OpenCode",
    emoji="🤝",
)

registry.register(
    name="opencode_edit_file",
    toolset="opencode",
    schema={
        "name": "opencode_edit_file",
        "description": "Ask OpenCode to edit a specific file. OpenCode will read the file, apply changes, and return the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "instructions": {
                    "type": "string",
                    "description": "What changes to make",
                },
                "model": {"type": "string", "description": "Optional model to use"},
            },
            "required": ["file_path", "instructions"],
        },
    },
    handler=lambda args, **kw: opencode_edit_file(
        file_path=args.get("file_path", ""),
        instructions=args.get("instructions", ""),
        model=args.get("model", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_opencode_requirements,
    requires_env=[],
    description="Edit files with OpenCode",
    emoji="✏️",
)

registry.register(
    name="opencode_review_code",
    toolset="opencode",
    schema={
        "name": "opencode_review_code",
        "description": "Ask OpenCode to review code or a diff. Returns detailed feedback on code quality, security, performance, and best practices.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Optional path to a file to review",
                },
                "diff": {"type": "string", "description": "Optional diff to review"},
                "instructions": {
                    "type": "string",
                    "description": "Specific review instructions (e.g., 'focus on security')",
                },
                "model": {"type": "string", "description": "Optional model to use"},
            },
        },
    },
    handler=lambda args, **kw: opencode_review_code(
        file_path=args.get("file_path", ""),
        diff=args.get("diff", ""),
        instructions=args.get("instructions", ""),
        model=args.get("model", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_opencode_requirements,
    requires_env=[],
    description="Code review with OpenCode",
    emoji="🔍",
)

registry.register(
    name="opencode_explain_code",
    toolset="opencode",
    schema={
        "name": "opencode_explain_code",
        "description": "Ask OpenCode to explain a piece of code. Returns a detailed explanation of what the code does, how it works, and potential improvements.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to explain"},
                "language": {
                    "type": "string",
                    "description": "Optional language hint (e.g., 'python', 'rust')",
                },
                "model": {"type": "string", "description": "Optional model to use"},
            },
            "required": ["code"],
        },
    },
    handler=lambda args, **kw: opencode_explain_code(
        code=args.get("code", ""),
        language=args.get("language", ""),
        model=args.get("model", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_opencode_requirements,
    requires_env=[],
    description="Explain code with OpenCode",
    emoji="💡",
)

registry.register(
    name="opencode_generate_code",
    toolset="opencode",
    schema={
        "name": "opencode_generate_code",
        "description": "Ask OpenCode to generate code from a description. Can optionally write the output to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What to generate"},
                "language": {
                    "type": "string",
                    "description": "Target programming language",
                    "default": "python",
                },
                "output_file": {
                    "type": "string",
                    "description": "Optional file to write the generated code to",
                },
                "model": {"type": "string", "description": "Optional model to use"},
            },
            "required": ["description"],
        },
    },
    handler=lambda args, **kw: opencode_generate_code(
        description=args.get("description", ""),
        language=args.get("language", "python"),
        output_file=args.get("output_file", ""),
        model=args.get("model", ""),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_opencode_requirements,
    requires_env=[],
    description="Generate code with OpenCode",
    emoji="⚡",
)

registry.register(
    name="opencode_status",
    toolset="opencode",
    schema={
        "name": "opencode_status",
        "description": "Check OpenCode availability, version, and configured providers.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    handler=lambda args, **kw: opencode_status(task_id=kw.get("task_id")),
    check_fn=lambda: True,
    requires_env=[],
    description="Check OpenCode status",
    emoji="📊",
)
