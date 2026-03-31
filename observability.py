"""
Hermes Observability - OpenTelemetry Integration

Provides:
- Tracing (request flow)
- Metrics (performance counters)
- Logging (structured logs)
- Export to various backends (Jaeger, Prometheus, etc.)
"""

from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from contextlib import contextmanager

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    HAS_OTLP = True
except ImportError:
    HAS_OTLP = False


# ============== Tracing ==============

@dataclass
class Span:
    """Represents a traced operation."""
    
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"
    parent_id: Optional[str] = None
    span_id: str = ""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.end()
    
    def end(self):
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def add_event(self, name: str, attributes: Optional[Dict] = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
    
    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
        }


class Tracer:
    """
    Simple tracer for tracking operations.
    
    Can export to:
    - Console (default)
    - File (JSONL)
    - OpenTelemetry (if installed)
    - Jaeger/Prometheus (via OTLP)
    """
    
    def __init__(
        self,
        service_name: str = "hermes",
        export_to_file: Optional[str] = None,
        export_to_console: bool = True,
    ):
        self.service_name = service_name
        self.export_to_file = export_to_file
        self.export_to_console = export_to_console
        
        # Storage
        self._spans: List[Span] = []
        self._current_span: Optional[Span] = None
        
        # OpenTelemetry setup
        self._otel_tracer = None
        if HAS_OTEL:
            self._setup_otel()
        
        # File export
        if export_to_file:
            self._export_path = Path(export_to_file)
            self._export_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _setup_otel(self):
        """Setup OpenTelemetry tracer."""
        resource = Resource.create({"service.name": self.service_name})
        provider = TracerProvider(resource=resource)
        
        # Console exporter
        if self.export_to_console:
            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)
        self._otel_tracer = trace.get_tracer(self.service_name)
    
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span."""
        import uuid
        
        span = Span(
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
            span_id=uuid.uuid4().hex[:16],
            parent_id=self._current_span.span_id if self._current_span else None,
        )
        
        self._spans.append(span)
        return span
    
    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for a span."""
        span = self.start_span(name, attributes)
        old_current = self._current_span
        self._current_span = span
        
        try:
            yield span
        except Exception as e:
            span.status = f"ERROR: {e}"
            raise
        finally:
            span.end()
            self._current_span = old_current
            self._export_span(span)
    
    def trace(self, name: Optional[str] = None):
        """Decorator to trace a function."""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.span(span_name):
                    return func(*args, **kwargs)
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.span(span_name):
                    return await func(*args, **kwargs)
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def _export_span(self, span: Span):
        """Export span to configured destinations."""
        if self.export_to_console:
            print(f"[TRACE] {span.name} - {span.duration_ms:.2f}ms - {span.status}")
        
        if self.export_to_file:
            with open(self._export_path, 'a') as f:
                f.write(json.dumps(span.to_dict()) + '\n')
    
    def get_spans(self) -> List[Dict[str, Any]]:
        """Get all recorded spans."""
        return [s.to_dict() for s in self._spans]
    
    def clear(self):
        """Clear all recorded spans."""
        self._spans.clear()


# ============== Metrics ==============

@dataclass
class MetricValue:
    """A single metric measurement."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsRegistry:
    """
    Simple metrics registry for counters, gauges, and histograms.
    
    Can export to:
    - Prometheus format
    - JSON
    - Console
    """
    
    def __init__(self, namespace: str = "hermes"):
        self.namespace = namespace
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._history: List[MetricValue] = []
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment a counter."""
        full_name = f"{self.namespace}_{name}"
        self._counters[full_name] = self._counters.get(full_name, 0) + value
        self._history.append(MetricValue(
            name=full_name,
            value=self._counters[full_name],
            timestamp=time.time(),
            labels=labels or {},
        ))
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value."""
        full_name = f"{self.namespace}_{name}"
        self._gauges[full_name] = value
        self._history.append(MetricValue(
            name=full_name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
        ))
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        full_name = f"{self.namespace}_{name}"
        if full_name not in self._histograms:
            self._histograms[full_name] = []
        self._histograms[full_name].append(value)
        self._history.append(MetricValue(
            name=full_name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
        ))
    
    def get_counter(self, name: str) -> float:
        """Get counter value."""
        full_name = f"{self.namespace}_{name}"
        return self._counters.get(full_name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        full_name = f"{self.namespace}_{name}"
        return self._gauges.get(full_name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        full_name = f"{self.namespace}_{name}"
        values = self._histograms.get(full_name, [])
        
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }
    
    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Histograms
        for name, values in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            stats = self.get_histogram_stats(name.replace(f"{self.namespace}_", ""))
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['sum']}")
        
        return '\n'.join(lines)
    
    def to_json(self) -> Dict[str, Any]:
        """Export metrics as JSON."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name.replace(f"{self.namespace}_", ""))
                for name in self._histograms
            },
        }


# ============== Logging ==============

class StructuredLogger:
    """
    Structured JSON logger with context support.
    """
    
    def __init__(self, name: str = "hermes"):
        self.name = name
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def with_context(self, **kwargs) -> "StructuredLogger":
        """Create a new logger with additional context."""
        new_logger = StructuredLogger(self.name)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _log(self, level: str, message: str, **kwargs):
        """Log with structured data."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            **self._context,
            **kwargs,
        }
        
        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(record),
        )
    
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)


# ============== Observability Manager ==============

class Observability:
    """
    Unified observability for Hermes.
    
    Combines tracing, metrics, and logging.
    """
    
    def __init__(
        self,
        service_name: str = "hermes",
        trace_file: Optional[str] = None,
        enable_console: bool = True,
    ):
        self.tracer = Tracer(
            service_name=service_name,
            export_to_file=trace_file,
            export_to_console=enable_console,
        )
        self.metrics = MetricsRegistry(namespace=service_name)
        self.logger = StructuredLogger(name=service_name)
    
    @contextmanager
    def trace_operation(self, name: str, **attributes):
        """Trace an operation with automatic metrics."""
        with self.tracer.span(name, attributes) as span:
            try:
                yield span
                self.metrics.counter(f"{name}_success")
            except Exception as e:
                self.metrics.counter(f"{name}_error")
                span.status = f"ERROR: {e}"
                raise
            finally:
                self.metrics.histogram(f"{name}_duration_ms", span.duration_ms)
    
    def record_request(self, agent: str, tokens: int, success: bool):
        """Record an agent request."""
        self.metrics.counter(f"{agent}_requests_total")
        self.metrics.counter(f"{agent}_tokens_total", value=tokens)
        
        if success:
            self.metrics.counter(f"{agent}_success_total")
        else:
            self.metrics.counter(f"{agent}_error_total")
        
        self.logger.info(
            f"Agent {agent} request completed",
            agent=agent,
            tokens=tokens,
            success=success,
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get observability summary."""
        return {
            "traces": {
                "total_spans": len(self.tracer._spans),
                "recent": self.tracer.get_spans()[-10:],
            },
            "metrics": self.metrics.to_json(),
        }


# ============== Singleton ==============

_observability: Optional[Observability] = None


def get_observability() -> Observability:
    """Get singleton Observability instance."""
    global _observability
    if _observability is None:
        _observability = Observability(
            trace_file=str(Path.home() / ".hermes" / "traces.jsonl"),
        )
    return _observability


# ============== CLI Test ==============

if __name__ == "__main__":
    print("\n=== Observability Test ===\n")
    
    obs = Observability(
        service_name="hermes-test",
        enable_console=True,
    )
    
    # Test tracing
    print("1. Testing tracing:")
    with obs.trace_operation("test_operation", user="test"):
        time.sleep(0.1)
        obs.logger.info("Inside traced operation")
    
    # Test metrics
    print("\n2. Testing metrics:")
    obs.metrics.counter("requests", value=5)
    obs.metrics.gauge("active_agents", value=3)
    obs.metrics.histogram("latency", value=42.5)
    obs.metrics.histogram("latency", value=38.2)
    
    print(f"   Counter: {obs.metrics.get_counter('requests')}")
    print(f"   Gauge: {obs.metrics.get_gauge('active_agents')}")
    print(f"   Histogram stats: {obs.metrics.get_histogram_stats('latency')}")
    
    # Test logging
    print("\n3. Testing structured logging:")
    obs.logger.info("Test message", extra_field="value")
    
    # Test Prometheus export
    print("\n4. Prometheus format:")
    print(obs.metrics.to_prometheus()[:200] + "...")
    
    # Test request recording
    print("\n5. Recording agent request:")
    obs.record_request("Dev", tokens=1500, success=True)
    
    # Summary
    print("\n6. Summary:")
    summary = obs.get_summary()
    print(f"   Traces: {summary['traces']['total_spans']} spans")
    print(f"   Metrics: {len(summary['metrics']['counters'])} counters")
    
    print("\n=== Test Complete ===")
