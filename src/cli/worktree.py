"""Worktree/Git helpers for CLI."""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _git_repo_root() -> Optional[str]:
    """Find the Git repository root by traversing up from cwd."""
    cwd = Path.cwd()
    while cwd != cwd.parent:
        if (cwd / ".git").exists():
            return str(cwd)
        cwd = cwd.parent
    return None


def _path_is_within_root(path: Path, root: Path) -> bool:
    """Check if path is within root directory."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _setup_worktree(repo_root: str = None) -> Optional[dict[str, str]]:
    """Set up a temporary git worktree for safe operations."""
    if repo_root is None:
        repo_root = _git_repo_root()
    if repo_root is None:
        return None

    repo_path = Path(repo_root)
    worktree_base = repo_path / ".aizen_worktrees"
    worktree_base.mkdir(exist_ok=True)

    import uuid

    worktree_id = uuid.uuid4().hex[:8]
    worktree_path = worktree_base / f"worktree_{worktree_id}"

    try:
        os.symlink(repo_path, worktree_path, target_is_directory=True)
        return {
            "path": str(worktree_path),
            "original": str(repo_path),
            "id": worktree_id,
        }
    except Exception as e:
        logger.warning("Failed to create worktree: %s", e)
        return None


def _cleanup_worktree(info: dict[str, str] = None) -> None:
    """Clean up a temporary worktree."""
    if info is None:
        return
    try:
        path = Path(info["path"])
        if path.exists() and path.is_symlink():
            path.unlink()
    except Exception as e:
        logger.debug("Worktree cleanup failed: %s", e)


def _prune_stale_worktrees(repo_root: str, max_age_hours: int = 24) -> None:
    """Remove stale worktrees older than max_age_hours."""
    import time

    repo_path = Path(repo_root)
    worktree_base = repo_path / ".aizen_worktrees"

    if not worktree_base.exists():
        return

    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for item in worktree_base.iterdir():
        if item.is_symlink():
            try:
                mtime = item.stat().st_mtime
                if now - mtime > max_age_seconds:
                    item.unlink()
                    logger.debug("Removed stale worktree: %s", item.name)
            except Exception:
                pass
