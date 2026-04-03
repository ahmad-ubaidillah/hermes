"""CLI Configuration helpers."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_aizen_home = None  # Set by parent


def _init_aizen_home():
    global _aizen_home
    if _aizen_home is None:
        from core.aizen_constants import get_aizen_home

        _aizen_home = get_aizen_home()


def _load_prefill_messages(file_path: str) -> List[Dict[str, Any]]:
    """Load ephemeral prefill messages from a JSON file."""
    _init_aizen_home()
    if not file_path:
        return []
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = _aizen_home / path
    if not path.exists():
        logger.warning("Prefill messages file not found: %s", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("Prefill messages file must contain a JSON array: %s", path)
            return []
        return data
    except Exception as e:
        logger.warning("Failed to load prefill messages from %s: %s", path, e)
        return []


def _parse_reasoning_config(effort: str) -> dict | None:
    """Parse a reasoning effort level into an OpenRouter reasoning config dict."""
    from core.aizen_constants import parse_reasoning_effort

    result = parse_reasoning_effort(effort)
    if effort and effort.strip() and result is None:
        logger.warning("Unknown reasoning_effort '%s', using default (medium)", effort)
    return result


def load_cli_config() -> Dict[str, Any]:
    """Load CLI configuration from config files."""
    from core.aizen_constants import OPENROUTER_BASE_URL, get_aizen_home

    _aizen_home = get_aizen_home()
    user_config_path = _aizen_home / "config.yaml"
    project_config_path = Path(__file__).parent / "cli-config.yaml"

    if user_config_path.exists():
        config_path = user_config_path
    else:
        config_path = project_config_path

    defaults = {
        "model": {
            "default": "anthropic/claude-opus-4.6",
            "base_url": OPENROUTER_BASE_URL,
            "provider": "auto",
        },
        "terminal": {
            "env_type": "local",
            "cwd": ".",
            "timeout": 60,
            "lifetime_seconds": 300,
        },
    }

    if not config_path.exists():
        return defaults

    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config is None:
            return defaults
        return {**defaults, **config}
    except Exception as e:
        logger.warning("Failed to load config from %s: %s", config_path, e)
        return defaults
