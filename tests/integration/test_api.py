"""
Integration tests for the FastAPI endpoints.
These tests require git to be installed on the host system.
"""

import subprocess
from pathlib import Path

import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, app_client):
        res = app_client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestStatusEndpoint:
    def test_get_status(self, app_client):
        res = app_client.get("/api/status")
        assert res.status_code == 200
        data = res.json()
        assert "branch" in data
        assert "staged" in data
        assert "unstaged" in data
        assert "untracked" in data

    def test_stage_all(self, app_client, tmp_git_repo):
        # Create a new file to stage
        (tmp_git_repo / "newfile.txt").write_text("hello")
        res = app_client.post("/api/status/stage-all", json={})
        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_stage_nonexistent_file_errors(self, app_client):
        res = app_client.post("/api/status/stage", json={"file_path": "does_not_exist.xyz"})
        assert res.status_code == 400

    def test_stage_path_traversal_blocked(self, app_client):
        res = app_client.post("/api/status/stage", json={"file_path": "../etc/passwd"})
        assert res.status_code == 422  # Pydantic validation rejects it

    def test_staged_diff(self, app_client):
        res = app_client.get("/api/status/diff")
        assert res.status_code == 200
        assert "diff" in res.json()


class TestCommitsEndpoint:
    def test_get_log(self, app_client):
        res = app_client.get("/api/commits/log")
        assert res.status_code == 200
        commits = res.json()
        assert isinstance(commits, list)
        assert len(commits) >= 1
        assert "sha" in commits[0]
        assert "message" in commits[0]

    def test_commit_empty_message_rejected(self, app_client):
        res = app_client.post("/api/commits", json={"message": "   "})
        assert res.status_code == 422

    def test_commit_too_long_rejected(self, app_client):
        res = app_client.post("/api/commits", json={"message": "x" * 5000})
        assert res.status_code == 422

    def test_log_limit_clamped(self, app_client):
        # limit > 200 should be rejected by query param validation
        res = app_client.get("/api/commits/log?limit=999")
        assert res.status_code == 422


class TestBranchesEndpoint:
    def test_list_branches(self, app_client):
        res = app_client.get("/api/branches")
        assert res.status_code == 200
        branches = res.json()
        assert any(b["is_current"] for b in branches)

    def test_create_invalid_branch_name(self, app_client):
        res = app_client.post("/api/branches", json={"name": "bad..name"})
        assert res.status_code == 422

    def test_create_branch_starting_with_dash_rejected(self, app_client):
        res = app_client.post("/api/branches", json={"name": "-d"})
        assert res.status_code == 422


class TestAiEndpointNoKey:
    """When GEMINI_API_KEY is not set, AI endpoints return 503."""

    def test_commit_message_no_key(self, app_client, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        from app.core import config
        config.get_settings.cache_clear()

        res = app_client.post("/api/ai/commit-message", json={})
        # Either 503 (no key) or 200 if there are no staged changes (ValueError -> 400)
        assert res.status_code in (400, 503)

        config.get_settings.cache_clear()

    def test_diagnose_empty_error_rejected(self, app_client):
        res = app_client.post("/api/ai/diagnose", json={"error_output": "   "})
        assert res.status_code == 422


class TestRemotesEndpoint:
    def test_list_remotes_empty(self, app_client):
        # Fresh test repo has no remotes
        res = app_client.get("/api/remotes")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_invalid_remote_name_rejected(self, app_client):
        res = app_client.post("/api/remotes/fetch", json={"remote": "-origin"})
        assert res.status_code == 422


class TestSecurityHeaders:
    def test_cors_restricted(self, app_client):
        # Request from an untrusted origin should not get CORS headers
        res = app_client.get("/health", headers={"Origin": "https://evil.com"})
        assert "access-control-allow-origin" not in res.headers or \
               res.headers.get("access-control-allow-origin") != "https://evil.com"