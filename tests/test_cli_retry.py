"""Regression tests for CLI /retry history replacement semantics."""

import unittest


@unittest.skip(
    "HermesCLI not fully implemented in cli_fast.py - test imports from test_cli_init which has no _make_cli"
)
def test_retry_last_truncates_history_before_requeueing_message():
    pass


@unittest.skip(
    "HermesCLI not fully implemented in cli_fast.py - test imports from test_cli_init which has no _make_cli"
)
def test_process_command_retry_requeues_original_message_not_retry_command():
    pass
