"""
Unit tests for git runner, commit service validation, and AI service utilities.
"""

import pytest

from app.core.exceptions import InvalidPathError, RepoNotFoundError
from app.services.commit_service import _is_valid_ref_name, _sanitize_commit_message
from app.services.ai_service import _is_safe_auto_fix


class TestRefNameValidation:
    def test_simple_name_valid(self):
        assert _is_valid_ref_name("main") is True

    def test_feature_branch_valid(self):
        assert _is_valid_ref_name("feature/my-feature") is True

    def test_empty_invalid(self):
        assert _is_valid_ref_name("") is False

    def test_starts_with_dash_invalid(self):
        assert _is_valid_ref_name("-d") is False

    def test_double_dot_invalid(self):
        assert _is_valid_ref_name("branch..name") is False

    def test_space_invalid(self):
        assert _is_valid_ref_name("branch name") is False

    def test_null_byte_invalid(self):
        assert _is_valid_ref_name("branch\x00name") is False

    def test_tilde_invalid(self):
        assert _is_valid_ref_name("branch~1") is False

    def test_very_long_name_invalid(self):
        assert _is_valid_ref_name("a" * 251) is False


class TestCommitMessageSanitization:
    def test_strips_null_bytes(self):
        result = _sanitize_commit_message("fix: bug\x00 fix")
        assert "\x00" not in result

    def test_strips_control_chars(self):
        result = _sanitize_commit_message("fix\x01\x02: bug")
        assert "\x01" not in result
        assert "\x02" not in result

    def test_preserves_newlines(self):
        msg = "feat: add feature\n\nLonger description."
        result = _sanitize_commit_message(msg)
        assert "\n" in result

    def test_strips_leading_trailing_whitespace(self):
        result = _sanitize_commit_message("  fix: bug  ")
        assert result == "fix: bug"

    def test_normal_message_unchanged(self):
        msg = "feat(api): add endpoint for status"
        assert _sanitize_commit_message(msg) == msg


class TestAutoFixWhitelist:
    def test_git_fetch_allowed(self):
        assert _is_safe_auto_fix("git fetch") is True

    def test_git_fetch_with_remote(self):
        assert _is_safe_auto_fix("git fetch origin") is True

    def test_git_merge_abort_allowed(self):
        assert _is_safe_auto_fix("git merge --abort") is True

    def test_git_rebase_abort_allowed(self):
        assert _is_safe_auto_fix("git rebase --abort") is True

    def test_git_stash_allowed(self):
        assert _is_safe_auto_fix("git stash") is True

    def test_git_stash_pop_allowed(self):
        assert _is_safe_auto_fix("git stash pop") is True

    def test_dangerous_force_push_blocked(self):
        assert _is_safe_auto_fix("git push origin --force") is False

    def test_rm_rf_blocked(self):
        assert _is_safe_auto_fix("rm -rf /") is False

    def test_git_reset_hard_blocked(self):
        assert _is_safe_auto_fix("git reset --hard HEAD~5") is False

    def test_chained_commands_blocked(self):
        assert _is_safe_auto_fix("git fetch && rm -rf /") is False

    def test_empty_string_blocked(self):
        assert _is_safe_auto_fix("") is False