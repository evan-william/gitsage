"""API routes for AI features."""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.services.ai_service import diagnose_error, generate_commit_message
from app.services.status_service import get_staged_diff

router = APIRouter()


class GenerateMessageRequest(BaseModel):
    repo_path: Optional[str] = None


class DiagnoseRequest(BaseModel):
    error_output: str
    context: Optional[str] = None
    repo_path: Optional[str] = None

    @field_validator("error_output")
    @classmethod
    def validate_error(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Error output cannot be empty.")
        return v[:3000]


@router.post("/commit-message")
async def ai_commit_message(req: GenerateMessageRequest):
    """Generate a commit message from the current staged diff."""
    try:
        diff = get_staged_diff(req.repo_path)
        message = await generate_commit_message(diff)
        return {"message": message}
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


@router.post("/diagnose")
async def ai_diagnose(req: DiagnoseRequest):
    """Diagnose a git error and suggest fixes."""
    try:
        result = await diagnose_error(req.error_output, req.context)
        return result
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})