"""Tests for hermes_resilience module."""

import time
import pytest
from unittest.mock import patch, MagicMock

from hermes_resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    RetryConfig,
    ToolFailureRecord,
    ToolFailureTracker,
    _calculate_delay,
    compress_context_fallback,
    get_all_circuit_breaker_statuses,
    get_circuit_breaker,
    handle_tool_failure,
    reset_all_circuit_breakers,
    retry,
)


class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.jitter is True

    def test_custom_config(self):
        cfg = RetryConfig(max_retries=5, base_delay=2.0, jitter=False)
        assert cfg.max_retries == 5
        assert cfg.base_delay == 2.0
        assert cfg.jitter is False


class TestCalculateDelay:
    def test_first_attempt(self):
        delay = _calculate_delay(
            0, RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        )
        assert delay == 1.0

    def test_second_attempt(self):
        delay = _calculate_delay(
            1, RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        )
        assert delay == 2.0

    def test_third_attempt(self):
        delay = _calculate_delay(
            2, RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        )
        assert delay == 4.0

    def test_respects_max_delay(self):
        delay = _calculate_delay(
            10,
            RetryConfig(
                base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False
            ),
        )
        assert delay == 5.0

    def test_jitter_adds_randomness(self):
        delays = [
            _calculate_delay(0, RetryConfig(base_delay=1.0, jitter=True))
            for _ in range(10)
        ]
        assert any(d != delays[0] for d in delays)


class TestRetry:
    def test_succeeds_on_first_try(self):
        call_count = [0]

        def func():
            call_count[0] += 1
            return "ok"

        result = retry(func)
        assert result == "ok"
        assert call_count[0] == 1

    def test_retries_on_failure_then_succeeds(self):
        call_count = [0]

        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "ok"

        result = retry(func, RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        assert result == "ok"
        assert call_count[0] == 3

    def test_exhausts_retries(self):
        def func():
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            retry(func, RetryConfig(max_retries=2, base_delay=0.01, jitter=False))

    def test_non_retryable_exception_not_retried(self):
        call_count = [0]

        def func():
            call_count[0] += 1
            raise KeyboardInterrupt("interrupt")

        with pytest.raises(KeyboardInterrupt):
            retry(func, RetryConfig(max_retries=3, retryable_exceptions=(ValueError,)))
        assert call_count[0] == 1


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_rejects_calls(self):
        cb = CircuitBreaker(
            "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=9999)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "ok")

    def test_recovers_after_timeout(self):
        cb = CircuitBreaker(
            "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        cb = CircuitBreaker(
            "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        cb = CircuitBreaker(
            "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail again")))
        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        cb = CircuitBreaker(
            "test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=9999)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_status(self):
        cb = CircuitBreaker("test")
        status = cb.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"

    def test_successful_call(self):
        cb = CircuitBreaker("test")
        result = cb.call(lambda: 42)
        assert result == 42


class TestCircuitBreakerRegistry:
    def teardown_method(self):
        reset_all_circuit_breakers()

    def test_get_circuit_breaker_creates_new(self):
        cb = get_circuit_breaker("new-cb")
        assert cb.name == "new-cb"

    def test_get_circuit_breaker_returns_existing(self):
        cb1 = get_circuit_breaker("existing-cb")
        cb2 = get_circuit_breaker("existing-cb")
        assert cb1 is cb2

    def test_reset_all(self):
        cb = get_circuit_breaker(
            "reset-test", CircuitBreakerConfig(failure_threshold=1)
        )
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        reset_all_circuit_breakers()
        assert cb.state == CircuitState.CLOSED

    def test_get_all_statuses(self):
        get_circuit_breaker("status-test")
        statuses = get_all_circuit_breaker_statuses()
        assert "status-test" in statuses


class TestCompressContextFallback:
    def test_keeps_system_and_last_n(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        system = {"role": "system", "content": "sys"}
        result = compress_context_fallback(
            messages, system_message=system, keep_last_n=3
        )
        assert result[0] == system
        assert len(result) == 4  # system + 3 messages
        assert result[-1]["content"] == "msg 9"

    def test_fewer_messages_than_keep_n(self):
        messages = [{"role": "user", "content": "only"}]
        result = compress_context_fallback(messages, keep_last_n=5)
        assert len(result) == 1

    def test_no_system_message(self):
        messages = [{"role": "user", "content": "msg"}]
        result = compress_context_fallback(messages, keep_last_n=1)
        assert len(result) == 1


class TestToolFailureTracker:
    def test_records_failure(self):
        tracker = ToolFailureTracker(max_failures_per_turn=1)
        tracker.record_failure("my_tool", "error msg", turn=1)
        assert not tracker.should_continue(turn=1)

    def test_should_continue_under_limit(self):
        tracker = ToolFailureTracker(max_failures_per_turn=3)
        tracker.record_failure("tool", "err", turn=1)
        tracker.record_failure("tool", "err", turn=1)
        assert tracker.should_continue(turn=1)

    def test_should_stop_at_limit(self):
        tracker = ToolFailureTracker(max_failures_per_turn=2)
        tracker.record_failure("tool", "err", turn=1)
        tracker.record_failure("tool", "err", turn=1)
        assert not tracker.should_continue(turn=1)

    def test_different_turns_independent(self):
        tracker = ToolFailureTracker(max_failures_per_turn=1)
        tracker.record_failure("tool", "err", turn=1)
        assert tracker.should_continue(turn=2)

    def test_get_failure_summary(self):
        tracker = ToolFailureTracker()
        tracker.record_failure("tool_a", "err_a", turn=1)
        tracker.record_failure("tool_b", "err_b", turn=1)
        summary = tracker.get_failure_summary(turn=1)
        assert "2 tool failures" in summary
        assert "tool_a" in summary

    def test_reset_turn(self):
        tracker = ToolFailureTracker(max_failures_per_turn=1)
        tracker.record_failure("tool", "err", turn=1)
        tracker.reset_turn(1)
        assert tracker.should_continue(turn=1)

    def test_clear(self):
        tracker = ToolFailureTracker()
        tracker.record_failure("tool", "err", turn=1)
        tracker.clear()
        assert tracker.get_failure_summary(turn=1) == ""


class TestHandleToolFailure:
    def test_returns_error_message(self):
        msg = handle_tool_failure("my_tool", "something broke")
        assert "my_tool" in msg
        assert "something broke" in msg

    def test_with_tracker_reaches_limit(self):
        tracker = ToolFailureTracker(max_failures_per_turn=1)
        handle_tool_failure("tool", "err1", tracker, turn=1)
        msg = handle_tool_failure("tool", "err2", tracker, turn=1)
        assert "Maximum tool failures" in msg

    def test_without_tracker_no_limit_message(self):
        msg = handle_tool_failure("tool", "err")
        assert "Maximum tool failures" not in msg
