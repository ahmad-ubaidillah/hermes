"""
Hermes Routing Module - Intent classification and agent routing.

This module provides smart task classification to route user requests
to appropriate agents and workflows.

Example:
    >>> from routing import IntentGate
    >>> gate = IntentGate()
    >>> result = gate.analyze("implement user auth")
    >>> print(result.verbalize())
    I detect **coding** intent — detected 'implement' indicates coding.
"""

from .intent_gate import IntentGate, IntentType, IntentResult

__all__ = ["IntentGate", "IntentType", "IntentResult"]
__version__ = "3.0.0"
