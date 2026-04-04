"""AIAgent initialization - extracted from run_agent.py for modularity."""

import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent.anthropic_adapter import (
    build_anthropic_client,
    resolve_anthropic_token,
    _is_oauth_token as _is_oat,
)
from agent.redact import RedactingFormatter
from core.aizen_constants import OPENROUTER_BASE_URL
from agent.model_metadata import fetch_model_metadata
from logging.handlers import RotatingFileHandler

from src.agent.iteration_budget import IterationBudget
from src.agent.safe_writer import _SafeWriter, _install_safe_stdio
from agent.distill import (
    ContentClassifier,
    ContentScorer,
    ContentCollapser,
    ContentComposer,
    SignalTier,
)
from src.agent.client_manager import ClientManager


def _extract_init_self():
    """Extract self attributes for initialization."""
    pass


class AizenInit:
    """Handles AIAgent initialization logic."""

    def __init__(self, agent):
        self.agent = agent

    def initialize(
        self,
        base_url: str = None,
        api_key: str = None,
        provider: str = None,
        api_mode: str = None,
        acp_command: str = None,
        acp_args: list[str] | None = None,
        command: str = None,
        args: list[str] | None = None,
        model: str = "anthropic/claude-opus-4.6",
        max_iterations: int = 90,
        tool_delay: float = 1.0,
        enabled_toolsets: List[str] = None,
        disabled_toolsets: List[str] = None,
        save_trajectories: bool = False,
        verbose_logging: bool = False,
        quiet_mode: bool = False,
        ephemeral_system_prompt: str = None,
        log_prefix_chars: int = 100,
        log_prefix: str = "",
        providers_allowed: List[str] = None,
        providers_ignored: List[str] = None,
        providers_order: List[str] = None,
        provider_sort: str = None,
        provider_require_parameters: bool = False,
        provider_data_collection: str = None,
        session_id: str = None,
        tool_progress_callback: callable = None,
        thinking_callback: callable = None,
        reasoning_callback: callable = None,
        clarify_callback: callable = None,
        step_callback: callable = None,
        stream_delta_callback: callable = None,
        tool_gen_callback: callable = None,
        status_callback: callable = None,
        max_tokens: int = None,
        reasoning_config: Dict[str, Any] = None,
        prefill_messages: List[Dict[str, Any]] = None,
        platform: str = None,
        skip_context_files: bool = False,
        skip_memory: bool = False,
        session_db=None,
        iteration_budget: "IterationBudget" = None,
        fallback_model: Dict[str, Any] = None,
        checkpoints_enabled: bool = False,
        checkpoint_max_snapshots: int = 50,
        pass_session_id: bool = False,
        persist_session: bool = True,
    ):
        """Initialize the AI Agent with all configuration options."""
        _install_safe_stdio()

        # Basic attributes
        self.agent.model = model
        self.agent.max_iterations = max_iterations
        self.agent.iteration_budget = iteration_budget or IterationBudget(
            max_iterations
        )
        self.agent.tool_delay = tool_delay
        self.agent.save_trajectories = save_trajectories
        self.agent.verbose_logging = verbose_logging
        self.agent.quiet_mode = quiet_mode
        self.agent.ephemeral_system_prompt = ephemeral_system_prompt
        self.agent.platform = platform
        self.agent._print_fn = None
        self.agent.background_review_callback = None
        self.agent.skip_context_files = skip_context_files
        self.agent.pass_session_id = pass_session_id
        self.agent.persist_session = persist_session
        self.agent.log_prefix_chars = log_prefix_chars
        self.agent.log_prefix = f"{log_prefix} " if log_prefix else ""

        # Store effective base URL for feature detection
        self.agent.base_url = base_url or OPENROUTER_BASE_URL
        provider_name = (
            provider.strip().lower()
            if isinstance(provider, str) and provider.strip()
            else None
        )
        self.agent.provider = provider_name or "openrouter"
        self.agent.acp_command = acp_command or command
        self.agent.acp_args = list(acp_args or args or [])

        # Determine API mode
        if api_mode in {"chat_completions", "codex_responses", "anthropic_messages"}:
            self.agent.api_mode = api_mode
        elif self.agent.provider == "openai-codex":
            self.agent.api_mode = "codex_responses"
        elif (
            provider_name is None
        ) and "chatgpt.com/backend-api/codex" in self.agent._base_url_lower:
            self.agent.api_mode = "codex_responses"
            self.agent.provider = "openai-codex"
        elif self.agent.provider == "anthropic" or (
            provider_name is None and "api.anthropic.com" in self.agent._base_url_lower
        ):
            self.agent.api_mode = "anthropic_messages"
            self.agent.provider = "anthropic"
        elif self.agent._base_url_lower.rstrip("/").endswith("/anthropic"):
            self.agent.api_mode = "anthropic_messages"
            self.agent.provider = "anthropic"
        else:
            self.agent.api_mode = "chat_completions"

        # Direct OpenAI sessions use the Responses API path
        if self.agent.api_mode == "chat_completions" and self._is_direct_openai_url():
            self.agent.api_mode = "codex_responses"

        # Pre-warm OpenRouter model metadata cache
        if self.agent.provider == "openrouter" or self._is_openrouter_url():
            threading.Thread(
                target=lambda: fetch_model_metadata(),
                daemon=True,
            ).start()

        self.agent.tool_progress_callback = tool_progress_callback
        self.agent.thinking_callback = thinking_callback
        self.agent.reasoning_callback = reasoning_callback
        self.agent._reasoning_deltas_fired = False
        self.agent.clarify_callback = clarify_callback
        self.agent.step_callback = step_callback
        self.agent.stream_delta_callback = stream_delta_callback
        self.agent.status_callback = status_callback
        self.agent.tool_gen_callback = tool_gen_callback
        self.agent._last_reported_tool = None
        self.agent._executing_tools = False
        self.agent._interrupt_requested = False
        self.agent._interrupt_message = None
        self.agent._client_lock = threading.RLock()

        # Subagent delegation state
        self.agent._delegate_depth = 0
        self.agent._active_children = []
        self.agent._active_children_lock = threading.Lock()

        # Store OpenRouter provider preferences
        self.agent.providers_allowed = providers_allowed
        self.agent.providers_ignored = providers_ignored
        self.agent.providers_order = providers_order
        self.agent.provider_sort = provider_sort
        self.agent.provider_require_parameters = provider_require_parameters
        self.agent.provider_data_collection = provider_data_collection

        # Store toolset filtering options
        self.agent.enabled_toolsets = enabled_toolsets
        self.agent.disabled_toolsets = disabled_toolsets

        # Model response configuration
        self.agent.max_tokens = max_tokens
        self.agent.reasoning_config = reasoning_config
        self.agent.prefill_messages = prefill_messages or []

        # Anthropic prompt caching
        is_openrouter = self._is_openrouter_url()
        is_claude = "claude" in self.agent.model.lower()
        is_native_anthropic = self.agent.api_mode == "anthropic_messages"
        self.agent._use_prompt_caching = (
            is_openrouter and is_claude
        ) or is_native_anthropic
        self.agent._cache_ttl = "5m"

        # Iteration budget pressure
        self.agent._budget_caution_threshold = 0.7
        self.agent._budget_warning_threshold = 0.9
        self.agent._budget_pressure_enabled = True

        # Context pressure warnings
        self.agent._context_pressure_warned = False

        # Persistent error log
        self._setup_error_logging()

        # Set logging level
        self._setup_logging_levels(verbose_logging, quiet_mode)

        # Initialize internal state
        self.agent._stream_callback = None
        self.agent._stream_needs_break = False
        self.agent._persist_user_message_idx = None
        self.agent._persist_user_message_override = None
        self.agent._anthropic_image_fallback_cache = {}

        # Initialize LLM client
        self._initialize_llm_client(api_key, base_url)

        # Initialize client manager for OpenAI client lifecycle management
        self.agent.client_manager = ClientManager(self.agent)

        # Initialize distillation pipeline for enhanced context compression
        self.agent.content_classifier = ContentClassifier()
        self.agent.content_scorer = ContentScorer()
        self.agent.content_collapser = ContentCollapser()
        self.agent.content_composer = ContentComposer()

        if not self.agent.quiet_mode:
            print(
                f"🤖 AI Agent initialized with model: {self.agent.model}"
                + (
                    " (Anthropic native)"
                    if self.agent.api_mode == "anthropic_messages"
                    else ""
                )
            )
            if (
                hasattr(self.agent, "_anthropic_api_key")
                and self.agent._anthropic_api_key
            ):
                if len(self.agent._anthropic_api_key) > 12:
                    print(
                        f"🔑 Using token: {self.agent._anthropic_api_key[:8]}...{self.agent._anthropic_api_key[-4:]}"
                    )

    def _setup_error_logging(self):
        """Setup persistent error logging."""
        import logging
        from core.aizen_constants import get_aizen_home

        root_logger = logging.getLogger()
        error_log_dir = get_aizen_home() / "logs"
        error_log_path = error_log_dir / "errors.log"
        resolved_error_log_path = error_log_path.resolve()
        has_errors_log_handler = any(
            isinstance(handler, RotatingFileHandler)
            and Path(getattr(handler, "baseFilename", "")).resolve()
            == resolved_error_log_path
            for handler in root_logger.handlers
        )

        if not has_errors_log_handler:
            error_log_dir.mkdir(parents=True, exist_ok=True)
            error_file_handler = RotatingFileHandler(
                error_log_path,
                maxBytes=2 * 1024 * 1024,
                backupCount=2,
            )
            error_file_handler.setLevel(logging.WARNING)
            error_file_handler.setFormatter(
                RedactingFormatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s",
                )
            )
            root_logger.addHandler(error_file_handler)

    def _setup_logging_levels(self, verbose_logging: bool, quiet_mode: bool):
        """Setup logging levels based on configuration."""
        import logging

        if verbose_logging:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            for handler in logging.getLogger().handlers:
                handler.setFormatter(
                    RedactingFormatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S",
                    )
                )
            logging.getLogger("openai").setLevel(logging.WARNING)
            logging.getLogger("openai._base_client").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("asyncio").setLevel(logging.WARNING)
            logging.getLogger("hpack").setLevel(logging.WARNING)
            logging.getLogger("hpack.hpack").setLevel(logging.WARNING)
            logging.getLogger("grpc").setLevel(logging.WARNING)
            logging.getLogger("modal").setLevel(logging.WARNING)
            logging.getLogger("rex-deploy").setLevel(logging.INFO)
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            logging.getLogger("openai").setLevel(logging.ERROR)
            logging.getLogger("openai._base_client").setLevel(logging.ERROR)
            logging.getLogger("httpx").setLevel(logging.ERROR)
            logging.getLogger("httpcore").setLevel(logging.ERROR)
            if quiet_mode:
                for quiet_logger in [
                    "tools",
                    "run_agent",
                    "trajectory_compressor",
                    "cron",
                    "aizen_cli",
                ]:
                    logging.getLogger(quiet_logger).setLevel(logging.ERROR)

    def _initialize_llm_client(self, api_key: str, base_url: str):
        """Initialize the LLM client based on provider and mode."""
        if self.agent.api_mode == "anthropic_messages":
            _is_native_anthropic = self.agent.provider == "anthropic"
            effective_key = (
                (api_key or resolve_anthropic_token() or "")
                if _is_native_anthropic
                else (api_key or "")
            )
            self.agent.api_key = effective_key
            self.agent._anthropic_api_key = effective_key
            self.agent._anthropic_base_url = base_url
            self.agent._is_anthropic_oauth = _is_oat(effective_key)
            self.agent._anthropic_client = build_anthropic_client(
                effective_key, base_url
            )
            self.agent.client = None
            self.agent._client_kwargs = {}
        else:
            if api_key and base_url:
                client_kwargs = {"api_key": api_key, "base_url": base_url}
                if self.agent.provider == "copilot-acp":
                    client_kwargs["command"] = self.agent.acp_command
                    client_kwargs["args"] = self.agent.acp_args
                effective_base = base_url
                if "openrouter" in effective_base.lower():
                    client_kwargs["default_headers"] = {
                        "HTTP-Referer": "https://aizen-agent.nousresearch.com",
                        "X-OpenRouter-Title": "Aizen Agent",
                        "X-OpenRouter-Categories": "productivity,cli-agent",
                    }
                elif "api.githubcopilot.com" in effective_base.lower():
                    from aizen_cli.models import copilot_default_headers

                    client_kwargs["default_headers"] = copilot_default_headers()
                elif "api.kimi.com" in effective_base.lower():
                    client_kwargs["default_headers"] = {
                        "User-Agent": "KimiCLI/1.3",
                    }
                self.agent.client = None
                self.agent._client_kwargs = client_kwargs
            else:
                from agent.auxiliary_client import resolve_provider_client

                # For backward compatibility, we use resolve_provider_client and extract credentials
                client, resolved_model = resolve_provider_client(
                    provider=self.agent.provider,
                    explicit_base_url=None,
                    explicit_api_key=None,
                )
                if client is not None:
                    self.agent.base_url = str(
                        getattr(client, "base_url", self.agent.base_url)
                    )
                    effective_key = getattr(client, "api_key", api_key)
                else:
                    # Fallback to environment variables
                    self.agent.base_url = self.agent.base_url
                    effective_key = api_key
                client_kwargs = {
                    "api_key": effective_key,
                    "base_url": self.agent.base_url,
                }
                if self.agent.provider == "copilot-acp":
                    client_kwargs["command"] = self.agent.acp_command
                    client_kwargs["args"] = self.agent.acp_args
                if "openrouter" in self.agent.base_url.lower():
                    client_kwargs["default_headers"] = {
                        "HTTP-Referer": "https://aizen-agent.nousresearch.com",
                        "X-OpenRouter-Title": "Aizen Agent",
                        "X-OpenRouter-Categories": "productivity,cli-agent",
                    }
                self.agent.client = None
                self.agent._client_kwargs = client_kwargs

    def _is_openrouter_url(self) -> bool:
        """Check if the base URL is an OpenRouter URL."""
        return "openrouter" in self.agent.base_url.lower()

    def _is_direct_openai_url(self) -> bool:
        """Check if the base URL is a direct OpenAI URL."""
        return (
            "api.openai.com" in self.agent.base_url.lower()
            and not self.agent.base_url.lower().endswith("/v1")
        )
