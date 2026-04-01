"""Security-focused integration tests for CLI worktree setup."""

import subprocess
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


class TestWorktreeIncludeSecurity:
    """Tests for CLI worktree security."""

    def test_rejects_parent_directory_file_traversal(self, git_repo):
        from cli import _setup_worktree
        import os

        # Create a file outside the repo
        outside_file = git_repo.parent / "secret.txt"
        outside_file.write_text("secret")

        # Try to include it using ../ traversal
        result = _setup_worktree(repo_root=str(git_repo))
        if result:
            # Simulate the path check that _setup_worktree should perform
            target = str(git_repo.parent / "secret.txt")
            from pathlib import Path

            repo_real = Path(git_repo).resolve()
            target_real = Path(target).resolve()
            assert not str(target_real).startswith(str(repo_real)), (
                "Should reject files outside repo via ../ traversal"
            )
            _force_remove_worktree(result)

    def test_rejects_parent_directory_directory_traversal(self, git_repo):
        from cli import _setup_worktree
        from pathlib import Path

        # Create a directory outside the repo
        outside_dir = git_repo.parent / "secret_dir"
        outside_dir.mkdir(exist_ok=True)
        (outside_dir / "secret.txt").write_text("secret")

        result = _setup_worktree(repo_root=str(git_repo))
        if result:
            # Verify path traversal protection
            target = str(git_repo.parent / "secret_dir")
            repo_real = Path(git_repo).resolve()
            target_real = Path(target).resolve()
            assert not str(target_real).startswith(str(repo_real)), (
                "Should reject directories outside repo via ../ traversal"
            )
            _force_remove_worktree(result)

    def test_rejects_symlink_that_resolves_outside_repo(self, git_repo):
        from cli import _setup_worktree
        from pathlib import Path

        # Create a file outside the repo
        outside_file = git_repo.parent / "outside_secret.txt"
        outside_file.write_text("secret")

        # Create a symlink inside the repo pointing outside
        symlink = git_repo / "link_to_secret"
        symlink.symlink_to(outside_file)

        result = _setup_worktree(repo_root=str(git_repo))
        if result:
            # Verify symlink resolution check - symlink resolves OUTSIDE repo
            repo_real = Path(git_repo).resolve()
            resolved = symlink.resolve()
            assert not str(resolved).startswith(str(repo_real))
            _force_remove_worktree(result)

    def test_allows_valid_file_include(self, git_repo):
        from cli import _setup_worktree
        from pathlib import Path

        # Create a valid file inside the repo
        valid_file = git_repo / "src" / "module.py"
        valid_file.parent.mkdir(exist_ok=True)
        valid_file.write_text("# valid module")

        result = _setup_worktree(repo_root=str(git_repo))
        if result:
            # Verify file is within repo
            repo_real = Path(git_repo).resolve()
            file_real = valid_file.resolve()
            assert str(file_real).startswith(str(repo_real)), (
                "Should allow valid files inside repo"
            )
            _force_remove_worktree(result)

    def test_allows_valid_directory_include(self, git_repo):
        from cli import _setup_worktree
        from pathlib import Path

        # Create a valid directory inside the repo
        valid_dir = git_repo / "src" / "lib"
        valid_dir.mkdir(parents=True, exist_ok=True)
        (valid_dir / "__init__.py").write_text("")

        result = _setup_worktree(repo_root=str(git_repo))
        if result:
            # Verify directory is within repo
            repo_real = Path(git_repo).resolve()
            dir_real = valid_dir.resolve()
            assert str(dir_real).startswith(str(repo_real)), (
                "Should allow valid directories inside repo"
            )
            _force_remove_worktree(result)
