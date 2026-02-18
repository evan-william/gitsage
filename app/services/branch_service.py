"""
Service layer for branch operations.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.git_runner import run_git
from app.services.commit_service import _is_valid_ref_name

logger = logging.getLogger(__name__)


@dataclass
class Branch:
    name: str
    is_current: bool
    is_remote: bool
    last_commit_sha: str
    last_commit_message: str


def list_branches(repo_path: Optional[str] = None) -> list[Branch]:
    """Return all local branches with their last commit info."""
    sep = "\x1f"
    fmt = sep.join(["%(refname:short)", "%(HEAD)", "%(objectname:short)", "%(subject)"])

    raw = run_git(["for-each-ref", f"--format={fmt}", "refs/heads/"], repo_path)
    branches = []
    for line in raw.splitlines():
        parts = line.split(sep)
        if len(parts) != 4:
            continue
        branches.append(
            Branch(
                name=parts[0],
                is_current=parts[1] == "*",
                is_remote=False,
                last_commit_sha=parts[2],
                last_commit_message=parts[3],
            )
        )
    return branches


def create_branch(name: str, checkout: bool = True, repo_path: Optional[str] = None) -> None:
    """Create (and optionally check out) a new branch."""
    if not _is_valid_ref_name(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    if checkout:
        run_git(["checkout", "-b", name], repo_path)
    else:
        run_git(["branch", name], repo_path)


def checkout_branch(name: str, repo_path: Optional[str] = None) -> None:
    """Switch to an existing branch."""
    if not _is_valid_ref_name(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    run_git(["checkout", name], repo_path)


def delete_branch(name: str, force: bool = False, repo_path: Optional[str] = None) -> None:
    """Delete a local branch."""
    if not _is_valid_ref_name(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    flag = "-D" if force else "-d"
    run_git(["branch", flag, name], repo_path)


def merge_branch(source: str, repo_path: Optional[str] = None) -> str:
    """Merge source branch into the current branch. Returns git output."""
    if not _is_valid_ref_name(source):
        raise ValueError(f"Invalid branch name: {source!r}")
    return run_git(["merge", "--no-ff", source], repo_path)


def get_branch_graph(repo_path: Optional[str] = None) -> list[dict]:
    """
    Return a simplified commit graph suitable for UI rendering.
    Each entry has sha, message, author, date, and refs.
    """
    sep = "\x1f"
    fmt = sep.join(["%h", "%s", "%an", "%ci", "%D"])
    raw = run_git(
        ["log", "--all", "--decorate=short", f"--format={fmt}", "--max-count=100"],
        repo_path,
    )
    graph = []
    for line in raw.splitlines():
        parts = line.split(sep)
        if len(parts) != 5:
            continue
        refs = [r.strip() for r in parts[4].split(",") if r.strip()]
        graph.append(
            {
                "sha": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
                "refs": refs,
            }
        )
    return graph