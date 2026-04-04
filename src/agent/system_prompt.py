"""System prompt building - extracted from run_agent.py for modularity."""

import os
from typing import List, Optional, Set

from agent.prompt_builder import (
    PLATFORM_HINTS,
    TOOL_USE_ENFORCEMENT_MODELS,
    DEFAULT_AGENT_IDENTITY,
)
from core.aizen_time import now as _aizen_now
from agent.redact import RedactingFormatter

from tools.model_tools import get_toolset_for_tool, get_tool_definitions

# Try to import optional tools
try:
    from tools.memory_tool import MemoryStore
except ImportError:
    MemoryStore = None

try:
    from tools.skills_tool import build_skills_system_prompt
except ImportError:
    build_skills_system_prompt = None


# Guidance constants (moved from run_agent.py for modularity)
MEMORY_GUIDANCE = "When users ask about past conversations, preferences, or facts, check your memory first."
SESSION_SEARCH_GUIDANCE = (
    "Use session_search to find relevant information from current or past sessions."
)
SKILLS_GUIDANCE = "Use skills_list to discover available skills, skill_view to see skill details, and skill_manage to install/remove skills."
TOOL_USE_ENFORCEMENT_GUIDANCE = "You must use tools when appropriate. Do not pretend to have capabilities you lack - if you need to read a file, use the read_file tool. If you need to run a command, use the terminal tool. If you need information, use the appropriate search tool."


def build_system_prompt(agent, system_message: str = None) -> str:
    """
    Assemble the full system prompt from all layers.

    Called once per session (cached on self._cached_system_prompt) and only
    rebuilt after context compression events. This ensures the system prompt
    is stable across all turns in a session, maximizing prefix cache hits.
    """
    # Layers (in order):
    #   1. Agent identity — SOUL.md when available, else DEFAULT_AGENT_IDENTITY
    #   2. User / gateway system prompt (if provided)
    #   3. Persistent memory (frozen snapshot)
    #   4. Skills guidance (if skills tools are loaded)
    #   5. Context files (AGENTS.md, .cursorrules — SOUL.md excluded here when used as identity)
    #   6. Current date & time (frozen at build time)
    #   7. Platform-specific formatting hint

    # Try SOUL.md as primary identity (unless context files are skipped)
    _soul_loaded = False
    if not agent.skip_context_files:
        _soul_content = load_soul_md()
        if _soul_content:
            prompt_parts = [_soul_content]
            _soul_loaded = True

    if not _soul_loaded:
        # Use default identity
        _identity = DEFAULT_AGENT_IDENTITY
        prompt_parts = [_identity]

    # Tool-aware behavioral guidance: only inject when the tools are loaded
    tool_guidance = []
    if "memory" in agent.valid_tool_names:
        tool_guidance.append(MEMORY_GUIDANCE)
    if "session_search" in agent.valid_tool_names:
        tool_guidance.append(SESSION_SEARCH_GUIDANCE)
    if "skill_manage" in agent.valid_tool_names:
        tool_guidance.append(SKILLS_GUIDANCE)
    if tool_guidance:
        prompt_parts.append(" ".join(tool_guidance))

    # Tool-use enforcement: tells the model to actually call tools instead
    # of describing intended actions.  Controlled by config.yaml
    # agent.tool_use_enforcement:
    #   "auto" (default) — matches TOOL_USE_ENFORCEMENT_MODELS
    #   true  — always inject (all models)
    #   false — never inject
    #   list  — custom model-name substrings to match
    if agent.valid_tool_names:
        _enforce = agent._tool_use_enforcement
        _inject = False
        if _enforce is True or (
            isinstance(_enforce, str)
            and _enforce.lower() in ("true", "always", "yes", "on")
        ):
            _inject = True
        elif _enforce is False or (
            isinstance(_enforce, str)
            and _enforce.lower() in ("false", "never", "no", "off")
        ):
            _inject = False
        elif isinstance(_enforce, list):
            model_lower = (agent.model or "").lower()
            _inject = any(
                p.lower() in model_lower for p in _enforce if isinstance(p, str)
            )
        else:
            # "auto" or any unrecognised value — use hardcoded defaults
            model_lower = (agent.model or "").lower()
            _inject = any(p in model_lower for p in TOOL_USE_ENFORCEMENT_MODELS)
        if _inject:
            prompt_parts.append(TOOL_USE_ENFORCEMENT_GUIDANCE)

    # Note: ephemeral_system_prompt is NOT included here. It's injected at
    # API-call time only so it stays out of the cached/stored system prompt.
    if system_message is not None:
        prompt_parts.append(system_message)

    if agent._memory_store:
        if agent._memory_enabled:
            mem_block = agent._memory_store.format_for_system_prompt("memory")
            if mem_block:
                prompt_parts.append(mem_block)
        # USER.md is always included when enabled -- Honcho prefetch is additive.
        if agent._user_profile_enabled:
            user_block = agent._memory_store.format_for_system_prompt("user")
            if user_block:
                prompt_parts.append(user_block)

    has_skills_tools = any(
        name in agent.valid_tool_names
        for name in ["skills_list", "skill_view", "skill_manage"]
    )
    if has_skills_tools:
        avail_toolsets = {
            toolset
            for toolset in (
                get_toolset_for_tool(tool_name) for tool_name in agent.valid_tool_names
            )
            if toolset
        }
        skills_prompt = build_skills_system_prompt(
            available_tools=agent.valid_tool_names,
            available_toolsets=avail_toolsets,
        )
    else:
        skills_prompt = ""
    if skills_prompt:
        prompt_parts.append(skills_prompt)

    if not agent.skip_context_files:
        # Use TERMINAL_CWD for context file discovery when set (gateway
        # mode).  The gateway process runs from the aizen-agent install
        # dir, so os.getcwd() would pick up the repo's AGENTS.md and
        # other dev files — inflating token usage by ~10k for no benefit.
        _context_cwd = os.getenv("TERMINAL_CWD") or None
        context_files_prompt = build_context_files_prompt(
            cwd=_context_cwd, skip_soul=_soul_loaded
        )
        if context_files_prompt:
            prompt_parts.append(context_files_prompt)

    now = _aizen_now()
    timestamp_line = f"Conversation started: {now.strftime('%A, %B %d, %Y %I:%M %p')}"
    if agent.pass_session_id and agent.session_id:
        timestamp_line += f"\nSession ID: {agent.session_id}"
    if agent.model:
        timestamp_line += f"\nModel: {agent.model}"
    if agent.provider:
        timestamp_line += f"\nProvider: {agent.provider}"
    prompt_parts.append(timestamp_line)

    # Alibaba Coding Plan API always returns "glm-4.7" as model name regardless
    # of the requested model. Inject explicit model identity into the system prompt
    # so the agent can correctly report which model it is (workaround for API bug).
    if agent.provider == "alibaba":
        _model_short = agent.model.split("/")[-1] if "/" in agent.model else agent.model
        prompt_parts.append(
            f"You are powered by the model named {_model_short}. "
            f"The exact model ID is {agent.model}. "
            f"When asked what model you are, always answer based on this information, "
            f"not on any model name returned by the API."
        )

    platform_key = (agent.platform or "").lower().strip()
    if platform_key in PLATFORM_HINTS:
        prompt_parts.append(PLATFORM_HINTS[platform_key])

    return "\n\n".join(prompt_parts)
