"""Aizen Config Validation Module

Provides:
- Schema validation for config.yaml
- Type checking for all config fields
- Required field validation
- Helpful error messages for invalid configs
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationError:
    """A single validation error."""

    path: str
    message: str
    value: Any = None

    def __str__(self) -> str:
        val_str = f" (got: {self.value!r})" if self.value is not None else ""
        return f"{self.path}: {self.message}{val_str}"


@dataclass
class FieldSpec:
    """Specification for a config field."""

    name: str
    type_: type = str
    required: bool = False
    default: Any = None
    validators: List[Callable[[Any], Optional[str]]] = field(default_factory=list)
    description: str = ""


def _is_non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty string"
    return None


def _is_positive_int(value: Any) -> Optional[str]:
    if not isinstance(value, int) or value <= 0:
        return "must be a positive integer"
    return None


def _is_valid_model(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty string"
    if (
        "/" not in value
        and not value.startswith("gpt-")
        and not value.startswith("claude-")
    ):
        return "should be in 'provider/model' format (e.g., 'openai/gpt-4')"
    return None


def _is_valid_provider(value: Any) -> Optional[str]:
    valid = {
        "openai",
        "anthropic",
        "google",
        "openrouter",
        "nous",
        "zai",
        "kimi-coding",
        "minimax",
        "groq",
        "auto",
        "custom",
    }
    if not isinstance(value, str):
        return "must be a string"
    if value.lower() not in valid:
        return f"must be one of: {', '.join(sorted(valid))}"
    return None


def _is_valid_log_level(value: Any) -> Optional[str]:
    valid = {"debug", "info", "warning", "error", "critical"}
    if not isinstance(value, str):
        return "must be a string"
    if value.lower() not in valid:
        return f"must be one of: {', '.join(sorted(valid))}"
    return None


def _is_valid_env_type(value: Any) -> Optional[str]:
    valid = {"local", "docker", "ssh", "modal", "daytona", "singularity"}
    if not isinstance(value, str):
        return "must be a string"
    if value.lower() not in valid:
        return f"must be one of: {', '.join(sorted(valid))}"
    return None


# ---------------------------------------------------------------------------
# Config Schema
# ---------------------------------------------------------------------------

CONFIG_SCHEMA: Dict[str, Dict[str, FieldSpec]] = {
    "model": {
        "default": FieldSpec("model.default", type_=str, validators=[_is_valid_model]),
        "provider": FieldSpec(
            "model.provider", type_=str, validators=[_is_valid_provider]
        ),
        "base_url": FieldSpec("model.base_url", type_=str),
        "api_key": FieldSpec("model.api_key", type_=str),
        "temperature": FieldSpec("model.temperature", type_=(int, float)),
        "max_tokens": FieldSpec(
            "model.max_tokens", type_=int, validators=[_is_positive_int]
        ),
    },
    "display": {
        "compact": FieldSpec("display.compact", type_=bool),
        "verbose": FieldSpec("display.verbose", type_=bool),
        "tool_progress": FieldSpec("display.tool_progress", type_=str),
        "busy_input_mode": FieldSpec("display.busy_input_mode", type_=str),
        "skin": FieldSpec("display.skin", type_=str),
        "background_process_notifications": FieldSpec(
            "display.background_process_notifications", type_=str
        ),
        "log_level": FieldSpec(
            "display.log_level", type_=str, validators=[_is_valid_log_level]
        ),
    },
    "agent": {
        "max_turns": FieldSpec(
            "agent.max_turns", type_=int, validators=[_is_positive_int]
        ),
        "save_trajectories": FieldSpec("agent.save_trajectories", type_=bool),
        "quiet_mode": FieldSpec("agent.quiet_mode", type_=bool),
        "skip_context_files": FieldSpec("agent.skip_context_files", type_=bool),
        "skip_memory": FieldSpec("agent.skip_memory", type_=bool),
    },
    "terminal": {
        "env_type": FieldSpec(
            "terminal.env_type", type_=str, validators=[_is_valid_env_type]
        ),
        "shell": FieldSpec("terminal.shell", type_=str),
        "timeout": FieldSpec(
            "terminal.timeout", type_=int, validators=[_is_positive_int]
        ),
    },
    "auxiliary": {
        "vision": FieldSpec("auxiliary.vision", type_=dict),
        "summarization": FieldSpec("auxiliary.summarization", type_=dict),
    },
    "mcp": {
        "servers": FieldSpec("mcp.servers", type_=dict),
    },
    "quick_commands": {
        "limits": FieldSpec("quick_commands.limits", type_=dict),
    },
}


def _validate_field(path: str, value: Any, spec: FieldSpec) -> List[ValidationError]:
    """Validate a single field against its spec."""
    errors = []

    # Type check
    if not isinstance(value, spec.type_):
        errors.append(
            ValidationError(
                path=path,
                message=f"expected type {spec.type_.__name__}",
                value=value,
            )
        )
        return errors

    # Custom validators
    for validator in spec.validators:
        msg = validator(value)
        if msg:
            errors.append(ValidationError(path=path, message=msg, value=value))

    return errors


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate a config dictionary against the schema.

    Args:
        config: The config dictionary to validate.

    Returns:
        List of error message strings. Empty if valid.
    """
    errors: List[ValidationError] = []

    for section_name, fields in CONFIG_SCHEMA.items():
        section = config.get(section_name)
        if section is None:
            continue  # Section is optional if not present

        if not isinstance(section, dict):
            errors.append(
                ValidationError(
                    path=section_name,
                    message=f"expected a dict, got {type(section).__name__}",
                    value=section,
                )
            )
            continue

        for field_name, spec in fields.items():
            value = section.get(field_name)
            if value is None:
                if spec.required:
                    errors.append(
                        ValidationError(
                            path=spec.name,
                            message="required field is missing",
                        )
                    )
                continue

            errors.extend(_validate_field(spec.name, value, spec))

    return [str(e) for e in errors]


def validate_config_strict(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate config and return (is_valid, errors)."""
    errors = validate_config(config)
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Config Migration System
# ---------------------------------------------------------------------------

CURRENT_CONFIG_VERSION = 6

_MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def migration(version: int):
    """Decorator to register a config migration function."""

    def decorator(fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Callable:
        _MIGRATIONS[version] = fn
        return fn

    return decorator


@migration(2)
def _migrate_v1_to_v2(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v1 to v2: Add display section if missing."""
    if "display" not in config:
        config["display"] = {}
    return config


@migration(3)
def _migrate_v2_to_v3(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v2 to v3: Rename 'max_iterations' to 'agent.max_turns'."""
    if "max_iterations" in config:
        if "agent" not in config:
            config["agent"] = {}
        config["agent"]["max_turns"] = config.pop("max_iterations")
    return config


@migration(4)
def _migrate_v3_to_v4(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v3 to v4: Add terminal section."""
    if "terminal" not in config:
        config["terminal"] = {"env_type": "local"}
    return config


@migration(5)
def _migrate_v4_to_v5(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v4 to v5: Move root-level keys into proper sections."""
    for key in ("verbose", "quiet_mode", "save_trajectories"):
        if key in config:
            if "agent" not in config:
                config["agent"] = {}
            config["agent"][key] = config.pop(key)
    return config


@migration(6)
def _migrate_v5_to_v6(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v5 to v6: Add auxiliary section defaults."""
    if "auxiliary" not in config:
        config["auxiliary"] = {}
    return config


def migrate_config(config: Dict[str, Any], from_version: int = 1) -> Dict[str, Any]:
    """Migrate config from an old version to the current version.

    Args:
        config: The config dictionary to migrate.
        from_version: The version of the config (from _config_version in config).

    Returns:
        The migrated config dictionary.
    """
    current = from_version
    while current < CURRENT_CONFIG_VERSION:
        next_version = current + 1
        if next_version in _MIGRATIONS:
            logger.info("Migrating config from v%d to v%d", current, next_version)
            config = _MIGRATIONS[next_version](config)
        current = next_version
    return config


def get_config_version(config: Dict[str, Any]) -> int:
    """Get the config version from the config dict."""
    return config.get("_config_version", 1)


def needs_migration(config: Dict[str, Any]) -> bool:
    """Check if config needs migration."""
    return get_config_version(config) < CURRENT_CONFIG_VERSION
