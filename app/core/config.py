"""
Configuration management. All settings come from environment variables or a .env file.
Sensitive values (API keys) are never logged or exposed via the API.
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    PORT: int = 8000
    DEBUG: bool = False

    # AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_REQUEST_TIMEOUT: int = 30
 
    # Git
    DEFAULT_REPO_PATH: str = "."
    MAX_DIFF_BYTES: int = 50_000  # Limit diff sent to AI to prevent token abuse

    @field_validator("DEFAULT_REPO_PATH")
    @classmethod
    def validate_repo_path(cls, v: str) -> str:
        path = Path(v).resolve()
        if not path.exists():
            raise ValueError(f"Repo path does not exist: {path}")
        return str(path)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()