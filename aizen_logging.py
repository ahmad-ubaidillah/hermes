"""Aizen Structured Logging Module

Centralized logging configuration with:
- Structured JSON logging (optional)
- Request/correlation ID propagation
- Secret redaction
- Log file rotation
- Per-conversation trace IDs
- Conversation tracing (spans exported to JSONL)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Aizen home (needed by ConversationTracer default)
# ---------------------------------------------------------------------------


def get_aizen_home() -> Path:
    """Return the Aizen home directory."""
    home = os.getenv("AIZEN_HOME")
    if home:
        return Path(home)
    return Path.home() / ".aizen"


# ---------------------------------------------------------------------------
# Context-local storage for request_id / trace_id
# ---------------------------------------------------------------------------

_local = threading.local()


def get_request_id() -> str:
    """Return the current request_id, or generate a new one."""
    rid = getattr(_local, "request_id", None)
    if rid is None:
        rid = str(uuid.uuid4())[:12]
        _local.request_id = rid
    return rid


def set_request_id(rid: str) -> None:
    """Set the request_id for the current thread."""
    _local.request_id = rid


def clear_request_id() -> None:
    """Clear the request_id for the current thread."""
    _local.request_id = None


def get_trace_id() -> str:
    """Return the current trace_id (conversation-level), or generate one."""
    tid = getattr(_local, "trace_id", None)
    if tid is None:
        tid = str(uuid.uuid4())[:12]
        _local.trace_id = tid
    return tid


def set_trace_id(tid: str) -> None:
    """Set the trace_id for the current thread."""
    _local.trace_id = tid


def clear_trace_id() -> None:
    """Clear the trace_id for the current thread."""
    _local.trace_id = None


# ---------------------------------------------------------------------------
# Conversation Tracer
# ---------------------------------------------------------------------------


class ConversationSpan:
    """Represents a traced operation within a conversation."""

    def __init__(self, name: str, parent_id: Optional[str] = None):
        self.name = name
        self.span_id = str(uuid.uuid4())[:12]
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.status: str = "OK"

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def end(self) -> None:
        self.end_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
            "status": self.status,
            "trace_id": get_trace_id(),
            "request_id": get_request_id(),
        }


class ConversationTracer:
    """Traces conversation turns and tool calls.

    Exports spans to a JSONL file under ~/.aizen/logs/traces/.
    Each conversation gets its own trace file named by trace_id.
    """

    def __init__(self, trace_dir: Optional[Path] = None):
        self._trace_dir = trace_dir or (get_aizen_home() / "logs" / "traces")
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        self._current_span: Optional[ConversationSpan] = None
        self._spans: List[ConversationSpan] = []
        self._lock = threading.Lock()
        self._enabled = os.getenv("AIZEN_ENABLE_TRACING", "false").lower() == "true"

    @property
    def enabled(self) -> bool:
        return self._enabled

    @contextmanager
    def span(self, name: str, **attributes: Any):
        """Context manager for a traced operation."""
        parent_id = self._current_span.span_id if self._current_span else None
        span = ConversationSpan(name, parent_id=parent_id)
        span.attributes.update(attributes)
        with self._lock:
            self._spans.append(span)
            old_current = self._current_span
            self._current_span = span
        try:
            yield span
        except Exception as e:
            span.status = f"ERROR: {e}"
            span.attributes["error"] = str(e)
            raise
        finally:
            span.end()
            with self._lock:
                self._current_span = old_current
            if self._enabled:
                self._export_span(span)

    def _export_span(self, span: ConversationSpan) -> None:
        """Append span to the trace file."""
        trace_file = self._trace_dir / f"{get_trace_id()}.jsonl"
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(span.to_dict()) + "\n")

    def get_spans(self) -> List[Dict[str, Any]]:
        """Return all spans for the current conversation."""
        with self._lock:
            return [s.to_dict() for s in self._spans]

    def clear(self) -> None:
        """Clear all spans (call at end of conversation)."""
        with self._lock:
            self._spans.clear()
            self._current_span = None


# Global tracer instance
_tracer = ConversationTracer()


def get_tracer() -> ConversationTracer:
    """Return the global conversation tracer."""
    return _tracer


# ---------------------------------------------------------------------------
# Secret redaction patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    (
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        lambda m: m.group(0)[:6] + "***" + m.group(0)[-4:],
    ),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}"), lambda m: "ghp_***"),
    (re.compile(r"xoxb-[a-zA-Z0-9-]{10,}"), lambda m: "xoxb-***"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9._-]{10,}"), lambda m: "Bearer ***"),
    (
        re.compile(r"(api_key['\"]?\s*[:=]\s*['\"]?)[a-zA-Z0-9_-]{10,}"),
        lambda m: m.group(1) + "***",
    ),
    (
        re.compile(r"(password['\"]?\s*[:=]\s*['\"]?)[^\s,'\"]{4,}"),
        lambda m: m.group(1) + "***",
    ),
]

_REDACT_ENABLED = os.getenv("AIZEN_REDACT_SECRETS", "true").lower() != "false"


def redact_secrets(text: str) -> str:
    """Mask secrets in a log message."""
    if not _REDACT_ENABLED:
        return text
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class StructuredFormatter(logging.Formatter):
    """JSON-structured formatter with request_id and trace_id."""

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
            "request_id": get_request_id(),
            "trace_id": get_trace_id(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if (
            record.exc_info is not None
            and record.exc_info is not True
            and record.exc_info[0] is not None
        ):
            data["exception"] = self.formatException(record.exc_info)
        elif record.exc_info is True:
            import sys

            exc_info = sys.exc_info()
            if exc_info[0] is not None:
                data["exception"] = self.formatException(exc_info)
        if hasattr(record, "tool_name"):
            data["tool_name"] = record.tool_name
        if hasattr(record, "duration_ms"):
            data["duration_ms"] = record.duration_ms
        if hasattr(record, "token_count"):
            data["token_count"] = record.token_count
        return json.dumps(data, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """Human-readable formatter with request_id prefix."""

    def format(self, record: logging.LogRecord) -> str:
        rid = get_request_id()
        msg = redact_secrets(record.getMessage())
        prefix = f"[{rid}] " if rid else ""
        return f"{self.formatTime(record, self.datefmt)} {prefix}{record.levelname:<7} {record.name}: {msg}"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def get_aizen_home() -> Path:
    """Return the Aizen home directory."""
    home = os.getenv("AIZEN_HOME")
    if home:
        return Path(home)
    return Path.home() / ".aizen"


def ensure_log_dir() -> Path:
    """Ensure the log directory exists and return its path."""
    log_dir = get_aizen_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _add_file_handler(
    logger: logging.Logger,
    filepath: Path,
    level: int,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    structured: bool = False,
) -> None:
    """Add a rotating file handler to a logger if not already present."""
    handler_key = str(filepath)
    for h in logger.handlers:
        if getattr(h, "baseFilename", None) == str(filepath):
            return  # Already added
    fh = RotatingFileHandler(
        str(filepath),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fmt = StructuredFormatter() if structured else PlainFormatter()
    fh.setFormatter(fmt)
    logger.addHandler(fh)


def configure_logging(
    verbose: bool = False,
    quiet: bool = False,
    structured: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure Aizen logging.

    Args:
        verbose: Enable DEBUG level logging.
        quiet: Suppress most log output (ERROR only).
        structured: Use JSON-structured log format.
        log_file: Optional path to an additional log file.
    """
    root = logging.getLogger()
    log_dir = ensure_log_dir()
    errors_log = log_dir / "errors.log"

    # Remove existing handlers to avoid duplicates on reconfigure
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler()
    if verbose:
        console.setLevel(logging.DEBUG)
    elif quiet:
        console.setLevel(logging.ERROR)
    else:
        console.setLevel(logging.INFO)

    fmt = StructuredFormatter() if structured else PlainFormatter()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Error log file (always present)
    _add_file_handler(
        root,
        errors_log,
        logging.WARNING,
        max_bytes=2 * 1024 * 1024,
        backup_count=2,
        structured=structured,
    )

    # Additional log file if specified
    if log_file:
        _add_file_handler(root, Path(log_file), logging.INFO, structured=structured)

    # Root level
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Suppress noisy third-party loggers
    noisy = {
        "openai": logging.WARNING,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "asyncio": logging.WARNING,
        "hpack": logging.WARNING,
        "grpc": logging.ERROR,
        "modal": logging.WARNING,
        "urllib3": logging.WARNING,
        "chromadb": logging.WARNING,
        "faster_whisper": logging.WARNING,
    }
    for name, level in noisy.items():
        logging.getLogger(name).setLevel(level)

    # Quiet mode: suppress internal loggers to ERROR
    if quiet:
        for name in ("tools", "run_agent", "gateway", "agent", "aizen_cli"):
            logging.getLogger(name).setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name (convenience wrapper)."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Context manager for request-scoped logging
# ---------------------------------------------------------------------------


class RequestScope:
    """Context manager that sets request_id and trace_id for a block of code."""

    def __init__(
        self, request_id: Optional[str] = None, trace_id: Optional[str] = None
    ):
        self._request_id = request_id
        self._trace_id = trace_id
        self._prev_request_id: Optional[str] = None
        self._prev_trace_id: Optional[str] = None

    def __enter__(self) -> "RequestScope":
        self._prev_request_id = getattr(_local, "request_id", None)
        self._prev_trace_id = getattr(_local, "trace_id", None)
        if self._request_id:
            set_request_id(self._request_id)
        if self._trace_id:
            set_trace_id(self._trace_id)
        return self

    def __exit__(self, *args) -> None:
        if self._prev_request_id is not None:
            set_request_id(self._prev_request_id)
        else:
            clear_request_id()
        if self._prev_trace_id is not None:
            set_trace_id(self._prev_trace_id)
        else:
            clear_trace_id()
