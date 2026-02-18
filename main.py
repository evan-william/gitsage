"""
GitSage - Local Git management with AI-powered features.
Entry point for the FastAPI application.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import commits, branches, status, ai, remotes
from app.core.config import settings
from app.core.exceptions import GitSageError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GitSage starting up...")
    yield
    logger.info("GitSage shutting down.")


app = FastAPI(
    title="GitSage",
    description="Local Git management with AI-powered commit messages and error diagnosis.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# Security: Only allow localhost access since this is a self-hosted tool
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "::1"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Requested-With"],
)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

templates = Jinja2Templates(directory="frontend/templates")

# Register routers
app.include_router(commits.router, prefix="/api/commits", tags=["commits"])
app.include_router(branches.router, prefix="/api/branches", tags=["branches"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(remotes.router, prefix="/api/remotes", tags=["remotes"])


@app.exception_handler(GitSageError)
async def gitsage_exception_handler(request: Request, exc: GitSageError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )