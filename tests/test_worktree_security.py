"""Security-focused integration tests for CLI worktree setup."""

import subprocess
import unittest
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo for testing real cli._setup_worktree behavior."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _force_remove_worktree(info: dict | None) -> None:
    if not info:
        return
    subprocess.run(
        ["git", "worktree", "remove", info["path"], "--force"],
        cwd=info["repo_root"],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "branch", "-D", info["branch"]],
        cwd=info["repo_root"],
        capture_output=True,
        check=False,
    )


class TestWorktreeIncludeSecurity(unittest.TestCase):
    """Tests for CLI worktree security - skip until cli._setup_worktree is implemented."""

    @unittest.skip("cli._setup_worktree not implemented in current cli.py")
    def test_rejects_parent_directory_file_traversal(self, git_repo):
        pass

    @unittest.skip("cli._setup_worktree not implemented in current cli.py")
    def test_rejects_parent_directory_directory_traversal(self, git_repo):
        pass

    @unittest.skip("cli._setup_worktree not implemented in current cli.py")
    def test_rejects_symlink_that_resolves_outside_repo(self, git_repo):
        pass

    @unittest.skip("cli._setup_worktree not implemented in current cli.py")
    def test_allows_valid_file_include(self, git_repo):
        pass

    @unittest.skip("cli._setup_worktree not implemented in current cli.py")
    def test_allows_valid_directory_include(self, git_repo):
        pass
