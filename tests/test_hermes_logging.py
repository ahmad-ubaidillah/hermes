"""Tests for hermes_logging module."""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_logging import (
    ConversationSpan,
    ConversationTracer,
    StructuredFormatter,
    PlainFormatter,
    RequestScope,
    clear_request_id,
    clear_trace_id,
    configure_logging,
    get_logger,
    get_request_id,
    get_trace_id,
    get_tracer,
    redact_secrets,
    set_request_id,
    set_trace_id,
)


class TestRequestID:
    def test_get_request_id_generates_new(self):
        clear_request_id()
        rid = get_request_id()
        assert len(rid) == 12

    def test_get_request_id_reuses_existing(self):
        set_request_id("test-rid-123")
        assert get_request_id() == "test-rid-123"

    def test_set_request_id(self):
        set_request_id("my-custom-id")
        assert get_request_id() == "my-custom-id"

    def test_clear_request_id(self):
        set_request_id("to-clear")
        clear_request_id()
        rid = get_request_id()
        assert rid != "to-clear"


class TestTraceID:
    def test_get_trace_id_generates_new(self):
        clear_trace_id()
        tid = get_trace_id()
        assert len(tid) == 12

    def test_set_trace_id(self):
        set_trace_id("my-trace-id")
        assert get_trace_id() == "my-trace-id"

    def test_clear_trace_id(self):
        set_trace_id("to-clear")
        clear_trace_id()
        tid = get_trace_id()
        assert tid != "to-clear"


class TestRequestScope:
    def test_sets_and_restores_request_id(self):
        clear_request_id()
        set_request_id("outer")
        with RequestScope(request_id="inner"):
            assert get_request_id() == "inner"
        assert get_request_id() == "outer"

    def test_sets_and_restores_trace_id(self):
        clear_trace_id()
        set_trace_id("outer-trace")
        with RequestScope(trace_id="inner-trace"):
            assert get_trace_id() == "inner-trace"
        assert get_trace_id() == "outer-trace"

    def test_clears_on_exit_if_no_previous(self):
        clear_request_id()
        with RequestScope(request_id="scoped"):
            assert get_request_id() == "scoped"
        # Should be cleared (or regenerated) after exit
        rid = get_request_id()
        assert rid != "scoped"


class TestRedactSecrets:
    def test_redacts_sk_key(self):
        result = redact_secrets("key=sk-abc123def456ghi789jkl012mno345")
        assert "sk-abc123def456ghi789jkl012mno345" not in result

    def test_redacts_ghp_token(self):
        result = redact_secrets("token=ghp_abc123def456ghi789jkl012mno345")
        assert "ghp_abc123def456ghi789jkl012mno345" not in result

    def test_redacts_bearer_token(self):
        result = redact_secrets(
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        )
        assert "eyJhbGci" not in result

    def test_redacts_api_key_assignment(self):
        result = redact_secrets('api_key: "sk-test-key-very-long-value-here"')
        assert "sk-test-key-very-long-value-here" not in result

    def test_redacts_password(self):
        result = redact_secrets('password: "super-secret-password-123"')
        assert "super-secret-password-123" not in result

    def test_no_redaction_for_normal_text(self):
        result = redact_secrets("Hello world, this is a normal message")
        assert result == "Hello world, this is a normal message"

    def test_redaction_can_be_disabled(self):
        import hermes_logging

        # Patch the module-level variable directly instead of reloading
        with patch.object(hermes_logging, "_REDACT_ENABLED", False):
            result = hermes_logging.redact_secrets("sk-abc...o345")
            assert "sk-abc...o345" in result


class TestStructuredFormatter:
    def test_produces_valid_json(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "Hello world"
        assert data["logger"] == "test.logger"
        assert "request_id" in data
        assert "trace_id" in data

    def test_includes_request_id(self):
        formatter = StructuredFormatter()
        set_request_id("test-rid")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["request_id"] == "test-rid"
        clear_request_id()

    def test_includes_trace_id(self):
        formatter = StructuredFormatter()
        set_trace_id("test-tid")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["trace_id"] == "test-tid"
        clear_trace_id()

    def test_redacts_secrets_in_message(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using key sk-abc123def456ghi789jkl012mno345",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "sk-abc123def456ghi789jkl012mno345" not in data["message"]

    def test_includes_exception_info(self):
        formatter = StructuredFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Failed",
                args=(),
                exc_info=exc_info,
            )
            output = formatter.format(record)
            data = json.loads(output)
            assert "exception" in data
            assert "ValueError" in data["exception"]


class TestPlainFormatter:
    def test_includes_request_id_prefix(self):
        formatter = PlainFormatter()
        set_request_id("test-rid")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "[test-rid]" in output
        clear_request_id()

    def test_redacts_secrets(self):
        formatter = PlainFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="key=sk-abc123def456ghi789jkl012mno345",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        assert "sk-abc123def456ghi789jkl012mno345" not in output


class TestConfigureLogging:
    def test_configure_creates_log_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        configure_logging()
        assert (tmp_path / "logs").exists()

    def test_verbose_sets_debug_level(self):
        configure_logging(verbose=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_quiet_sets_error_level(self):
        configure_logging(quiet=True)
        root = logging.getLogger()
        # Root is INFO, but console handler is ERROR
        console_handlers = [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename")
        ]
        assert any(h.level == logging.ERROR for h in console_handlers)

    def test_structured_uses_json_formatter(self):
        configure_logging(structured=True)
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename"):
                assert isinstance(h.formatter, StructuredFormatter)
                break


class TestGetLogger:
    def test_get_logger_returns_logging_logger(self):
        logger = get_logger("my.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "my.module"


class TestConversationSpan:
    def test_span_has_correct_fields(self):
        span = ConversationSpan("test_op")
        assert span.name == "test_op"
        assert len(span.span_id) == 12
        assert span.parent_id is None
        assert span.status == "OK"

    def test_span_duration(self):
        span = ConversationSpan("test_op")
        import time

        time.sleep(0.01)
        span.end()
        assert span.duration_ms >= 10

    def test_span_to_dict(self):
        span = ConversationSpan("test_op", parent_id="parent-123")
        span.attributes["key"] = "value"
        span.end()
        d = span.to_dict()
        assert d["name"] == "test_op"
        assert d["parent_id"] == "parent-123"
        assert d["attributes"]["key"] == "value"
        assert "trace_id" in d
        assert "request_id" in d


class TestConversationTracer:
    def test_tracer_disabled_by_default(self):
        tracer = ConversationTracer()
        assert tracer.enabled is False

    def test_tracer_enabled_via_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HERMES_ENABLE_TRACING", "true")
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        assert tracer.enabled is True

    def test_span_context_manager(self, tmp_path):
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        tracer._enabled = True
        with tracer.span("test_op", foo="bar") as span:
            assert span.name == "test_op"
            assert span.attributes["foo"] == "bar"
        assert span.end_time is not None
        assert span.status == "OK"

    def test_span_error_status(self, tmp_path):
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        tracer._enabled = True
        with pytest.raises(ValueError):
            with tracer.span("failing_op"):
                raise ValueError("oops")
        spans = tracer.get_spans()
        assert spans[-1]["status"].startswith("ERROR")

    def test_nested_spans(self, tmp_path):
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        tracer._enabled = True
        with tracer.span("parent"):
            with tracer.span("child"):
                pass
        spans = tracer.get_spans()
        assert len(spans) == 2
        child = spans[1]
        parent = spans[0]
        assert child["parent_id"] == parent["span_id"]

    def test_export_creates_jsonl_file(self, tmp_path):
        trace_dir = tmp_path / "traces"
        tracer = ConversationTracer(trace_dir=trace_dir)
        tracer._enabled = True
        set_trace_id("test-trace-123")
        with tracer.span("exported_op"):
            pass
        trace_file = trace_dir / "test-trace-123.jsonl"
        assert trace_file.exists()
        content = trace_file.read_text()
        data = json.loads(content.strip())
        assert data["name"] == "exported_op"
        clear_trace_id()

    def test_get_spans_returns_list(self, tmp_path):
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        with tracer.span("op1"):
            pass
        with tracer.span("op2"):
            pass
        spans = tracer.get_spans()
        assert len(spans) == 2

    def test_clear_removes_all_spans(self, tmp_path):
        tracer = ConversationTracer(trace_dir=tmp_path / "traces")
        with tracer.span("op1"):
            pass
        tracer.clear()
        assert len(tracer.get_spans()) == 0

    def test_get_tracer_returns_singleton(self):
        t1 = get_tracer()
        t2 = get_tracer()
        assert t1 is t2
