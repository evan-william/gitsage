"""
Service layer for remote operations (fetch, pull, push).
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.core.git_runner import run_git

logger = logging.getLogger(__name__)


@dataclass
class Remote:
    name: str
    fetch_url: str
    push_url: str


def list_remotes(repo_path: Optional[str] = None) -> list[Remote]:
    """Return configured remotes."""
    raw = run_git(["remote", "-v"], repo_path)
    seen: dict[str, dict] = {}

    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, url, direction = parts[0], parts[1], parts[2].strip("()")
        if name not in seen:
            seen[name] = {"name": name, "fetch_url": "", "push_url": ""}
        if direction == "fetch":
            seen[name]["fetch_url"] = url
        elif direction == "push":
            seen[name]["push_url"] = url

    return [Remote(**v) for v in seen.values()]


def fetch(remote: str = "origin", repo_path: Optional[str] = None) -> str:
    """Fetch from a remote."""
    return run_git(["fetch", "--prune", remote], repo_path)


def pull(remote: str = "origin", branch: Optional[str] = None, repo_path: Optional[str] = None) -> str:
    """Pull from a remote branch."""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    return run_git(args, repo_path)


def push(remote: str = "origin", branch: Optional[str] = None, repo_path: Optional[str] = None) -> str:
    """Push to a remote branch."""
    args = ["push", remote]
    if branch:
        args.append(branch)
    return run_git(args, repo_path)