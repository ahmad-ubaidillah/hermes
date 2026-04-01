# hermes_cli/cli_fast.py - Fast CLI entry point (re-exports from cli.py)
#
# This module provides a clean import surface for the HermesCLI class and
# related helpers. All implementations live in the root-level cli.py; this
# file exists so tests and downstream code can import from a stable,
# package-scoped location.

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `cli` resolves to the root cli.py.
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cli import (
    HermesCLI,
    _rich_text_from_ansi,
    _setup_worktree,
    _cleanup_worktree,
    _parse_reasoning_config,
    load_cli_config,
    save_config_value,
    main,
)

__all__ = [
    "HermesCLI",
    "_rich_text_from_ansi",
    "_setup_worktree",
    "_cleanup_worktree",
    "_parse_reasoning_config",
    "load_cli_config",
    "save_config_value",
    "main",
]
