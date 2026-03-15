"""
FinSight — Application Settings
===================================
Single source of truth for runtime configuration.

Secret resolution (first non-empty wins):
  1. ``st.secrets["ANTHROPIC_API_KEY"]``  → Streamlit Cloud
  2. ``ANTHROPIC_API_KEY`` env var / .env  → local dev

Usage::

    from config.settings import settings
    key = settings.api_key          # raises RuntimeError if missing
    model = settings.claude_model
"""
from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION  = "production"


def _resolve_anthropic_key() -> str:
    """Try Streamlit Cloud secrets first, then OS env."""
    try:
        import streamlit as st  # noqa: PLC0415
        key: str = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:  # noqa: BLE001
        pass
    return os.getenv("ANTHROPIC_API_KEY", "")


class Settings(BaseSettings):
    """Validated application configuration loaded from env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: SecretStr = Field(default="")
    claude_model: str            = Field(default="claude-sonnet-4-6")
    max_tokens: int              = Field(default=2048, ge=256, le=8192)
    temperature: float           = Field(default=0.2,  ge=0.0, le=1.0)

    # App
    app_env:     Environment = Field(default=Environment.DEVELOPMENT)
    log_level:   str         = Field(default="INFO")
    app_title:   str         = Field(default="FinSight")
    app_version: str         = Field(default="0.1.0")

    # RAG
    chunk_size:      int = Field(default=800, ge=100, le=4000)
    chunk_overlap:   int = Field(default=100, ge=0,   le=500)
    top_k_results:   int = Field(default=5,   ge=1,   le=20)
    faiss_index_path: str = Field(default="/tmp/finsight_faiss")

    # yfinance
    yfinance_cache_ttl:   int   = Field(default=600, ge=60)
    yfinance_max_retries: int   = Field(default=3,   ge=1, le=5)
    yfinance_timeout:     float = Field(default=15.0, gt=0)

    # Validators
    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        up = v.upper()
        if up not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return up

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_lt_chunk(cls, v: int, info) -> int:  # type: ignore[override]
        size = info.data.get("chunk_size", 800)
        if v >= size:
            raise ValueError(f"chunk_overlap ({v}) must be < chunk_size ({size})")
        return v

    # Computed properties
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def api_key(self) -> str:
        """Resolved API key — raises RuntimeError if missing."""
        key = _resolve_anthropic_key() or self.anthropic_api_key.get_secret_value()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not configured.\n"
                "  Streamlit Cloud: App → Settings → Secrets\n"
                "  Local: set ANTHROPIC_API_KEY in .env"
            )
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()


settings: Settings = get_settings()
