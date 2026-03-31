"""
Hermes v3.0 - Autonomous AI Team Platform

This package provides the core v3.0 modules:
- routing: Intent classification and agent routing
- lifecycle: Background agents and lifecycle hooks
- orchestration: Main pipeline integration
- observability: OpenTelemetry tracing and metrics

Quick Start:
    >>> from routing import IntentGate
    >>> from lifecycle import BackgroundAgentPool, hooks
    >>> from orchestration import process_request
    >>> 
    >>> # Classify intent
    >>> gate = IntentGate()
    >>> result = gate.analyze("implement feature")
    >>> 
    >>> # Process request
    >>> result = await process_request("build auth system")
"""

__version__ = "3.0.0"
__author__ = "Ahmad Ubaidillah"

# Core modules
from routing import IntentGate, IntentType, IntentResult
from lifecycle import (
    BackgroundAgentPool,
    ParallelAgentPool,
    hooks,
    HookEvent,
)
from orchestration import HermesPipeline, process_request
from observability import Observability, get_observability

__all__ = [
    # Routing
    "IntentGate",
    "IntentType",
    "IntentResult",
    
    # Lifecycle
    "BackgroundAgentPool",
    "ParallelAgentPool",
    "hooks",
    "HookEvent",
    
    # Orchestration
    "HermesPipeline",
    "process_request",
    
    # Observability
    "Observability",
    "get_observability",
]
