"""
Application-level exceptions with HTTP status codes.
"""


class GitSageError(Exception):
    """Base exception for all GitSage errors."""

    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


class GitCommandError(GitSageError):
    """A git command failed."""

    status_code = 400

    def __init__(self, message: str, stderr: str = ""):
        self.stderr = stderr
        super().__init__(message)


class RepoNotFoundError(GitSageError):
    """Path is not a git repository."""

    status_code = 404
    message = "Not a valid git repository."


class AIServiceError(GitSageError):
    """AI service call failed."""

    status_code = 503
    message = "AI service unavailable. Check your GEMINI_API_KEY."


class AINotConfiguredError(GitSageError):
    """Gemini API key not set."""

    status_code = 503
    message = "Gemini API key not configured. Add GEMINI_API_KEY to your .env file."


class InvalidPathError(GitSageError):
    """Path traversal or invalid path detected."""

    status_code = 400
    message = "Invalid repository path."