"""Tests for hermes_config validation module."""

import pytest

from hermes_config import (
    ValidationError,
    validate_config,
    validate_config_strict,
    CONFIG_SCHEMA,
    migrate_config,
    get_config_version,
    needs_migration,
    CURRENT_CONFIG_VERSION,
    _MIGRATIONS,
)


class TestValidateConfig:
    def test_empty_config_is_valid(self):
        errors = validate_config({})
        assert errors == []

    def test_valid_model_config(self):
        config = {
            "model": {
                "default": "openai/gpt-4",
                "provider": "openai",
            }
        }
        errors = validate_config(config)
        assert errors == []

    def test_invalid_model_format(self):
        config = {"model": {"default": "just-a-name"}}
        errors = validate_config(config)
        assert any("provider/model" in e for e in errors)

    def test_invalid_provider(self):
        config = {"model": {"provider": "invalid-provider-xyz"}}
        errors = validate_config(config)
        assert any("must be one of" in e for e in errors)

    def test_valid_provider_values(self):
        for provider in [
            "openai",
            "anthropic",
            "google",
            "openrouter",
            "nous",
            "auto",
            "custom",
        ]:
            config = {"model": {"provider": provider}}
            errors = validate_config(config)
            assert errors == [], f"Provider '{provider}' should be valid"

    def test_invalid_type_for_model_default(self):
        config = {"model": {"default": 123}}
        errors = validate_config(config)
        assert any("expected type str" in e for e in errors)

    def test_invalid_type_for_max_turns(self):
        config = {"agent": {"max_turns": "not-a-number"}}
        errors = validate_config(config)
        assert any("expected type int" in e for e in errors)

    def test_negative_max_turns(self):
        config = {"agent": {"max_turns": -1}}
        errors = validate_config(config)
        assert any("positive integer" in e for e in errors)

    def test_zero_max_turns(self):
        config = {"agent": {"max_turns": 0}}
        errors = validate_config(config)
        assert any("positive integer" in e for e in errors)

    def test_valid_positive_max_turns(self):
        config = {"agent": {"max_turns": 50}}
        errors = validate_config(config)
        assert errors == []

    def test_invalid_log_level(self):
        config = {"display": {"log_level": "TRACE"}}
        errors = validate_config(config)
        assert any("must be one of" in e for e in errors)

    def test_valid_log_levels(self):
        for level in ["debug", "info", "warning", "error", "critical"]:
            config = {"display": {"log_level": level}}
            errors = validate_config(config)
            assert errors == [], f"Log level '{level}' should be valid"

    def test_invalid_env_type(self):
        config = {"terminal": {"env_type": "kubernetes"}}
        errors = validate_config(config)
        assert any("must be one of" in e for e in errors)

    def test_valid_env_types(self):
        for env in ["local", "docker", "ssh", "modal", "daytona", "singularity"]:
            config = {"terminal": {"env_type": env}}
            errors = validate_config(config)
            assert errors == [], f"Env type '{env}' should be valid"

    def test_section_not_dict(self):
        config = {"model": "not-a-dict"}
        errors = validate_config(config)
        assert any("expected a dict" in e for e in errors)

    def test_multiple_errors(self):
        config = {
            "model": {"default": 123, "provider": "invalid"},
            "agent": {"max_turns": -1},
        }
        errors = validate_config(config)
        assert len(errors) >= 3

    def test_unknown_fields_ignored(self):
        config = {"model": {"unknown_field": "value", "default": "openai/gpt-4"}}
        errors = validate_config(config)
        assert errors == []

    def test_valid_full_config(self):
        config = {
            "model": {
                "default": "anthropic/claude-opus-4.6",
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            "display": {
                "compact": False,
                "verbose": True,
                "tool_progress": "all",
                "skin": "default",
                "log_level": "info",
            },
            "agent": {
                "max_turns": 90,
                "save_trajectories": True,
            },
            "terminal": {
                "env_type": "local",
                "timeout": 300,
            },
        }
        errors = validate_config(config)
        assert errors == []


class TestValidateConfigStrict:
    def test_valid_config_returns_true(self):
        valid, errors = validate_config_strict({"model": {"default": "openai/gpt-4"}})
        assert valid is True
        assert errors == []

    def test_invalid_config_returns_false(self):
        valid, errors = validate_config_strict({"model": {"default": 123}})
        assert valid is False
        assert len(errors) > 0


class TestValidationError:
    def test_str_without_value(self):
        err = ValidationError(path="model.default", message="must be a string")
        assert str(err) == "model.default: must be a string"

    def test_str_with_value(self):
        err = ValidationError(
            path="model.default", message="expected type str", value=123
        )
        assert "model.default: expected type str" in str(err)
        assert "123" in str(err)


class TestConfigSchema:
    def test_schema_has_required_sections(self):
        assert "model" in CONFIG_SCHEMA
        assert "display" in CONFIG_SCHEMA
        assert "agent" in CONFIG_SCHEMA
        assert "terminal" in CONFIG_SCHEMA

    def test_model_section_has_default_field(self):
        assert "default" in CONFIG_SCHEMA["model"]

    def test_agent_section_has_max_turns(self):
        assert "max_turns" in CONFIG_SCHEMA["agent"]


class TestConfigMigration:
    def test_current_version(self):
        assert CURRENT_CONFIG_VERSION >= 6

    def test_get_config_version_default(self):
        assert get_config_version({}) == 1

    def test_get_config_version_from_config(self):
        assert get_config_version({"_config_version": 3}) == 3

    def test_needs_migration_old_version(self):
        assert needs_migration({"_config_version": 1}) is True

    def test_needs_migration_current_version(self):
        assert needs_migration({"_config_version": CURRENT_CONFIG_VERSION}) is False

    def test_migrate_v1_to_v2_adds_display(self):
        config = {}
        result = migrate_config(config, from_version=1)
        assert "display" in result

    def test_migrate_v2_to_v3_renames_max_iterations(self):
        config = {"max_iterations": 50}
        result = migrate_config(config, from_version=2)
        assert "max_iterations" not in result
        assert result.get("agent", {}).get("max_turns") == 50

    def test_migrate_v3_to_v4_adds_terminal(self):
        config = {}
        result = migrate_config(config, from_version=3)
        assert "terminal" in result
        assert result["terminal"]["env_type"] == "local"

    def test_migrate_v4_to_v5_moves_root_keys(self):
        config = {"verbose": True, "quiet_mode": False}
        result = migrate_config(config, from_version=4)
        assert "verbose" not in result
        assert "quiet_mode" not in result
        assert result.get("agent", {}).get("verbose") is True

    def test_migrate_v5_to_v6_adds_auxiliary(self):
        config = {}
        result = migrate_config(config, from_version=5)
        assert "auxiliary" in result

    def test_full_migration_chain(self):
        config = {"max_iterations": 42, "verbose": True}
        result = migrate_config(config, from_version=1)
        assert "display" in result
        assert "terminal" in result
        assert "auxiliary" in result
        assert result.get("agent", {}).get("max_turns") == 42
        assert result.get("agent", {}).get("verbose") is True

    def test_migrations_registered(self):
        assert len(_MIGRATIONS) >= 5

    def test_no_op_for_current_version(self):
        config = {"model": {"default": "openai/gpt-4"}}
        result = migrate_config(config, from_version=CURRENT_CONFIG_VERSION)
        assert result == config
