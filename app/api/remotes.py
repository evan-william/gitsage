"""API routes for remote operations."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, field_validator

from app.services.remote_service import fetch, list_remotes, pull, push

router = APIRouter()


class RemoteActionRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None
    repo_path: Optional[str] = None

    @field_validator("remote")
    @classmethod
    def validate_remote(cls, v: str) -> str:
        if not v or v.startswith("-") or " " in v:
            raise ValueError("Invalid remote name.")
        return v


@router.get("")
async def remotes(repo_path: Optional[str] = Query(None)):
    return [r.__dict__ for r in list_remotes(repo_path)]


@router.post("/fetch")
async def do_fetch(req: RemoteActionRequest):
    output = fetch(req.remote, req.repo_path)
    return {"output": output}


@router.post("/pull")
async def do_pull(req: RemoteActionRequest):
    output = pull(req.remote, req.branch, req.repo_path)
    return {"output": output}


@router.post("/push")
async def do_push(req: RemoteActionRequest):
    output = push(req.remote, req.branch, req.repo_path)
    return {"output": output}