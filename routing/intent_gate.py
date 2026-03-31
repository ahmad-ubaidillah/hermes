"""
IntentGate - Smart task classification for Hermes.

Analyzes user's true intent before routing to appropriate agent/workflow.
Inspired by oh-my-openagent's IntentGate system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class IntentType(str, Enum):
    """Intent types for task classification."""
    
    QUICK_TASK = "quick_task"        # Simple, can be done immediately (Flash)
    CODING = "coding"                # Requires coding/implementation
    ARCHITECTURE = "architecture"    # Requires design/planning
    RESEARCH = "research"            # Information gathering
    DEPLOYMENT = "deployment"        # Infrastructure/ops
    REVIEW = "review"                # Code review/analysis
    DEBUGGING = "debugging"          # Fix bugs/issues
    QUESTION = "question"            # Just asking for info
    EVALUATION = "evaluation"        # User wants judgment/opinion
    OPEN_ENDED = "open_ended"        # Vague improvement request
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent analysis."""
    
    intent: IntentType
    confidence: float
    suggested_agent: str
    suggested_workflow: str
    is_flash_task: bool
    requires_planning: bool
    requires_confirmation: bool
    estimated_tokens: int
    sub_intents: List[str] = field(default_factory=list)
    reasoning: str = ""
    
    def verbalize(self) -> str:
        """Return verbalization string for intent classification."""
        return f"I detect **{self.intent.value}** intent — {self.reasoning}. My approach: {self.suggested_workflow}."


class IntentGate:
    """
    Analyzes true user intent before acting.
    
    The user's surface request may not match their true intent.
    This system identifies what they ACTUALLY want, then routes accordingly.
    """
    
    # Pattern weights for intent detection
    PATTERNS: Dict[IntentType, Tuple[List[str], int]] = {
        IntentType.QUICK_TASK: ([
            "print", "show", "list", "display", "check",
            "what is", "tell me", "quick", "simple",
            "just", "only", "fast", "now",
        ], 1),
        IntentType.CODING: ([
            "create", "implement", "build", "develop",
            "add feature", "write code", "make a", "write a",
            "code", "script", "function", "module",
        ], 2),
        IntentType.ARCHITECTURE: ([
            "design", "architecture", "structure",
            "how should", "plan for", "system design",
            "refactor", "restructure", "organize",
        ], 2),
        IntentType.RESEARCH: ([
            "research", "analyze", "investigate",
            "find out", "explore", "study",
            "explain", "how does", "why does",
        ], 1),
        IntentType.DEPLOYMENT: ([
            "deploy", "release", "ship",
            "production", "server", "infrastructure",
            "docker", "kubernetes", "ci/cd",
        ], 2),
        IntentType.DEBUGGING: ([
            "fix", "debug", "error", "bug",
            "not working", "broken", "issue",
            "crash", "exception", "traceback",
        ], 2),
        IntentType.REVIEW: ([
            "review", "check code", "analyze code",
            "security", "audit", "improve",
            "optimize", "refactor",
        ], 2),
        IntentType.EVALUATION: ([
            "what do you think", "opinion", "evaluate",
            "assess", "judge", "better",
        ], 2),
        IntentType.QUESTION: ([
            "how do i", "what is", "why is",
            "can you explain", "help me understand",
            "tell me about",
        ], 1),
    }
    
    # Flash task indicators
    FLASH_INDICATORS = [
        "quick", "simple", "just", "only",
        "fast", "now", "immediately", "asap",
    ]
    
    # Planning-required indicators
    PLANNING_INDICATORS = [
        "implement", "build", "create", "develop",
        "architecture", "design", "refactor",
        "migrate", "integrate",
    ]
    
    # Ambiguity indicators
    AMBIGUITY_INDICATORS = [
        "improve", "clean up", "optimize", "better",
        "enhance", "update", "modify",
    ]
    
    # Agent routing map
    AGENT_MAP: Dict[IntentType, Tuple[str, str]] = {
        IntentType.QUICK_TASK: ("Flash", "quick_execute"),
        IntentType.CODING: ("Dev", "sprint_workflow"),
        IntentType.ARCHITECTURE: ("Arch", "planning_workflow"),
        IntentType.RESEARCH: ("Research", "research_workflow"),
        IntentType.DEPLOYMENT: ("Ops", "deploy_workflow"),
        IntentType.DEBUGGING: ("Dev", "debug_workflow"),
        IntentType.REVIEW: ("QA", "review_workflow"),
        IntentType.QUESTION: ("Flash", "quick_execute"),
        IntentType.EVALUATION: ("Flash", "evaluate_workflow"),
        IntentType.OPEN_ENDED: ("Flash", "assess_workflow"),
        IntentType.UNKNOWN: ("Flash", "quick_execute"),
    }
    
    # Token estimation
    TOKEN_ESTIMATES: Dict[IntentType, int] = {
        IntentType.QUICK_TASK: 1000,
        IntentType.CODING: 15000,
        IntentType.ARCHITECTURE: 8000,
        IntentType.RESEARCH: 5000,
        IntentType.DEPLOYMENT: 8000,
        IntentType.DEBUGGING: 6000,
        IntentType.REVIEW: 4000,
        IntentType.QUESTION: 1000,
        IntentType.EVALUATION: 2000,
        IntentType.OPEN_ENDED: 3000,
        IntentType.UNKNOWN: 2000,
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for faster matching."""
        self._compiled: Dict[IntentType, List[re.Pattern]] = {}
        for intent, (patterns, _) in self.PATTERNS.items():
            self._compiled[intent] = [
                re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE)
                for p in patterns
            ]
    
    def analyze(self, user_input: str, context: str = "") -> IntentResult:
        """
        Analyze user intent from input.
        
        Args:
            user_input: The user's message/request
            context: Optional additional context (previous messages, etc.)
        
        Returns:
            IntentResult with classification and routing info
        """
        text = (user_input or "").strip().lower()
        context_text = (context or "").strip().lower()
        combined = f"{text} {context_text}".strip()
        
        if not text:
            return self._unknown_result("Empty input")
        
        # Score each intent type
        scores: Dict[IntentType, float] = {}
        matched_patterns: Dict[IntentType, List[str]] = {}
        
        for intent, patterns_tuple in self.PATTERNS.items():
            patterns, weight = patterns_tuple
            matches = []
            for pattern in patterns:
                if pattern in text:
                    matches.append(pattern)
            
            # Weight matches by pattern importance
            scores[intent] = len(matches) * weight
            matched_patterns[intent] = matches
        
        # Find best intent
        if max(scores.values()) == 0:
            return self._unknown_result("No matching patterns found")
        
        best_intent = max(scores, key=scores.get)
        total_patterns = len(self.PATTERNS[best_intent][0])
        confidence = min(scores[best_intent] / max(total_patterns, 1), 1.0)
        
        # Check for flash task
        is_flash = self._is_flash_task(text, best_intent, confidence)
        
        # Check if planning required
        requires_planning = self._requires_planning(text, best_intent)
        
        # Check if evaluation/open-ended (needs confirmation)
        requires_confirmation = best_intent in [
            IntentType.EVALUATION, 
            IntentType.OPEN_ENDED
        ] or self._is_ambiguous(text)
        
        # Get agent and workflow
        agent, workflow = self.AGENT_MAP.get(best_intent, ("Flash", "quick_execute"))
        
        # Build reasoning
        reasoning = self._build_reasoning(
            best_intent, matched_patterns[best_intent], text
        )
        
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            suggested_agent=agent,
            suggested_workflow=workflow,
            is_flash_task=is_flash,
            requires_planning=requires_planning,
            requires_confirmation=requires_confirmation,
            estimated_tokens=self.TOKEN_ESTIMATES.get(best_intent, 2000),
            sub_intents=self._find_sub_intents(scores, best_intent),
            reasoning=reasoning,
        )
    
    def _is_flash_task(self, text: str, intent: IntentType, confidence: float) -> bool:
        """Determine if task qualifies for Flash execution."""
        # Quick tasks are always flash
        if intent == IntentType.QUICK_TASK:
            return True
        
        # Questions are flash
        if intent == IntentType.QUESTION:
            return True
        
        # Check for flash indicators
        has_flash_indicator = any(ind in text for ind in self.FLASH_INDICATORS)
        
        # Short, simple requests can be flash
        is_short = len(text.split()) < 15
        is_simple = "```" not in text and "\n" not in text
        
        # High confidence + simple + short = flash
        if confidence > 0.7 and is_short and is_simple:
            return True
        
        # Has flash indicator + simple
        if has_flash_indicator and is_simple:
            return True
        
        return False
    
    def _requires_planning(self, text: str, intent: IntentType) -> bool:
        """Determine if task requires planning phase."""
        if intent in [IntentType.CODING, IntentType.ARCHITECTURE]:
            return True
        
        if intent == IntentType.DEBUGGING:
            # Complex debugging needs planning
            if "complex" in text or "multiple" in text or "architecture" in text:
                return True
        
        return any(ind in text for ind in self.PLANNING_INDICATORS)
    
    def _is_ambiguous(self, text: str) -> bool:
        """Check if request is ambiguous."""
        return any(ind in text for ind in self.AMBIGUITY_INDICATORS)
    
    def _find_sub_intents(self, scores: Dict[IntentType, float], 
                          primary: IntentType) -> List[str]:
        """Find secondary intents."""
        sub = []
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for intent, score in sorted_intents[1:4]:  # Top 3 after primary
            if score > 0:
                sub.append(intent.value)
        return sub
    
    def _build_reasoning(self, intent: IntentType, matches: List[str], 
                         text: str) -> str:
        """Build human-readable reasoning."""
        if not matches:
            return f"classified as {intent.value}"
        
        if len(matches) == 1:
            return f"detected '{matches[0]}' indicates {intent.value}"
        
        return f"detected {', '.join(f'{m!r}' for m in matches[:3])} suggests {intent.value}"
    
    def _unknown_result(self, reason: str) -> IntentResult:
        """Return unknown intent result."""
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            suggested_agent="Flash",
            suggested_workflow="quick_execute",
            is_flash_task=True,
            requires_planning=False,
            requires_confirmation=True,
            estimated_tokens=2000,
            reasoning=reason,
        )
    
    # Convenience methods
    
    def is_simple_query(self, text: str) -> bool:
        """Check if text is a simple query (no code/tools needed)."""
        result = self.analyze(text)
        return result.is_flash_task and result.intent in [
            IntentType.QUICK_TASK, 
            IntentType.QUESTION,
        ]
    
    def should_use_free_model(self, text: str) -> bool:
        """Check if request can use free model (token-efficient)."""
        result = self.analyze(text)
        return (
            result.is_flash_task 
            and result.estimated_tokens < 3000
            and result.intent not in [IntentType.CODING, IntentType.ARCHITECTURE]
        )
    
    def get_model_recommendation(self, text: str) -> Dict[str, str]:
        """Get model recommendation based on intent."""
        result = self.analyze(text)
        
        # Free models for simple tasks
        if result.should_use_free_model:
            return {
                "provider": "zai",
                "model": "qwen3.6-plus-free",
                "reason": "simple task, using free model",
            }
        
        # Complex coding needs capable model
        if result.intent == IntentType.CODING:
            return {
                "provider": "zai",
                "model": "minimax-m2.5-free",
                "reason": "coding task, using capable free model",
            }
        
        # Architecture needs reasoning
        if result.intent == IntentType.ARCHITECTURE:
            return {
                "provider": "zai",
                "model": "minimax-m2.5-free",
                "reason": "architecture task, using reasoning model",
            }
        
        # Default to fast model
        return {
            "provider": "zai",
            "model": "mimo-v2-omni-free",
            "reason": "general task, using fast free model",
        }


# Singleton instance
_gate: Optional[IntentGate] = None


def get_intent_gate() -> IntentGate:
    """Get singleton IntentGate instance."""
    global _gate
    if _gate is None:
        _gate = IntentGate()
    return _gate


def analyze_intent(text: str, context: str = "") -> IntentResult:
    """Convenience function to analyze intent."""
    return get_intent_gate().analyze(text, context)


# CLI test
if __name__ == "__main__":
    gate = IntentGate()
    
    test_cases = [
        "quick show me the files",
        "implement user authentication with JWT",
        "design a microservices architecture",
        "fix the login bug",
        "what is your opinion on this code?",
        "deploy to production",
        "how does this work?",
        "improve the code quality",
    ]
    
    print("\n=== IntentGate Test ===\n")
    for case in test_cases:
        result = gate.analyze(case)
        print(f"Input: {case}")
        print(f"  {result.verbalize()}")
        print(f"  Agent: {result.suggested_agent} | Flash: {result.is_flash_task} | Tokens: ~{result.estimated_tokens}")
        print()
