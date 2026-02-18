"""API routes for commits."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, field_validator

from app.services.commit_service import Commit, create_commit, get_log

router = APIRouter()


class CommitRequest(BaseModel):
    message: str
    repo_path: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Commit message cannot be empty.")
        if len(stripped) > 4096:
            raise ValueError("Commit message too long.")
        return stripped


class CommitOut(BaseModel):
    sha: str
    short_sha: str
    author: str
    email: str
    date: str
    message: str


@router.post("")
async def commit(req: CommitRequest):
    sha = create_commit(req.message, req.repo_path)
    return {"sha": sha}


@router.get("/log", response_model=list[CommitOut])
async def log(
    limit: int = Query(30, ge=1, le=200),
    branch: Optional[str] = Query(None),
    repo_path: Optional[str] = Query(None),
):
    commits = get_log(limit=limit, branch=branch, repo_path=repo_path)
    return [CommitOut(**c.__dict__) for c in commits]