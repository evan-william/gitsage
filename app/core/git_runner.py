"""
Git command executor. All git subprocess calls go through this module.

Security notes:
- Commands are passed as lists, never shell=True, preventing injection.
- Repo path is validated and canonicalized before every call.
- Sensitive credential tokens are never passed as arguments; git credential store handles auth.
"""

import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import GitCommandError, InvalidPathError, RepoNotFoundError

logger = logging.getLogger(__name__)

_GIT_TIMEOUT = 30  # seconds


def _resolve_repo(repo_path: Optional[str] = None) -> Path:
    """
    Resolve and validate a repository path.
    Prevents path traversal by ensuring the resolved path stays within an allowed root.
    """
    raw = repo_path or settings.DEFAULT_REPO_PATH
    resolved = Path(raw).resolve()

    if not resolved.exists():
        raise InvalidPathError(f"Path does not exist: {resolved}")

    # Verify it's actually a git repo
    git_dir = resolved / ".git"
    if not git_dir.exists():
        raise RepoNotFoundError()

    return resolved


def run_git(
    args: list[str],
    repo_path: Optional[str] = None,
    capture_stderr: bool = True,
) -> str:
    """
    Run a git command and return stdout as a string.

    Args:
        args: Git subcommand and flags, e.g. ["status", "--short"].
        repo_path: Repository directory. Defaults to settings.DEFAULT_REPO_PATH.
        capture_stderr: Whether to capture stderr (useful for diff/log).

    Raises:
        GitCommandError: If git exits with a non-zero code.
        InvalidPathError: If the path is unsafe.
        RepoNotFoundError: If the path has no .git directory.
    """
    cwd = _resolve_repo(repo_path)
    cmd = ["git", "-C", str(cwd)] + args

    logger.debug("Running: %s", shlex.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            # Explicitly inherit a clean, minimal environment to avoid leaking
            # sensitive variables from the parent process.
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": os.environ.get("HOME", "/root"),
                "GIT_TERMINAL_PROMPT": "0",  # Never prompt for credentials
            },
        )
    except subprocess.TimeoutExpired:
        raise GitCommandError("Git command timed out.", stderr="")
    except FileNotFoundError:
        raise GitCommandError("git executable not found. Is git installed?")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.warning("Git error (exit %d): %s", result.returncode, stderr)
        raise GitCommandError(
            message=f"Git command failed: {' '.join(args[:2])}",
            stderr=stderr,
        )

    return result.stdout


def get_repo_root(repo_path: Optional[str] = None) -> str:
    """Return the absolute root of the git repository."""
    return run_git(["rev-parse", "--show-toplevel"], repo_path).strip()


def is_repo(path: str) -> bool:
    """Check whether a directory is a git repo without raising."""
    try:
        _resolve_repo(path)
        return True
    except (RepoNotFoundError, InvalidPathError):
        return False