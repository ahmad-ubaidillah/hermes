"""Load tests for Aizen Agent core subsystems.

Run separately from unit tests:
    pytest -m load tests/load/
"""

import gc
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _isolate_aizen_home(tmp_path, monkeypatch):
    fake_home = tmp_path / "aizen_load_test"
    fake_home.mkdir()
    (fake_home / "sessions").mkdir(parents=True)
    monkeypatch.setenv("AIZEN_HOME", str(fake_home))


@pytest.fixture
def snapshot_memory():
    tracemalloc.start()
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    yield (current, peak)
    tracemalloc.stop()


class TestConcurrentSessions:
    @pytest.mark.load
    @pytest.mark.parametrize("concurrency", [10, 50, 100])
    def test_concurrent_session_creation(self, tmp_path, concurrency):
        """Test concurrent session creation with SQLite."""
        import sqlite3

        db_path = str(tmp_path / "sessions.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions "
            "(id TEXT PRIMARY KEY, data TEXT, created_at REAL)"
        )
        conn.commit()
        conn.close()

        def create_session(session_id):
            c = sqlite3.connect(db_path)
            c.execute(
                "INSERT INTO sessions (id, data, created_at) VALUES (?, ?, ?)",
                (session_id, f'{{"id": "{session_id}"}}', time.time()),
            )
            c.commit()
            c.close()
            return session_id

        session_ids = [f"session_{i}" for i in range(concurrency)]
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=min(concurrency, 32)) as pool:
            futures = {pool.submit(create_session, sid): sid for sid in session_ids}
            results = [f.result() for f in as_completed(futures)]
        elapsed = time.monotonic() - start

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()

        assert count == concurrency
        assert len(results) == concurrency
        assert elapsed < 30.0, f"Concurrent creation took {elapsed:.1f}s"

    @pytest.mark.load
    def test_concurrent_session_read_write(self, tmp_path):
        """Test concurrent read/write operations."""
        import sqlite3

        db_path = str(tmp_path / "sessions.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions "
            "(id TEXT PRIMARY KEY, data TEXT, created_at REAL)"
        )
        conn.execute(
            "INSERT INTO sessions (id, data, created_at) VALUES (?, ?, ?)",
            ("base", '{"counter": 0}', time.time()),
        )
        conn.commit()
        conn.close()

        errors = []

        def writer(n):
            try:
                c = sqlite3.connect(db_path)
                c.execute(
                    "UPDATE sessions SET data = ? WHERE id = ?",
                    (f'{{"counter": {n}}}', "base"),
                )
                c.commit()
                c.close()
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                c = sqlite3.connect(db_path)
                c.execute("SELECT data FROM sessions WHERE id = ?", ("base",)).fetchone()
                c.close()
                return True
            except Exception as e:
                errors.append(e)
                return False

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = []
            for i in range(50):
                futures.append(pool.submit(writer, i))
            for _ in range(50):
                futures.append(pool.submit(reader))
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Concurrent read/write errors: {errors[:5]}"


class TestMemoryGrowth:
    @pytest.mark.load
    def test_session_store_memory_growth(self, tmp_path, snapshot_memory):
        """Repeated session operations should not leak memory."""
        from core.aizen_state import SessionDB

        db = SessionDB(db_path=tmp_path / "sessions.db")
        gc.collect()
        before_current, _ = tracemalloc.get_traced_memory()

        iterations = 100
        for i in range(iterations):
            sid = f"mem_test_{i}"
            db.create_session(
                session_id=sid, source="cli", user_id="test", model="test/model"
            )
            db.append_message(sid, "user", f"test {i}")
            db.get_session(sid)

        gc.collect()
        after_current, _ = tracemalloc.get_traced_memory()
        growth = after_current - before_current
        growth_per_op = growth / iterations
        assert growth_per_op < 2048, (
            f"Memory growth per session op: {growth_per_op:.1f} bytes/op"
        )


class TestResponseLatency:
    @pytest.mark.load
    def test_session_store_latency(self, tmp_path):
        """Measure session store operation latencies."""
        from core.aizen_state import SessionDB

        db = SessionDB(db_path=tmp_path / "sessions.db")
        create_times = []
        get_times = []
        iterations = 100

        for i in range(iterations):
            sid = f"lat_{i}"
            start = time.monotonic()
            db.create_session(
                session_id=sid, source="cli", user_id="test", model="test/model"
            )
            db.append_message(sid, "user", f"value_{i}")
            create_times.append(time.monotonic() - start)

        for i in range(iterations):
            sid = f"lat_{i}"
            start = time.monotonic()
            db.get_session(sid)
            get_times.append(time.monotonic() - start)

        avg_create = sum(create_times) / len(create_times)
        avg_get = sum(get_times) / len(get_times)

        assert avg_create < 0.01, f"Create avg latency: {avg_create*1000:.1f}ms"
        assert avg_get < 0.005, f"Get avg latency: {avg_get*1000:.1f}ms"


class TestBottlenecks:
    @pytest.mark.load
    def test_tool_dispatch_overhead(self):
        """Measure tool registry lookup overhead."""
        from tools.registry import registry

        iterations = 500
        times = []

        for _ in range(iterations):
            start = time.monotonic()
            _ = registry._tools.get("read_file")
            times.append(time.monotonic() - start)

        avg = sum(times) / len(times)
        assert avg < 0.0001, f"Tool lookup avg: {avg*1000000:.1f}us (expected <100us)"

    @pytest.mark.load
    def test_config_load_performance(self, tmp_path):
        """Measure config loading performance."""
        from aizen_cli.config import load_config

        iterations = 100
        times = []

        for _ in range(iterations):
            start = time.monotonic()
            load_config()
            times.append(time.monotonic() - start)

        avg = sum(times) / len(times)
        assert avg < 0.1, f"Config load avg: {avg*1000:.1f}ms (expected <100ms)"
