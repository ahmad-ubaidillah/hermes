"""Tests for aizen_health module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aizen_health import (
    HealthChecker,
    HealthCheckResult,
    HealthReport,
    HealthStatus,
    check_api_connectivity,
    check_disk_space,
    check_aizen_home,
    check_session_db,
    get_health_checker,
    run_health_check,
)


class TestHealthCheckResult:
    def test_to_dict(self):
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.OK,
            message="All good",
            details={"key": "value"},
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "ok"
        assert d["message"] == "All good"
        assert d["details"]["key"] == "value"


class TestHealthReport:
    def test_to_dict(self):
        report = HealthReport(
            overall=HealthStatus.OK,
            checks=[
                HealthCheckResult("check1", HealthStatus.OK, "ok"),
                HealthCheckResult("check2", HealthStatus.DEGRADED, "warn"),
            ],
        )
        d = report.to_dict()
        assert d["overall"] == "ok"
        assert len(d["checks"]) == 2


class TestCheckDiskSpace:
    def test_enough_space(self, tmp_path):
        result = check_disk_space(str(tmp_path), min_free_mb=1)
        assert result.status == HealthStatus.OK

    def test_low_space(self, tmp_path):
        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = MagicMock(free=50 * 1024 * 1024)  # 50MB
            result = check_disk_space(str(tmp_path), min_free_mb=100)
            assert result.status == HealthStatus.UNHEALTHY
            assert "Low disk space" in result.message

    def test_degraded_space(self, tmp_path):
        with patch("shutil.disk_usage") as mock_usage:
            mock_usage.return_value = MagicMock(free=200 * 1024 * 1024)  # 200MB
            result = check_disk_space(str(tmp_path), min_free_mb=100)
            assert result.status == HealthStatus.DEGRADED

    def test_exception_handling(self):
        with patch("shutil.disk_usage", side_effect=OSError("fail")):
            result = check_disk_space("/nonexistent")
            assert result.status == HealthStatus.UNHEALTHY


class TestCheckAizenHome:
    def test_existing_writable_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEN_HOME", str(tmp_path))
        result = check_aizen_home()
        assert result.status == HealthStatus.OK

    def test_nonexistent_home(self, monkeypatch):
        monkeypatch.setenv("AIZEN_HOME", "/nonexistent/path/xyz")
        result = check_aizen_home()
        assert result.status == HealthStatus.UNHEALTHY


class TestCheckSessionDb:
    def test_db_not_available(self):
        result = check_session_db("/nonexistent/db.sqlite")
        # Should be DEGRADED or UNHEALTHY since DB doesn't exist
        assert result.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)


class TestCheckApiConnectivity:
    def test_unknown_provider(self):
        result = check_api_connectivity("unknown_provider_xyz")
        assert result.status == HealthStatus.DEGRADED

    def test_openai_provider_format(self):
        result = check_api_connectivity("openai")
        assert result.name == "api_openai"


class TestHealthChecker:
    def test_run_basic(self):
        checker = HealthChecker()
        report = checker.run()
        assert isinstance(report, HealthReport)
        assert report.overall in (
            HealthStatus.OK,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )
        assert len(report.checks) >= 3  # aizen_home, disk_space, session_db

    def test_add_check(self):
        checker = HealthChecker()
        checker.add_check(
            lambda: HealthCheckResult("custom", HealthStatus.OK, "custom ok")
        )
        report = checker.run()
        names = [c.name for c in report.checks]
        assert "custom" in names

    def test_overall_is_worst_status(self):
        checker = HealthChecker()
        checker._checks = [
            lambda: HealthCheckResult("ok", HealthStatus.OK, "ok"),
            lambda: HealthCheckResult("bad", HealthStatus.UNHEALTHY, "bad"),
        ]
        report = checker.run()
        assert report.overall == HealthStatus.UNHEALTHY

    def test_check_exception_handled(self):
        checker = HealthChecker()
        checker._checks = [lambda: (_ for _ in ()).throw(RuntimeError("boom"))]
        report = checker.run()
        assert report.overall == HealthStatus.UNHEALTHY

    def test_get_health_checker_singleton(self):
        h1 = get_health_checker()
        h2 = get_health_checker()
        assert h1 is h2

    def test_run_health_check_function(self):
        report = run_health_check()
        assert isinstance(report, HealthReport)
