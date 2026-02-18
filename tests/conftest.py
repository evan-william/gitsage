"""
Shared pytest fixtures.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture(scope="session")
def tmp_git_repo() -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@gitsage.local"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "GitSage Test"],
            cwd=repo, check=True, capture_output=True,
        )
        # Create an initial commit so HEAD is valid
        (repo / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: initial commit"],
            cwd=repo, check=True, capture_output=True,
        )
        yield repo


@pytest.fixture
def app_client(tmp_git_repo, monkeypatch):
    """FastAPI test client with the temp repo as default path."""
    monkeypatch.setenv("DEFAULT_REPO_PATH", str(tmp_git_repo))
    monkeypatch.setenv("DEBUG", "true")

    # Reload settings cache so the new env var is picked up
    from app.core import config
    config.get_settings.cache_clear()

    from main import app
    with TestClient(app) as client:
        yield client

    config.get_settings.cache_clear()