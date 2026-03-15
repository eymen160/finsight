"""
FinSight — Application Settings
================================
Supports two secret sources (checked in order):
  1. Streamlit Cloud  → st.secrets["ANTHROPIC_API_KEY"]
  2. Local dev        → .env file / environment variables

Import `settings` anywhere in the codebase; never hardcode values.

Usage:
    from config.settings import settings
    client = anthropic.Anthropic(api_key=settings.api_key)
"""

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


def _resolve_api_key() -> str:
    """
    Return the Anthropic API key from whichever source is available.

    Priority:
      1. st.secrets  (Streamlit Cloud deployment)
      2. ANTHROPIC_API_KEY env var / .env file
    """
    # Try Streamlit secrets first (won't import-error if streamlit absent)
    try:
        import streamlit as st  # noqa: PLC0415
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:  # noqa: BLE001
        pass

    # Fall back to env var (set by .env or host environment)
    return os.getenv("ANTHROPIC_API_KEY", "")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ─────────────────────────────────────────────
    # Default="" so Pydantic won't error on import; _resolve_api_key
    # handles the real validation at runtime via the `api_key` property.
    anthropic_api_key: SecretStr = Field(default="", description="Anthropic API key")
    claude_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model identifier",
    )
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    # ── App ───────────────────────────────────────────────────
    app_env: Environment = Field(default=Environment.DEVELOPMENT)
    log_level: str = Field(default="INFO")
    app_title: str = "FinSight"
    app_version: str = "0.1.0"

    # ── RAG ───────────────────────────────────────────────────
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=150, ge=0, le=500)
    top_k_results: int = Field(default=5, ge=1, le=20)
    faiss_index_path: str = Field(
        default="/tmp/finsight_faiss",  # /tmp is writable on Streamlit Cloud
        description="Directory where FAISS index is persisted",
    )

    # ── Cache ─────────────────────────────────────────────────
    cache_ttl_seconds: int = Field(default=300, ge=60)

    # ── Derived helpers ───────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def api_key(self) -> str:
        """
        Return the live API key, checking st.secrets before env vars.
        Raises RuntimeError if neither source has a value.
        """
        key = _resolve_api_key() or self.anthropic_api_key.get_secret_value()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to Streamlit Cloud secrets or your .env file."
            )
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — call this everywhere."""
    return Settings()


# Module-level singleton for convenience
settings = get_settings()
