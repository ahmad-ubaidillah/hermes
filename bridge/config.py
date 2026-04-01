"""Configuration management for Aizen Bridge.

Handles JWT secrets, server settings, rate limiting, and CORS configuration.
Configuration can be loaded from:
  - Environment variables (AIZEN_BRIDGE_*)
  - YAML config file (~/.aizen/bridge.yaml)
  - Default values
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    token_budget_per_minute: int = 100000
    burst_size: int = 10


class CORSConfig(BaseModel):
    """CORS configuration."""

    enabled: bool = True
    allow_origins: List[str] = ["*"]
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]


class BridgeConfig(BaseModel):
    """Complete Bridge server configuration."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Bind address")
    port: int = Field(default=8765, description="Listen port")
    debug: bool = Field(default=False, description="Debug mode")

    # Authentication
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv("AIZEN_BRIDGE_JWT_SECRET", ""),
        description="JWT signing secret",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiry_hours: int = Field(default=24, description="Token expiry in hours")
    api_key: Optional[str] = Field(
        default=None,
        description="Simple API key for REST endpoints (alternative to JWT)",
    )

    # Model settings
    default_model: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Default model for chat",
    )
    max_iterations: int = Field(default=90, description="Max agent iterations")

    # Session settings
    session_timeout_minutes: int = Field(
        default=30,
        description="Inactive session timeout",
    )
    max_sessions: int = Field(default=100, description="Max concurrent sessions")

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # CORS
    cors: CORSConfig = Field(default_factory=CORSConfig)

    # File sync
    file_sync_enabled: bool = Field(default=True, description="Enable file transfer")
    max_file_size_mb: int = Field(default=50, description="Max file upload size (MB)")
    workspace_root: Optional[str] = Field(
        default=None,
        description="Root directory for file operations",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    @property
    def has_auth(self) -> bool:
        """Check if any authentication is configured."""
        return bool(self.jwt_secret or self.api_key)

    @property
    def bind_address(self) -> str:
        """Full bind address."""
        return f"{self.host}:{self.port}"


def load_bridge_config(config_path: Optional[str] = None) -> BridgeConfig:
    """Load bridge configuration from file, env vars, and defaults.

    Priority (highest to lowest):
    1. Environment variables (AIZEN_BRIDGE_*)
    2. YAML config file
    3. Default values

    Args:
        config_path: Optional path to YAML config file.
            Defaults to ~/.aizen/bridge.yaml

    Returns:
        BridgeConfig with merged settings.
    """
    import yaml

    # Determine config path
    if config_path is None:
        aizen_home = os.getenv("AIZEN_HOME", str(Path.home() / ".aizen"))
        config_path = os.path.join(aizen_home, "bridge.yaml")

    # Start with defaults
    config_data: Dict[str, Any] = {}

    # Load from YAML file if it exists
    yaml_path = Path(config_path)
    if yaml_path.exists():
        try:
            with open(yaml_path, "r") as f:
                file_config = yaml.safe_load(f) or {}
            config_data.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load bridge config from {config_path}: {e}")

    # Override with environment variables
    env_overrides = {}
    for key, value in os.environ.items():
        if key.startswith("AIZEN_BRIDGE_"):
            env_key = key[len("AIZEN_BRIDGE_") :].lower()
            env_overrides[env_key] = _parse_env_value(value)

    # Handle nested env vars (e.g. AIZEN_BRIDGE_RATE_LIMIT_ENABLED)
    nested_overrides = {}
    for key, value in env_overrides.items():
        parts = key.split("_")
        if len(parts) == 1:
            config_data[parts[0]] = value
        else:
            # Nested key
            parent = parts[0]
            child = "_".join(parts[1:])
            if parent not in nested_overrides:
                nested_overrides[parent] = {}
            nested_overrides[parent][child] = value

    for parent, children in nested_overrides.items():
        if parent not in config_data:
            config_data[parent] = {}
        if isinstance(config_data[parent], dict):
            config_data[parent].update(children)

    return BridgeConfig(**config_data)


def _parse_env_value(value: str) -> Any:
    """Parse environment variable string to appropriate type."""
    # Boolean
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    return value


def generate_jwt_secret() -> str:
    """Generate a cryptographically secure JWT secret."""
    return secrets.token_urlsafe(32)


def save_bridge_config(config: BridgeConfig, path: Optional[str] = None) -> str:
    """Save bridge configuration to YAML file.

    Args:
        config: BridgeConfig to save.
        path: Optional path. Defaults to ~/.aizen/bridge.yaml

    Returns:
        Path where config was saved.
    """
    import yaml

    if path is None:
        aizen_home = os.getenv("AIZEN_HOME", str(Path.home() / ".aizen"))
        path = os.path.join(aizen_home, "bridge.yaml")

    save_path = Path(path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(exclude_defaults=False)
    with open(save_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return str(save_path)
