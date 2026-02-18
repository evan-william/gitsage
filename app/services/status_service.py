"""
Service layer for git status and staging operations.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.core.git_runner import run_git
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FileStatus:
    path: str
    index_status: str   # X in XY format (staged)
    work_status: str    # Y in XY format (unstaged)

    @property
    def is_staged(self) -> bool:
        return self.index_status not in ("?", " ", "!")

    @property
    def is_unstaged(self) -> bool:
        return self.work_status not in (" ", "!")


@dataclass
class RepoStatus:
    branch: str
    ahead: int
    behind: int
    staged: list[FileStatus]
    unstaged: list[FileStatus]
    untracked: list[FileStatus]


def _parse_porcelain(output: str) -> list[FileStatus]:
    files = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        x = line[0]
        y = line[1]
        # Path starts at index 3; handle renames (-> separator)
        path_part = line[3:]
        path = path_part.split(" -> ")[-1]
        files.append(FileStatus(path=path, index_status=x, work_status=y))
    return files


def get_status(repo_path: Optional[str] = None) -> RepoStatus:
    """Return a structured representation of the current working tree status."""
    raw = run_git(["status", "--porcelain=v1", "--branch"], repo_path)
    lines = raw.splitlines()

    branch = "unknown"
    ahead = behind = 0

    if lines and lines[0].startswith("## "):
        header = lines[0][3:]
        # Format: "main...origin/main [ahead N, behind M]"
        parts = header.split("...")
        branch = parts[0]
        if "[" in header:
            info = header[header.index("[") + 1 : header.index("]")]
            for segment in info.split(","):
                segment = segment.strip()
                if segment.startswith("ahead"):
                    ahead = int(segment.split()[-1])
                elif segment.startswith("behind"):
                    behind = int(segment.split()[-1])

    all_files = _parse_porcelain("\n".join(lines[1:]))

    staged = [f for f in all_files if f.is_staged and f.index_status not in ("?", "!")]
    unstaged = [f for f in all_files if f.is_unstaged and f.index_status != "?"]
    untracked = [f for f in all_files if f.index_status == "?" and f.work_status == "?"]

    return RepoStatus(
        branch=branch,
        ahead=ahead,
        behind=behind,
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
    )


def stage_file(file_path: str, repo_path: Optional[str] = None) -> None:
    """Stage a single file. file_path is relative to the repo root."""
    # Basic validation: reject paths that look like flags or contain null bytes
    if file_path.startswith("-") or "\x00" in file_path:
        raise ValueError(f"Invalid file path: {file_path!r}")
    run_git(["add", "--", file_path], repo_path)


def unstage_file(file_path: str, repo_path: Optional[str] = None) -> None:
    """Unstage a single file."""
    if file_path.startswith("-") or "\x00" in file_path:
        raise ValueError(f"Invalid file path: {file_path!r}")
    run_git(["restore", "--staged", "--", file_path], repo_path)


def stage_all(repo_path: Optional[str] = None) -> None:
    """Stage all changes."""
    run_git(["add", "-A"], repo_path)


def get_staged_diff(repo_path: Optional[str] = None) -> str:
    """Return the diff of staged changes, capped at MAX_DIFF_BYTES."""
    diff = run_git(["diff", "--cached"], repo_path)
    max_bytes = settings.MAX_DIFF_BYTES
    if len(diff) > max_bytes:
        diff = diff[:max_bytes] + "\n\n[diff truncated — too large]"
    return diff