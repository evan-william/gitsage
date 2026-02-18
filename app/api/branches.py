"""API routes for branch management."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, field_validator

from app.services.branch_service import (
    Branch,
    checkout_branch,
    create_branch,
    delete_branch,
    get_branch_graph,
    list_branches,
    merge_branch,
)
from app.services.commit_service import _is_valid_ref_name

router = APIRouter()


def _validate_ref(name: str) -> str:
    if not _is_valid_ref_name(name):
        raise ValueError(f"Invalid branch name: {name!r}")
    return name


class BranchOut(BaseModel):
    name: str
    is_current: bool
    is_remote: bool
    last_commit_sha: str
    last_commit_message: str


class CreateBranchRequest(BaseModel):
    name: str
    checkout: bool = True
    repo_path: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_ref(v)


class BranchActionRequest(BaseModel):
    name: str
    repo_path: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_ref(v)


class DeleteBranchRequest(BaseModel):
    name: str
    force: bool = False
    repo_path: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return _validate_ref(v)


@router.get("", response_model=list[BranchOut])
async def branches(repo_path: Optional[str] = Query(None)):
    return [BranchOut(**b.__dict__) for b in list_branches(repo_path)]


@router.post("")
async def create(req: CreateBranchRequest):
    create_branch(req.name, req.checkout, req.repo_path)
    return {"ok": True}


@router.post("/checkout")
async def checkout(req: BranchActionRequest):
    checkout_branch(req.name, req.repo_path)
    return {"ok": True}


@router.delete("")
async def delete(req: DeleteBranchRequest):
    delete_branch(req.name, req.force, req.repo_path)
    return {"ok": True}


@router.post("/merge")
async def merge(req: BranchActionRequest):
    output = merge_branch(req.name, req.repo_path)
    return {"output": output}


@router.get("/graph")
async def graph(repo_path: Optional[str] = Query(None)):
    return get_branch_graph(repo_path)