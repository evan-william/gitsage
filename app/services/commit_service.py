"""
Service layer for git commit operations and commit log.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.git_runner import run_git

logger = logging.getLogger(__name__)

_SAFE_MESSAGE_PATTERN = re.compile(r"^[\w\s\(\):\-/\.,!#\[\]'\"@&+=<>_]+$", re.UNICODE)


@dataclass
class Commit:
    sha: str
    short_sha: str
    author: str
    email: str
    date: str
    message: str


def _sanitize_commit_message(message: str) -> str:
    """
    Strip control characters from commit messages.
    This is a defence-in-depth measure; the AI output should already be clean.
    """
    # Remove null bytes and control characters except newline/tab
    cleaned = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", message)
    return cleaned.strip()


def create_commit(message: str, repo_path: Optional[str] = None) -> str:
    """
    Create a commit with the given message.
    Returns the short SHA of the new commit.
    """
    clean_message = _sanitize_commit_message(message)
    if not clean_message:
        raise ValueError("Commit message cannot be empty.")
    if len(clean_message) > 4096:
        raise ValueError("Commit message exceeds maximum length of 4096 characters.")

    # Pass message via -m; git receives it as a single argument, no shell expansion
    run_git(["commit", "-m", clean_message], repo_path)

    sha = run_git(["rev-parse", "--short", "HEAD"], repo_path).strip()
    return sha


def get_log(
    limit: int = 30,
    branch: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> list[Commit]:
    """Retrieve the commit log."""
    limit = min(max(1, limit), 200)  # Clamp to sane range

    sep = "\x1f"  # Unit separator — unlikely to appear in git data
    fmt = sep.join(["%H", "%h", "%an", "%ae", "%ci", "%s"])

    args = ["log", f"--format={fmt}", f"-{limit}"]
    if branch:
        # Validate branch name before using it as an argument
        if not _is_valid_ref_name(branch):
            raise ValueError(f"Invalid branch name: {branch!r}")
        args.append(branch)

    raw = run_git(args, repo_path)
    commits = []
    for line in raw.splitlines():
        parts = line.split(sep)
        if len(parts) != 6:
            continue
        commits.append(
            Commit(
                sha=parts[0],
                short_sha=parts[1],
                author=parts[2],
                email=parts[3],
                date=parts[4],
                message=parts[5],
            )
        )
    return commits


def _is_valid_ref_name(name: str) -> bool:
    """Rough check that a branch/ref name is safe to pass to git."""
    if not name or len(name) > 250:
        return False
    forbidden = [" ", "\t", "\n", "\x00", "\\", "..", "~", "^", ":", "?", "*", "["]
    return not any(c in name for c in forbidden) and not name.startswith("-")