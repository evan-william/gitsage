"""API routes for repository status and staging."""

from typing import Annotated, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, field_validator

from app.services.status_service import (
    FileStatus,
    RepoStatus,
    get_staged_diff,
    get_status,
    stage_all,
    stage_file,
    unstage_file,
)

router = APIRouter()


class FileActionRequest(BaseModel):
    file_path: str
    repo_path: Optional[str] = None

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.startswith("-") or "\x00" in v or ".." in v:
            raise ValueError("Invalid file path.")
        return v


class FileStatusOut(BaseModel):
    path: str
    index_status: str
    work_status: str
    is_staged: bool
    is_unstaged: bool


class RepoStatusOut(BaseModel):
    branch: str
    ahead: int
    behind: int
    staged: list[FileStatusOut]
    unstaged: list[FileStatusOut]
    untracked: list[FileStatusOut]


def _file_out(f: FileStatus) -> FileStatusOut:
    return FileStatusOut(
        path=f.path,
        index_status=f.index_status,
        work_status=f.work_status,
        is_staged=f.is_staged,
        is_unstaged=f.is_unstaged,
    )


@router.get("", response_model=RepoStatusOut)
async def repo_status(repo_path: Optional[str] = Query(None)):
    status = get_status(repo_path)
    return RepoStatusOut(
        branch=status.branch,
        ahead=status.ahead,
        behind=status.behind,
        staged=[_file_out(f) for f in status.staged],
        unstaged=[_file_out(f) for f in status.unstaged],
        untracked=[_file_out(f) for f in status.untracked],
    )


@router.post("/stage")
async def stage(req: FileActionRequest):
    stage_file(req.file_path, req.repo_path)
    return {"ok": True}


@router.post("/unstage")
async def unstage(req: FileActionRequest):
    unstage_file(req.file_path, req.repo_path)
    return {"ok": True}


@router.post("/stage-all")
async def stage_all_files(repo_path: Optional[str] = Body(None, embed=True)):
    stage_all(repo_path)
    return {"ok": True}


@router.get("/diff")
async def staged_diff(repo_path: Optional[str] = Query(None)):
    diff = get_staged_diff(repo_path)
    return {"diff": diff}