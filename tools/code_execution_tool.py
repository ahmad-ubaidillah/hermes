#!/usr/bin/env python3
"""
Code Execution Tool -- Programmatic Tool Calling (PTC)

Lets the LLM write a Python script that calls Hermes tools via RPC,
collapsing multi-step tool chains into a single inference turn.

Architecture:
  1. Parent generates a `hermes_tools.py` stub module with RPC functions
  2. Parent opens a Unix domain socket and starts an RPC listener thread
  3. Parent spawns a child process that runs the LLM's script
  4. When the script calls a tool function, the call travels over the UDS
     back to the parent, which dispatches through handle_function_call
  5. Only the script's stdout is returned to the LLM; intermediate tool
     results never enter the context window

Platform: Linux / macOS only (Unix domain sockets). Disabled on Windows.
"""

import json
import logging
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

_IS_WINDOWS = platform.system() == "Windows"
from typing import Any, Dict, List, Optional

# Availability gate: UDS requires a POSIX OS
logger = logging.getLogger(__name__)

SANDBOX_AVAILABLE = sys.platform != "win32"

# The 7 tools allowed inside the sandbox. The intersection of this list
# and the session's enabled tools determines which stubs are generated.
SANDBOX_ALLOWED_TOOLS = frozenset(
    [
        "web_search",
        "web_extract",
        "read_file",
        "write_file",
        "search_files",
        "patch",
        "terminal",
    ]
)

# Resource limit defaults (overridable via config.yaml → code_execution.*)
DEFAULT_TIMEOUT = 300  # 5 minutes
DEFAULT_MAX_TOOL_CALLS = 50
MAX_STDOUT_BYTES = 50_000  # 50 KB
MAX_STDERR_BYTES = 10_000  # 10 KB

# Docker sandbox defaults
DEFAULT_DOCKER_CPU = 0.5
DEFAULT_DOCKER_MEMORY = "256m"
DEFAULT_DOCKER_PIDS_LIMIT = 64
DEFAULT_DOCKER_NETWORK = "none"
DEFAULT_DOCKER_DISK_READ_BPS = "10mb"
DEFAULT_DOCKER_DISK_WRITE_BPS = "10mb"
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"
DEFAULT_DOCKER_TMPFS_SIZE = "64m"
DEFAULT_DOCKER_ROOTFS_SIZE = "128m"


def check_sandbox_requirements() -> bool:
    """Code execution sandbox requires a POSIX OS for Unix domain sockets."""
    return SANDBOX_AVAILABLE


# ---------------------------------------------------------------------------
# hermes_tools.py code generator
# ---------------------------------------------------------------------------

# Per-tool stub templates: (function_name, signature, docstring, args_dict_expr)
# The args_dict_expr builds the JSON payload sent over the RPC socket.
_TOOL_STUBS = {
    "web_search": (
        "web_search",
        "query: str, limit: int = 5",
        '"""Search the web. Returns dict with data.web list of {url, title, description}."""',
        '{"query": query, "limit": limit}',
    ),
    "web_extract": (
        "web_extract",
        "urls: list",
        '"""Extract content from URLs. Returns dict with results list of {url, title, content, error}."""',
        '{"urls": urls}',
    ),
    "read_file": (
        "read_file",
        "path: str, offset: int = 1, limit: int = 500",
        '"""Read a file (1-indexed lines). Returns dict with "content" and "total_lines"."""',
        '{"path": path, "offset": offset, "limit": limit}',
    ),
    "write_file": (
        "write_file",
        "path: str, content: str",
        '"""Write content to a file (always overwrites). Returns dict with status."""',
        '{"path": path, "content": content}',
    ),
    "search_files": (
        "search_files",
        'pattern: str, target: str = "content", path: str = ".", file_glob: str = None, limit: int = 50, offset: int = 0, output_mode: str = "content", context: int = 0',
        '"""Search file contents (target="content") or find files by name (target="files"). Returns dict with "matches"."""',
        '{"pattern": pattern, "target": target, "path": path, "file_glob": file_glob, "limit": limit, "offset": offset, "output_mode": output_mode, "context": context}',
    ),
    "patch": (
        "patch",
        'path: str = None, old_string: str = None, new_string: str = None, replace_all: bool = False, mode: str = "replace", patch: str = None',
        '"""Targeted find-and-replace (mode="replace") or V4A multi-file patches (mode="patch"). Returns dict with status."""',
        '{"path": path, "old_string": old_string, "new_string": new_string, "replace_all": replace_all, "mode": mode, "patch": patch}',
    ),
    "terminal": (
        "terminal",
        "command: str, timeout: int = None, workdir: str = None",
        '"""Run a shell command (foreground only). Returns dict with "output" and "exit_code"."""',
        '{"command": command, "timeout": timeout, "workdir": workdir}',
    ),
}


def generate_hermes_tools_module(enabled_tools: List[str]) -> str:
    """
    Build the source code for the hermes_tools.py stub module.

    Only tools in both SANDBOX_ALLOWED_TOOLS and enabled_tools get stubs.
    """
    tools_to_generate = sorted(SANDBOX_ALLOWED_TOOLS & set(enabled_tools))

    stub_functions = []
    export_names = []
    for tool_name in tools_to_generate:
        if tool_name not in _TOOL_STUBS:
            continue
        func_name, sig, doc, args_expr = _TOOL_STUBS[tool_name]
        stub_functions.append(
            f"def {func_name}({sig}):\n"
            f"    {doc}\n"
            f"    return _call({func_name!r}, {args_expr})\n"
        )
        export_names.append(func_name)

    header = '''\
"""Auto-generated Hermes tools RPC stubs."""
import json, os, socket, shlex, time

_sock = None


# ---------------------------------------------------------------------------
# Convenience helpers (avoid common scripting pitfalls)
# ---------------------------------------------------------------------------

def json_parse(text: str):
    """Parse JSON tolerant of control characters (strict=False).
    Use this instead of json.loads() when parsing output from terminal()
    or web_extract() that may contain raw tabs/newlines in strings."""
    return json.loads(text, strict=False)


def shell_quote(s: str) -> str:
    """Shell-escape a string for safe interpolation into commands.
    Use this when inserting dynamic content into terminal() commands:
        terminal(f"echo {shell_quote(user_input)}")
    """
    return shlex.quote(s)


def retry(fn, max_attempts=3, delay=2):
    """Retry a function up to max_attempts times with exponential backoff.
    Use for transient failures (network errors, API rate limits):
        result = retry(lambda: terminal("gh issue list ..."))
    """
    last_err = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < max_attempts - 1:
                time.sleep(delay * (2 ** attempt))
    raise last_err

def _connect():
    global _sock
    if _sock is None:
        _sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        _sock.connect(os.environ["HERMES_RPC_SOCKET"])
        _sock.settimeout(300)
    return _sock

def _call(tool_name, args):
    """Send a tool call to the parent process and return the parsed result."""
    conn = _connect()
    request = json.dumps({"tool": tool_name, "args": args}) + "\\n"
    conn.sendall(request.encode())
    buf = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            raise RuntimeError("Agent process disconnected")
        buf += chunk
        if buf.endswith(b"\\n"):
            break
    raw = buf.decode().strip()
    result = json.loads(raw)
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result
    return result

'''

    return header + "\n".join(stub_functions)


# ---------------------------------------------------------------------------
# RPC server (runs in a thread inside the parent process)
# ---------------------------------------------------------------------------

# Terminal parameters that must not be used from ephemeral sandbox scripts
_TERMINAL_BLOCKED_PARAMS = {"background", "check_interval", "pty"}


def _rpc_server_loop(
    server_sock: socket.socket,
    task_id: str,
    tool_call_log: list,
    tool_call_counter: list,  # mutable [int] so the thread can increment
    max_tool_calls: int,
    allowed_tools: frozenset,
):
    """
    Accept one client connection and dispatch tool-call requests until
    the client disconnects or the call limit is reached.
    """
    from tools.model_tools import handle_function_call

    conn = None
    try:
        server_sock.settimeout(5)
        conn, _ = server_sock.accept()
        conn.settimeout(300)

        buf = b""
        while True:
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk

            # Process all complete newline-delimited messages in the buffer
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue

                call_start = time.monotonic()
                try:
                    request = json.loads(line.decode())
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    resp = json.dumps({"error": f"Invalid RPC request: {exc}"})
                    conn.sendall((resp + "\n").encode())
                    continue

                tool_name = request.get("tool", "")
                tool_args = request.get("args", {})

                # Enforce the allow-list
                if tool_name not in allowed_tools:
                    available = ", ".join(sorted(allowed_tools))
                    resp = json.dumps(
                        {
                            "error": (
                                f"Tool '{tool_name}' is not available in execute_code. "
                                f"Available: {available}"
                            )
                        }
                    )
                    conn.sendall((resp + "\n").encode())
                    continue

                # Enforce tool call limit
                if tool_call_counter[0] >= max_tool_calls:
                    resp = json.dumps(
                        {
                            "error": (
                                f"Tool call limit reached ({max_tool_calls}). "
                                "No more tool calls allowed in this execution."
                            )
                        }
                    )
                    conn.sendall((resp + "\n").encode())
                    continue

                # Strip forbidden terminal parameters
                if tool_name == "terminal" and isinstance(tool_args, dict):
                    for param in _TERMINAL_BLOCKED_PARAMS:
                        tool_args.pop(param, None)

                # Dispatch through the standard tool handler.
                # Suppress stdout/stderr from internal tool handlers so
                # their status prints don't leak into the CLI spinner.
                try:
                    _real_stdout, _real_stderr = sys.stdout, sys.stderr
                    devnull = open(os.devnull, "w")
                    try:
                        sys.stdout = devnull
                        sys.stderr = devnull
                        result = handle_function_call(
                            tool_name, tool_args, task_id=task_id
                        )
                    finally:
                        sys.stdout, sys.stderr = _real_stdout, _real_stderr
                        devnull.close()
                except Exception as exc:
                    logger.error("Tool call failed in sandbox: %s", exc, exc_info=True)
                    result = json.dumps({"error": str(exc)})

                tool_call_counter[0] += 1
                call_duration = time.monotonic() - call_start

                # Log for observability
                args_preview = str(tool_args)[:80]
                tool_call_log.append(
                    {
                        "tool": tool_name,
                        "args_preview": args_preview,
                        "duration": round(call_duration, 2),
                    }
                )

                conn.sendall((result + "\n").encode())

    except socket.timeout:
        logger.debug("RPC listener socket timeout")
    except OSError as e:
        logger.debug("RPC listener socket error: %s", e, exc_info=True)
    finally:
        if conn:
            try:
                conn.close()
            except OSError as e:
                logger.debug("RPC conn close error: %s", e)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def execute_code(
    code: str,
    task_id: Optional[str] = None,
    enabled_tools: Optional[List[str]] = None,
) -> str:
    """
    Run a Python script in a sandboxed environment with RPC access
    to a subset of Hermes tools.

    Dispatches to subprocess (default) or Docker mode based on config.

    Args:
        code:          Python source code to execute.
        task_id:       Session task ID for tool isolation (terminal env, etc.).
        enabled_tools: Tool names enabled in the current session. The sandbox
                       gets the intersection with SANDBOX_ALLOWED_TOOLS.

    Returns:
        JSON string with execution results.
    """
    if not SANDBOX_AVAILABLE:
        return json.dumps(
            {
                "error": "execute_code is not available on Windows. Use normal tool calls instead."
            }
        )

    if not code or not code.strip():
        return json.dumps({"error": "No code provided."})

    _cfg = _load_config()

    session_tools = set(enabled_tools) if enabled_tools else set()
    sandbox_tools = frozenset(SANDBOX_ALLOWED_TOOLS & session_tools)
    if not sandbox_tools:
        sandbox_tools = SANDBOX_ALLOWED_TOOLS

    mode = _cfg.get("mode", "subprocess")
    if mode == "docker":
        return _execute_in_docker(code, task_id, sandbox_tools, _cfg)
    return _execute_subprocess(code, task_id, sandbox_tools, _cfg)


def _find_docker() -> Optional[str]:
    """Locate the docker CLI binary."""
    return shutil.which("docker")


def _cleanup_docker_container(docker_exe: str, container_id: str):
    """Kill and remove a Docker container, suppressing errors."""
    try:
        subprocess.run(
            [docker_exe, "kill", container_id],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    try:
        subprocess.run(
            [docker_exe, "rm", "-f", container_id],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


def _execute_in_docker(
    code: str,
    task_id: Optional[str],
    sandbox_tools: frozenset,
    cfg: dict,
) -> str:
    """Run Python code inside a hardened Docker container with RPC access."""
    from tools.terminal_tool import _interrupt_event

    docker_exe = _find_docker()
    if not docker_exe:
        logger.warning(
            "Docker mode requested but docker CLI not found; falling back to subprocess"
        )
        return _execute_subprocess(code, task_id, sandbox_tools, cfg)

    import shutil as _shutil

    timeout = cfg.get("timeout", DEFAULT_TIMEOUT)
    max_tool_calls = cfg.get("max_tool_calls", DEFAULT_MAX_TOOL_CALLS)
    docker_cpu = cfg.get("docker_cpu", DEFAULT_DOCKER_CPU)
    docker_memory = cfg.get("docker_memory", DEFAULT_DOCKER_MEMORY)
    docker_pids_limit = cfg.get("docker_pids_limit", DEFAULT_DOCKER_PIDS_LIMIT)
    docker_network = cfg.get("docker_network", DEFAULT_DOCKER_NETWORK)
    docker_disk_read_bps = cfg.get("docker_disk_read_bps", DEFAULT_DOCKER_DISK_READ_BPS)
    docker_disk_write_bps = cfg.get(
        "docker_disk_write_bps", DEFAULT_DOCKER_DISK_WRITE_BPS
    )
    docker_image = cfg.get("docker_image", DEFAULT_DOCKER_IMAGE)

    tmpdir = tempfile.mkdtemp(prefix="hermes_docker_")
    container_id: Optional[str] = None
    exec_start = time.monotonic()
    tool_call_log: list = []
    tool_call_counter = [0]
    server_sock = None
    status = "success"

    try:
        tools_src = generate_hermes_tools_module(list(sandbox_tools))
        with open(os.path.join(tmpdir, "hermes_tools.py"), "w") as f:
            f.write(tools_src)
        with open(os.path.join(tmpdir, "script.py"), "w") as f:
            f.write(code)

        # TCP RPC server (UDS cannot cross container boundaries)
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        rpc_port = server_sock.getsockname()[1]

        rpc_thread = threading.Thread(
            target=_rpc_server_loop,
            args=(
                server_sock,
                task_id,
                tool_call_log,
                tool_call_counter,
                max_tool_calls,
                sandbox_tools,
            ),
            daemon=True,
        )
        rpc_thread.start()

        # Build Docker command
        container_name = f"hermes-exec-{uuid.uuid4().hex[:12]}"
        cmd = [
            docker_exe,
            "run",
            "-d",
            "--name",
            container_name,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(docker_pids_limit),
            "--cpus",
            str(docker_cpu),
            "--memory",
            str(docker_memory),
            "--network",
            docker_network,
            "--tmpfs",
            f"/tmp:rw,nosuid,size={DEFAULT_DOCKER_TMPFS_SIZE}",
            "--tmpfs",
            f"/root:rw,exec,size={DEFAULT_DOCKER_ROOTFS_SIZE}",
            "-v",
            f"{tmpdir}:/sandbox:ro",
            "-w",
            "/sandbox",
        ]

        if docker_disk_read_bps:
            cmd.extend(["--device-read-bps", f"/dev/sda:{docker_disk_read_bps}"])
        if docker_disk_write_bps:
            cmd.extend(["--device-write-bps", f"/dev/sda:{docker_disk_write_bps}"])

        if docker_network == "none":
            cmd.extend(["--add-host", "host.docker.internal:host-gateway"])

        cmd.extend([docker_image, "python", "/sandbox/script.py"])

        # Build child env (same filtering as subprocess mode)
        child_env = _build_child_env()
        child_env["HERMES_RPC_HOST"] = "host.docker.internal"
        child_env["HERMES_RPC_PORT"] = str(rpc_port)
        # Convert RPC stubs to use TCP when these vars are present
        child_env["HERMES_RPC_MODE"] = "tcp"

        # Pass env via -e flags
        for k, v in child_env.items():
            cmd.extend(["-e", f"{k}={v}"])

        logger.debug("Docker run command: %s", " ".join(cmd))
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=True
        )
        container_id = result.stdout.strip()

        # Poll for container exit
        deadline = time.monotonic() + timeout
        while True:
            if _interrupt_event.is_set():
                _cleanup_docker_container(docker_exe, container_id)
                container_id = None
                status = "interrupted"
                break
            if time.monotonic() > deadline:
                _cleanup_docker_container(docker_exe, container_id)
                container_id = None
                status = "timeout"
                break
            inspect = subprocess.run(
                [docker_exe, "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.stdout.strip() == "false":
                break
            time.sleep(0.3)

        # Collect stdout/stderr from container logs
        stdout_text = ""
        stderr_text = ""
        if container_id:
            try:
                logs = subprocess.run(
                    [docker_exe, "logs", container_id],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                stdout_text = logs.stdout or ""
                stderr_text = logs.stderr or ""
            except Exception as e:
                stderr_text = f"Could not retrieve container logs: {e}"

        exit_code = -1
        if container_id:
            try:
                inspect = subprocess.run(
                    [docker_exe, "inspect", "-f", "{{.State.ExitCode}}", container_id],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                exit_code = int(inspect.stdout.strip())
            except Exception:
                pass

        # Truncate stdout
        from tools.ansi_strip import strip_ansi

        stdout_text = strip_ansi(stdout_text)
        stderr_text = strip_ansi(stderr_text)

        total_stdout = len(stdout_text)
        if total_stdout > MAX_STDOUT_BYTES:
            head = stdout_text[: int(MAX_STDOUT_BYTES * 0.4)]
            tail = stdout_text[-(MAX_STDOUT_BYTES - len(head)) :]
            omitted = total_stdout - len(head) - len(tail)
            truncated_notice = (
                f"\n\n... [OUTPUT TRUNCATED - {omitted:,} chars omitted "
                f"out of {total_stdout:,} total] ...\n\n"
            )
            stdout_text = head + truncated_notice + tail

        duration = round(time.monotonic() - exec_start, 2)

        server_sock.close()
        server_sock = None
        rpc_thread.join(timeout=3)

        result_dict: Dict[str, Any] = {
            "status": status,
            "output": stdout_text,
            "tool_calls_made": tool_call_counter[0],
            "duration_seconds": duration,
        }

        if status == "timeout":
            result_dict["error"] = f"Script timed out after {timeout}s and was killed."
        elif status == "interrupted":
            result_dict["output"] = (
                stdout_text + "\n[execution interrupted — user sent a new message]"
            )
        elif exit_code != 0:
            result_dict["status"] = "error"
            result_dict["error"] = stderr_text or f"Script exited with code {exit_code}"
            if stderr_text:
                result_dict["output"] = stdout_text + "\n--- stderr ---\n" + stderr_text

        return json.dumps(result_dict, ensure_ascii=False)

    except subprocess.TimeoutExpired:
        duration = round(time.monotonic() - exec_start, 2)
        if container_id:
            _cleanup_docker_container(docker_exe, container_id)
        return json.dumps(
            {
                "status": "timeout",
                "error": f"Script timed out after {timeout}s and was killed.",
                "tool_calls_made": tool_call_counter[0],
                "duration_seconds": duration,
            }
        )
    except Exception as exc:
        duration = round(time.monotonic() - exec_start, 2)
        logger.error(
            "execute_code (docker) failed after %ss with %d tool calls: %s: %s",
            duration,
            tool_call_counter[0],
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        if container_id:
            _cleanup_docker_container(docker_exe, container_id)
        return json.dumps(
            {
                "status": "error",
                "error": str(exc),
                "tool_calls_made": tool_call_counter[0],
                "duration_seconds": duration,
            },
            ensure_ascii=False,
        )
    finally:
        if server_sock is not None:
            try:
                server_sock.close()
            except OSError:
                pass
        if container_id and docker_exe:
            _cleanup_docker_container(docker_exe, container_id)
        _shutil.rmtree(tmpdir, ignore_errors=True)


def _build_child_env() -> dict:
    """Build a filtered environment for the sandboxed process."""
    _SAFE_ENV_PREFIXES = (
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_",
        "TERM",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SHELL",
        "LOGNAME",
        "XDG_",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "CONDA",
    )
    _SECRET_SUBSTRINGS = (
        "KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
        "CREDENTIAL",
        "PASSWD",
        "AUTH",
    )
    try:
        from tools.env_passthrough import is_env_passthrough as _is_passthrough
    except Exception:
        _is_passthrough = lambda _: False
    child_env = {}
    for k, v in os.environ.items():
        if _is_passthrough(k):
            child_env[k] = v
            continue
        if any(s in k.upper() for s in _SECRET_SUBSTRINGS):
            continue
        if any(k.startswith(p) for p in _SAFE_ENV_PREFIXES):
            child_env[k] = v
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    _hermes_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _existing_pp = child_env.get("PYTHONPATH", "")
    child_env["PYTHONPATH"] = _hermes_root + (
        os.pathsep + _existing_pp if _existing_pp else ""
    )
    _tz_name = os.getenv("HERMES_TIMEZONE", "").strip()
    if _tz_name:
        child_env["TZ"] = _tz_name
    return child_env


def _execute_subprocess(
    code: str,
    task_id: Optional[str],
    sandbox_tools: frozenset,
    cfg: dict,
) -> str:
    """Run Python code in a sandboxed subprocess with RPC access to Hermes tools.

    This is the original execution path — unchanged from the prior implementation.
    """
    from tools.terminal_tool import _interrupt_event

    timeout = cfg.get("timeout", DEFAULT_TIMEOUT)
    max_tool_calls = cfg.get("max_tool_calls", DEFAULT_MAX_TOOL_CALLS)

    tmpdir = tempfile.mkdtemp(prefix="hermes_sandbox_")
    _sock_tmpdir = "/tmp" if sys.platform == "darwin" else tempfile.gettempdir()
    sock_path = os.path.join(_sock_tmpdir, f"hermes_rpc_{uuid.uuid4().hex}.sock")

    tool_call_log: list = []
    tool_call_counter = [0]
    exec_start = time.monotonic()
    server_sock = None

    try:
        tools_src = generate_hermes_tools_module(list(sandbox_tools))
        with open(os.path.join(tmpdir, "hermes_tools.py"), "w") as f:
            f.write(tools_src)

        with open(os.path.join(tmpdir, "script.py"), "w") as f:
            f.write(code)

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(sock_path)
        server_sock.listen(1)

        rpc_thread = threading.Thread(
            target=_rpc_server_loop,
            args=(
                server_sock,
                task_id,
                tool_call_log,
                tool_call_counter,
                max_tool_calls,
                sandbox_tools,
            ),
            daemon=True,
        )
        rpc_thread.start()

        child_env = _build_child_env()
        child_env["HERMES_RPC_SOCKET"] = sock_path

        proc = subprocess.Popen(
            [sys.executable, "script.py"],
            cwd=tmpdir,
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            preexec_fn=None if _IS_WINDOWS else os.setsid,
        )

        deadline = time.monotonic() + timeout
        stderr_chunks: list = []

        _STDOUT_HEAD_BYTES = int(MAX_STDOUT_BYTES * 0.4)
        _STDOUT_TAIL_BYTES = MAX_STDOUT_BYTES - _STDOUT_HEAD_BYTES

        def _drain(pipe, chunks, max_bytes):
            total = 0
            try:
                while True:
                    data = pipe.read(4096)
                    if not data:
                        break
                    if total < max_bytes:
                        keep = max_bytes - total
                        chunks.append(data[:keep])
                    total += len(data)
            except (ValueError, OSError) as e:
                logger.debug("Error reading process output: %s", e, exc_info=True)

        stdout_total_bytes = [0]

        def _drain_head_tail(
            pipe, head_chunks, tail_chunks, head_bytes, tail_bytes, total_ref
        ):
            head_collected = 0
            from collections import deque

            tail_buf = deque()
            tail_collected = 0
            try:
                while True:
                    data = pipe.read(4096)
                    if not data:
                        break
                    total_ref[0] += len(data)
                    if head_collected < head_bytes:
                        keep = min(len(data), head_bytes - head_collected)
                        head_chunks.append(data[:keep])
                        head_collected += keep
                        data = data[keep:]
                        if not data:
                            continue
                    tail_buf.append(data)
                    tail_collected += len(data)
                    while tail_collected > tail_bytes and tail_buf:
                        oldest = tail_buf.popleft()
                        tail_collected -= len(oldest)
            except (ValueError, OSError):
                pass
            tail_chunks.extend(tail_buf)

        stdout_head_chunks: list = []
        stdout_tail_chunks: list = []

        stdout_reader = threading.Thread(
            target=_drain_head_tail,
            args=(
                proc.stdout,
                stdout_head_chunks,
                stdout_tail_chunks,
                _STDOUT_HEAD_BYTES,
                _STDOUT_TAIL_BYTES,
                stdout_total_bytes,
            ),
            daemon=True,
        )
        stderr_reader = threading.Thread(
            target=_drain,
            args=(proc.stderr, stderr_chunks, MAX_STDERR_BYTES),
            daemon=True,
        )
        stdout_reader.start()
        stderr_reader.start()

        status = "success"
        while proc.poll() is None:
            if _interrupt_event.is_set():
                _kill_process_group(proc)
                status = "interrupted"
                break
            if time.monotonic() > deadline:
                _kill_process_group(proc, escalate=True)
                status = "timeout"
                break
            time.sleep(0.2)

        stdout_reader.join(timeout=3)
        stderr_reader.join(timeout=3)

        stdout_head = b"".join(stdout_head_chunks).decode("utf-8", errors="replace")
        stdout_tail = b"".join(stdout_tail_chunks).decode("utf-8", errors="replace")
        stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")

        total_stdout = stdout_total_bytes[0]
        if total_stdout > MAX_STDOUT_BYTES and stdout_tail:
            omitted = total_stdout - len(stdout_head) - len(stdout_tail)
            truncated_notice = (
                f"\n\n... [OUTPUT TRUNCATED - {omitted:,} chars omitted "
                f"out of {total_stdout:,} total] ...\n\n"
            )
            stdout_text = stdout_head + truncated_notice + stdout_tail
        else:
            stdout_text = stdout_head + stdout_tail

        exit_code = proc.returncode if proc.returncode is not None else -1
        duration = round(time.monotonic() - exec_start, 2)

        server_sock.close()
        server_sock = None
        rpc_thread.join(timeout=3)

        from tools.ansi_strip import strip_ansi

        stdout_text = strip_ansi(stdout_text)
        stderr_text = strip_ansi(stderr_text)

        result: Dict[str, Any] = {
            "status": status,
            "output": stdout_text,
            "tool_calls_made": tool_call_counter[0],
            "duration_seconds": duration,
        }

        if status == "timeout":
            result["error"] = f"Script timed out after {timeout}s and was killed."
        elif status == "interrupted":
            result["output"] = (
                stdout_text + "\n[execution interrupted — user sent a new message]"
            )
        elif exit_code != 0:
            result["status"] = "error"
            result["error"] = stderr_text or f"Script exited with code {exit_code}"
            if stderr_text:
                result["output"] = stdout_text + "\n--- stderr ---\n" + stderr_text

        return json.dumps(result, ensure_ascii=False)

    except Exception as exc:
        duration = round(time.monotonic() - exec_start, 2)
        logger.error(
            "execute_code failed after %ss with %d tool calls: %s: %s",
            duration,
            tool_call_counter[0],
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return json.dumps(
            {
                "status": "error",
                "error": str(exc),
                "tool_calls_made": tool_call_counter[0],
                "duration_seconds": duration,
            },
            ensure_ascii=False,
        )

    finally:
        if server_sock is not None:
            try:
                server_sock.close()
            except OSError as e:
                logger.debug("Server socket close error: %s", e)
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)
        try:
            os.unlink(sock_path)
        except OSError:
            pass


def _kill_process_group(proc, escalate: bool = False):
    """Kill the child and its entire process group."""
    try:
        if _IS_WINDOWS:
            proc.terminate()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError) as e:
        logger.debug("Could not kill process group: %s", e, exc_info=True)
        try:
            proc.kill()
        except Exception as e2:
            logger.debug("Could not kill process: %s", e2, exc_info=True)

    if escalate:
        # Give the process 5s to exit after SIGTERM, then SIGKILL
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                if _IS_WINDOWS:
                    proc.kill()
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError) as e:
                logger.debug(
                    "Could not kill process group with SIGKILL: %s", e, exc_info=True
                )
                try:
                    proc.kill()
                except Exception as e2:
                    logger.debug("Could not kill process: %s", e2, exc_info=True)


def _load_config() -> dict:
    """Load code_execution config from CLI_CONFIG if available."""
    try:
        from cli import CLI_CONFIG

        return CLI_CONFIG.get("code_execution", {})
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# OpenAI Function-Calling Schema
# ---------------------------------------------------------------------------

# Per-tool documentation lines for the execute_code description.
# Ordered to match the canonical display order.
_TOOL_DOC_LINES = [
    (
        "web_search",
        "  web_search(query: str, limit: int = 5) -> dict\n"
        '    Returns {"data": {"web": [{"url", "title", "description"}, ...]}}',
    ),
    (
        "web_extract",
        "  web_extract(urls: list[str]) -> dict\n"
        '    Returns {"results": [{"url", "title", "content", "error"}, ...]} where content is markdown',
    ),
    (
        "read_file",
        "  read_file(path: str, offset: int = 1, limit: int = 500) -> dict\n"
        '    Lines are 1-indexed. Returns {"content": "...", "total_lines": N}',
    ),
    (
        "write_file",
        "  write_file(path: str, content: str) -> dict\n"
        "    Always overwrites the entire file.",
    ),
    (
        "search_files",
        '  search_files(pattern: str, target="content", path=".", file_glob=None, limit=50) -> dict\n'
        '    target: "content" (search inside files) or "files" (find files by name). Returns {"matches": [...]}',
    ),
    (
        "patch",
        "  patch(path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict\n"
        "    Replaces old_string with new_string in the file.",
    ),
    (
        "terminal",
        "  terminal(command: str, timeout=None, workdir=None) -> dict\n"
        '    Foreground only (no background/pty). Returns {"output": "...", "exit_code": N}',
    ),
]


def build_execute_code_schema(
    enabled_sandbox_tools: Optional[frozenset] = None,
) -> dict:
    """Build the execute_code schema with description listing only enabled tools.

    When tools are disabled via ``hermes tools`` (e.g. web is turned off),
    the schema description should NOT mention web_search / web_extract —
    otherwise the model thinks they are available and keeps trying to use them.
    """
    if enabled_sandbox_tools is None:
        enabled_sandbox_tools = SANDBOX_ALLOWED_TOOLS
    else:
        enabled_sandbox_tools = frozenset(enabled_sandbox_tools)

    # Build tool documentation lines for only the enabled tools
    tool_lines = "\n".join(
        doc for name, doc in _TOOL_DOC_LINES if name in enabled_sandbox_tools
    )

    # Build example import list from enabled tools
    import_examples = [
        n for n in ("web_search", "terminal") if n in enabled_sandbox_tools
    ]
    if not import_examples:
        import_examples = sorted(enabled_sandbox_tools)[:2]
    if import_examples:
        import_str = ", ".join(import_examples) + ", ..."
    else:
        import_str = "..."

    description = (
        "Run a Python script that can call Hermes tools programmatically. "
        "Use this when you need 3+ tool calls with processing logic between them, "
        "need to filter/reduce large tool outputs before they enter your context, "
        "need conditional branching (if X then Y else Z), or need to loop "
        "(fetch N pages, process N files, retry on failure).\n\n"
        "Use normal tool calls instead when: single tool call with no processing, "
        "you need to see the full result and apply complex reasoning, "
        "or the task requires interactive user input.\n\n"
        f"Available via `from hermes_tools import ...`:\n\n"
        f"{tool_lines}\n\n"
        "Limits: 5-minute timeout, 50KB stdout cap, max 50 tool calls per script. "
        "terminal() is foreground-only (no background or pty).\n\n"
        "Print your final result to stdout. Use Python stdlib (json, re, math, csv, "
        "datetime, collections, etc.) for processing between tool calls.\n\n"
        "Also available (no import needed — built into hermes_tools):\n"
        "  json_parse(text: str) — json.loads with strict=False; use for terminal() output with control chars\n"
        "  shell_quote(s: str) — shlex.quote(); use when interpolating dynamic strings into shell commands\n"
        "  retry(fn, max_attempts=3, delay=2) — retry with exponential backoff for transient failures"
    )

    return {
        "name": "execute_code",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": (
                        "Python code to execute. Import tools with "
                        f"`from hermes_tools import {import_str}` "
                        "and print your final result to stdout."
                    ),
                },
            },
            "required": ["code"],
        },
    }


# Default schema used at registration time (all sandbox tools listed)
EXECUTE_CODE_SCHEMA = build_execute_code_schema()


# --- Registry ---
from tools.registry import registry

registry.register(
    name="execute_code",
    toolset="code_execution",
    schema=EXECUTE_CODE_SCHEMA,
    handler=lambda args, **kw: execute_code(
        code=args.get("code", ""),
        task_id=kw.get("task_id"),
        enabled_tools=kw.get("enabled_tools"),
    ),
    check_fn=check_sandbox_requirements,
    emoji="🐍",
)
