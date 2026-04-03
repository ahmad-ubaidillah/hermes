"""AIAgent helper methods - URL detection, content parsing, etc."""

import re
from typing import Dict, Optional


class AIAgentHelpers:
    """Mixin class with helper methods for AIAgent.

    These are small, self-contained methods that can be extracted easily.
    """

    @staticmethod
    def _is_direct_openai_url(base_url: str) -> bool:
        """Return True when a base URL targets OpenAI's native API."""
        url = (base_url or "").lower()
        return "api.openai.com" in url and "openrouter" not in url

    @staticmethod
    def _is_openrouter_url(base_url: str) -> bool:
        """Return True when the base URL targets OpenRouter."""
        return "openrouter" in (base_url or "").lower()

    @staticmethod
    def _is_anthropic_url(base_url: str) -> bool:
        """Return True when the base URL targets Anthropic."""
        url = (base_url or "").lower()
        return "api.anthropic.com" in url or url.rstrip("/").endswith("/anthropic")

    @staticmethod
    def _max_tokens_param(value: int, base_url: str = None) -> dict:
        """Return the correct max tokens kwarg for the current provider."""
        if AIAgentHelpers._is_direct_openai_url(base_url):
            return {"max_completion_tokens": value}
        return {"max_tokens": value}

    @staticmethod
    def _has_content_after_think_block(content: str) -> bool:
        """Check if content has actual text after any reasoning/thinking blocks."""
        if not content:
            return False
        # Check for actual content after think blocks
        think_pattern = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)
        after_think = think_pattern.sub("", content)
        return bool(after_think.strip())

    @staticmethod
    def _strip_think_blocks(content: str) -> str:
        """Remove thinking blocks from content."""
        if not content:
            return content
        # Remove various think block formats
        patterns = [
            re.compile(r"<thinking>.*?</thinking>", re.DOTALL),
            re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL),
            re.compile(r"\n\n\[THINKING\]\n.*?\n\[/THINKING\]", re.DOTALL),
        ]
        result = content
        for pattern in patterns:
            result = pattern.sub("", result)
        return result.strip()

    @staticmethod
    def _mask_api_key_for_logs(key: Optional[str]) -> Optional[str]:
        """Mask API key for safe logging."""
        if not key or len(key) < 12:
            return key
        return f"{key[:4]}...{key[-4:]}"

    @staticmethod
    def _clean_error_message(error_msg: str) -> str:
        """Clean error message for user display."""
        # Remove sensitive information
        cleaned = re.sub(
            r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s,]+', "[API_KEY]", error_msg
        )
        cleaned = re.sub(r'token["\']?\s*[:=]\s*["\']?[^"\'\s,]+', "[TOKEN]", cleaned)
        return cleaned


__all__ = ["AIAgentHelpers"]
