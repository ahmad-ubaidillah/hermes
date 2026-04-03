"""Tool execution helpers - parallelization, path scoping, sanitization."""

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Parallelization Constants
# =============================================================================

# Tools that must never run concurrently (interactive / user-facing).
# When any of these appear in a batch, we fall back to sequential execution.
_NEVER_PARALLEL_TOOLS = frozenset({"clarify"})

# Read-only tools with no shared mutable session state.
_PARALLEL_SAFE_TOOLS = frozenset(
    {
        "ha_get_state",
        "ha_list_entities",
        "ha_list_services",
        "read_file",
        "search_files",
        "session_search",
        "skill_view",
        "skills_list",
        "vision_analyze",
        "web_extract",
        "web_search",
    }
)

# File tools can run concurrently when they target independent paths.
_PATH_SCOPED_TOOLS = frozenset({"read_file", "write_file", "patch"})

# Maximum number of concurrent worker threads for parallel tool execution.
_MAX_TOOL_WORKERS = 8

# Patterns that indicate a terminal command may modify/delete files.
_DESTRUCTIVE_PATTERNS = re.compile(
    r"""(?:^|\s|&&|\|\||;|`)(?:
        rm\s|rmdir\s|
        mv\s|
        sed\s+-i|
        truncate\s|
        dd\s|
        shred\s|
        git\s+(?:reset|clean|checkout)\s
    )""",
    re.VERBOSE,
)

# Output redirects that overwrite files (> but not >>)
_REDIRECT_OVERWRITE = re.compile(r"[^>]>[^>]|^>[^>]")


# =============================================================================
# Parallelization Functions
# =============================================================================


def _is_destructive_command(cmd: str) -> bool:
    """Heuristic: does this terminal command look like it modifies/deletes files?"""
    if not cmd:
        return False
    if _DESTRUCTIVE_PATTERNS.search(cmd):
        return True
    if _REDIRECT_OVERWRITE.search(cmd):
        return True
    return False


def _should_parallelize_tool_batch(tool_calls: list[Any]) -> bool:
    """Return True when a tool-call batch is safe to run concurrently."""
    if len(tool_calls) <= 1:
        return False

    tool_names = [tc.function.name for tc in tool_calls]
    if any(name in _NEVER_PARALLEL_TOOLS for name in tool_names):
        return False

    reserved_paths: list[Path] = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        try:
            function_args = json.loads(tool_call.function.arguments)
        except Exception:
            logging.debug(
                "Could not parse args for %s — defaulting to sequential; raw=%s",
                tool_name,
                tool_call.function.arguments[:200],
            )
            return False
        if not isinstance(function_args, dict):
            logging.debug(
                "Non-dict args for %s (%s) — defaulting to sequential",
                tool_name,
                type(function_args).__name__,
            )
            return False

        if tool_name in _PATH_SCOPED_TOOLS:
            scoped_path = _extract_parallel_scope_path(tool_name, function_args)
            if scoped_path is None:
                return False
            if any(
                _paths_overlap(scoped_path, existing) for existing in reserved_paths
            ):
                return False
            reserved_paths.append(scoped_path)
            continue

        if tool_name not in _PARALLEL_SAFE_TOOLS:
            return False

    return True


def _extract_parallel_scope_path(tool_name: str, function_args: dict) -> Path | None:
    """Return the normalized file target for path-scoped tools."""
    if tool_name not in _PATH_SCOPED_TOOLS:
        return None

    raw_path = function_args.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    # Avoid resolve(); the file may not exist yet.
    return Path(raw_path).expanduser()


def _paths_overlap(left: Path, right: Path) -> bool:
    """Return True when two paths may refer to the same subtree."""
    left_parts = left.parts
    right_parts = right.parts
    if not left_parts or not right_parts:
        return bool(left_parts) == bool(right_parts) and bool(left_parts)
    common_len = min(len(left_parts), len(right_parts))
    return left_parts[:common_len] == right_parts[:common_len]


# =============================================================================
# Sanitization Functions
# =============================================================================

# Budget warning text patterns injected by _get_budget_warning().
_BUDGET_WARNING_RE = re.compile(
    r"\[BUDGET(?:\s+WARNING)?:\s+Iteration\s+\d+/\d+\..*?\]",
    re.DOTALL,
)

# Regex to match lone surrogate code points (U+D800..U+DFFF).
# These are invalid in UTF-8 and cause UnicodeEncodeError when the OpenAI SDK
# serialises messages to JSON.
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def _sanitize_surrogates(text: str) -> str:
    """Replace lone surrogate code points with U+FFFD (replacement character).

    Surrogates are invalid in UTF-8 and will crash json.dumps() inside the
    OpenAI SDK. This is a fast no-op when the text contains no surrogates.
    """
    if _SURROGATE_RE.search(text):
        return _SURROGATE_RE.sub("\ufffd", text)
    return text


def _sanitize_messages_surrogates(messages: list) -> bool:
    """Sanitize surrogate characters from all string content in a messages list.

    Walks message dicts in-place. Returns True if any surrogates were found
    and replaced, False otherwise.
    """
    found = False
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str) and _SURROGATE_RE.search(content):
            msg["content"] = _SURROGATE_RE.sub("\ufffd", content)
            found = True
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and _SURROGATE_RE.search(text):
                        part["text"] = _SURROGATE_RE.sub("\ufffd", text)
                        found = True
    return found


def _strip_budget_warnings_from_history(messages: list) -> None:
    """Remove budget pressure warnings from tool-result messages in-place.

    Budget warnings are turn-scoped signals that must not leak into replayed
    history. They live in tool-result content either as a JSON key
    (_budget_warning) or appended plain text.
    """
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if (
            not isinstance(content, str)
            or "_budget_warning" not in content
            and "[BUDGET" not in content
        ):
            continue

        # Try JSON first (the common case: _budget_warning key in a dict)
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "_budget_warning" in parsed:
                del parsed["_budget_warning"]
                msg["content"] = json.dumps(parsed, ensure_ascii=False)
                continue
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: strip the text pattern from plain-text tool results
        cleaned = _BUDGET_WARNING_RE.sub("", content).strip()
        if cleaned != content:
            msg["content"] = cleaned


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "_NEVER_PARALLEL_TOOLS",
    "_PARALLEL_SAFE_TOOLS",
    "_PATH_SCOPED_TOOLS",
    "_MAX_TOOL_WORKERS",
    "_DESTRUCTIVE_PATTERNS",
    "_REDIRECT_OVERWRITE",
    "_is_destructive_command",
    "_should_parallelize_tool_batch",
    "_extract_parallel_scope_path",
    "_paths_overlap",
    "_BUDGET_WARNING_RE",
    "_SURROGATE_RE",
    "_sanitize_surrogates",
    "_sanitize_messages_surrogates",
    "_strip_budget_warnings_from_history",
]
