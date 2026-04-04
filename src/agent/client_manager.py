"""
OpenAI client management for AIAgent.
Extracted from run_agent.py to reduce file size and improve organization.
"""

import logging
import os
import threading
from typing import Any, Dict
from unittest.mock import Mock

from openai import OpenAI

logger = logging.getLogger(__name__)


class ClientManager:
    """Manages OpenAI client creation, validation, and lifecycle for AIAgent."""

    def __init__(self, aizen_agent):
        """Initialize with reference to the AIAgent instance."""
        self.agent = aizen_agent
        self.logger = logger.bind(agent_id=id(aizen_agent))

    def _openai_client_lock(self) -> threading.RLock:
        """Get or create the OpenAI client lock."""
        if not hasattr(self.agent, "_client_lock"):
            lock = threading.RLock()
            self.agent._client_lock = lock
        return self.agent._client_lock

    @staticmethod
    def _is_openai_client_closed(client: Any) -> bool:
        """Check if an OpenAI client is closed."""
        if isinstance(client, Mock):
            return False
        if bool(getattr(client, "is_closed", False)):
            return True
        http_client = getattr(client, "_client", None)
        return bool(getattr(http_client, "is_closed", False))

    def _create_openai_client(
        self, client_kwargs: dict, *, reason: str, shared: bool
    ) -> Any:
        """Create an OpenAI client based on provider configuration."""
        if self.agent.provider == "copilot-acp" or str(
            client_kwargs.get("base_url", "")
        ).startswith("acp://copilot"):
            from agent.copilot_acp_client import CopilotACPClient

            client = CopilotACPClient(**client_kwargs)
            self.logger.info(
                "Copilot ACP client created (%s, shared=%s) %s",
                reason,
                shared,
                self._client_log_context(),
            )
            return client
        client = OpenAI(**client_kwargs)
        self.logger.info(
            "OpenAI client created (%s, shared=%s) %s",
            reason,
            shared,
            self._client_log_context(),
        )
        return client

    def _close_openai_client(self, client: Any, *, reason: str, shared: bool) -> None:
        """Close an OpenAI client safely."""
        if client is None:
            return
        try:
            client.close()
            self.logger.info(
                "OpenAI client closed (%s, shared=%s) %s",
                reason,
                shared,
                self._client_log_context(),
            )
        except Exception as exc:
            self.logger.debug(
                "OpenAI client close failed (%s, shared=%s) %s error=%s",
                reason,
                shared,
                self._client_log_context(),
                exc,
            )

    def _replace_primary_openai_client(self, *, reason: str) -> bool:
        """Replace the primary OpenAI client with a new one."""
        with self._openai_client_lock():
            old_client = getattr(self.agent, "client", None)
            try:
                new_client = self._create_openai_client(
                    self.agent._client_kwargs, reason=reason, shared=True
                )
            except Exception as exc:
                self.logger.warning(
                    "Failed to rebuild shared OpenAI client (%s) %s error=%s",
                    reason,
                    self._client_log_context(),
                    exc,
                )
                return False
            self.agent.client = new_client
        self._close_openai_client(old_client, reason=f"replace:{reason}", shared=True)
        return True

    def _ensure_primary_openai_client(self, *, reason: str) -> Any:
        """Ensure we have a valid primary OpenAI client, recreating if necessary."""
        with self._openai_client_lock():
            client = getattr(self.agent, "client", None)
            if client is not None and not self._is_openai_client_closed(client):
                return client

        self.logger.warning(
            "Detected closed shared OpenAI client; recreating before use (%s) %s",
            reason,
            self._client_log_context(),
        )
        if not self._replace_primary_openai_client(reason=f"recreate_closed:{reason}"):
            raise RuntimeError("Failed to recreate closed OpenAI client")
        with self._openai_client_lock():
            return self.agent.client

    def _create_request_openai_client(self, *, reason: str) -> Any:
        """Create a request-specific OpenAI client (not shared)."""
        from unittest.mock import Mock

        primary_client = self._ensure_primary_openai_client(reason=reason)
        if isinstance(primary_client, Mock):
            return primary_client
        with self._openai_client_lock():
            request_kwargs = dict(self.agent._client_kwargs)
        return self._create_openai_client(request_kwargs, reason=reason, shared=False)

    def _close_request_openai_client(self, client: Any, *, reason: str) -> None:
        """Close a request-specific OpenAI client."""
        self._close_openai_client(client, reason=reason, shared=False)

    def _client_log_context(self) -> str:
        """Generate log context for client operations."""
        provider = getattr(self.agent, "provider", "unknown")
        base_url = getattr(self.agent, "base_url", "unknown")
        model = getattr(self.agent, "model", "unknown")
        thread_identity = getattr(self.agent, "_thread_identity", lambda: "unknown")()
        return (
            f"thread={thread_identity} provider={provider} "
            f"base_url={base_url} model={model}"
        )

    # Credential refresh methods
    def _try_refresh_codex_client_credentials(self, *, force: bool = True) -> bool:
        """Refresh Codex client credentials if needed."""
        if (
            self.agent.api_mode != "codex_responses"
            or self.agent.provider != "openai-codex"
        ):
            return False

        try:
            from aizen_cli.auth import resolve_codex_runtime_credentials

            creds = resolve_codex_runtime_credentials(force_refresh=force)
        except Exception as exc:
            self.logger.debug("Codex credential refresh failed: %s", exc)
            return False

        api_key = creds.get("api_key")
        base_url = creds.get("base_url")
        if not isinstance(api_key, str) or not api_key.strip():
            return False
        if not isinstance(base_url, str) or not base_url.strip():
            return False

        self.agent.api_key = api_key.strip()
        self.agent.base_url = base_url.strip().rstrip("/")
        self.agent._client_kwargs["api_key"] = self.agent.api_key
        self.agent._client_kwargs["base_url"] = self.agent.base_url

        if not self._replace_primary_openai_client(reason="codex_credential_refresh"):
            return False

        return True

    def _try_refresh_nous_client_credentials(self, *, force: bool = True) -> bool:
        """Refresh Nous client credentials if needed."""
        if self.agent.api_mode != "chat_completions" or self.agent.provider != "nous":
            return False

        try:
            from aizen_cli.auth import resolve_nous_runtime_credentials

            creds = resolve_nous_runtime_credentials(
                min_key_ttl_seconds=max(
                    60, int(os.getenv("AIZEN_NOUS_MIN_KEY_TTL_SECONDS", "1800"))
                ),
                timeout_seconds=float(os.getenv("AIZEN_NOUS_TIMEOUT_SECONDS", "15")),
                force_mint=force,
            )
        except Exception as exc:
            self.logger.debug("Nous credential refresh failed: %s", exc)
            return False

        api_key = creds.get("api_key")
        base_url = creds.get("base_url")
        if not isinstance(api_key, str) or not api_key.strip():
            return False
        if not isinstance(base_url, str) or not base_url.strip():
            return False

        self.agent.api_key = api_key.strip()
        self.agent.base_url = base_url.strip().rstrip("/")
        self.agent._client_kwargs["api_key"] = self.agent.api_key
        self.agent._client_kwargs["base_url"] = self.agent.base_url
        # Nous requests should not inherit OpenRouter-only attribution headers.
        self.agent._client_kwargs.pop("default_headers", None)

        if not self._replace_primary_openai_client(reason="nous_credential_refresh"):
            return False

        return True

    def _try_refresh_anthropic_client_credentials(self) -> bool:
        """Refresh Anthropic client credentials if needed."""
        if self.agent.api_mode != "anthropic_messages" or not hasattr(
            self.agent, "_anthropic_api_key"
        ):
            return False
        # Only refresh credentials for the native Anthropic provider.
        # Other anthropic_messages providers (MiniMax, Alibaba, etc.) use their own keys.
        if self.agent.provider != "anthropic":
            return False

        try:
            from agent.anthropic_adapter import (
                resolve_anthropic_token,
                build_anthropic_client,
            )

            new_token = resolve_anthropic_token()
        except Exception as exc:
            self.logger.debug("Anthropic credential refresh failed: %s", exc)
            return False

        if not isinstance(new_token, str) or not new_token.strip():
            return False
        new_token = new_token.strip()
        if new_token == self.agent._anthropic_api_key:
            return False

        try:
            self.agent._anthropic_client.close()
        except Exception:
            pass

        try:
            self.agent._anthropic_client = build_anthropic_client(
                new_token, getattr(self.agent, "_anthropic_base_url", None)
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to rebuild Anthropic client after credential refresh: %s", exc
            )
            return False

        self.agent._anthropic_api_key = new_token
        # Update OAuth flag — token type may have changed (API key ↔ OAuth)
        from agent.anthropic_adapter import _is_oauth_token

        self.agent._is_anthropic_oauth = _is_oauth_token(new_token)
        return True
