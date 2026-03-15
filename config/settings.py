"""
FinSight — Application Settings
===================================
Single source of truth for all runtime configuration.

Secret resolution order (first non-empty value wins):

1. ``st.secrets["ANTHROPIC_API_KEY"]``  — Streamlit Cloud deployment
2. ``ANTHROPIC_API_KEY`` environment variable / ``.env`` file     — local dev

All other settings are read exclusively from environment variables or
``.env``.  Nothing is ever hardcoded.

Usage::

    from config.settings import settings
    print(settings.api_key)      # resolved API key (raises if missing)
    print(settings.claude_model) # "claude-sonnet-4-6"
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Runtime environment identifier."""

    DEVELOPMENT = "development"
    PRODUCTION  = "production"


def _resolve_anthropic_key() -> str:
    """Resolve the Anthropic API key from available secret sources.

    Checks Streamlit Cloud secrets first so that deployments work
    without any OS-level environment variable configuration.

    Returns:
        The raw API key string, or ``""`` if not found in any source.
    """
    # 1. Streamlit Cloud secrets (only available inside a running Streamlit app)
    try:
        import streamlit as st  # noqa: PLC0415  (local import intentional)

        key: str = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:  # noqa: BLE001
        pass

    # 2. OS environment / .env file (picked up by pydantic-settings below,
    #    but we also check here for the rare case where Settings is
    #    instantiated before dotenv loads).
    return os.getenv("ANTHROPIC_API_KEY", "")


class Settings(BaseSettings):
    """Centralised, validated application configuration.

    All fields can be overridden via environment variables (case-insensitive)
    or a ``.env`` file in the project root.  Pydantic validates types and
    constraints at startup, failing fast if the config is invalid.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: SecretStr = Field(
        default="",
        description="Anthropic API key.  Set via ANTHROPIC_API_KEY env var.",
    )
    claude_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model identifier passed to the Messages API.",
    )
    max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Maximum tokens in Claude's response.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Sampling temperature. Lower = more deterministic.",
    )

    # ── Application ───────────────────────────────────────────
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Runtime environment tag.",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level (DEBUG / INFO / WARNING / ERROR).",
    )
    app_title: str = Field(default="FinSight")
    app_version: str = Field(default="0.1.0")

    # ── RAG pipeline ──────────────────────────────────────────
    chunk_size: int = Field(
        default=800,
        ge=100,
        le=4000,
        description="Target token count per document chunk.",
    )
    chunk_overlap: int = Field(
        default=100,
        ge=0,
        le=500,
        description="Token overlap between consecutive chunks.",
    )
    top_k_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks returned per retrieval query.",
    )
    faiss_index_path: str = Field(
        default="/tmp/finsight_faiss",  # /tmp writable on Streamlit Cloud
        description="Directory where the FAISS index is persisted.",
    )

    # ── Market data ───────────────────────────────────────────
    yfinance_cache_ttl: int = Field(
        default=600,
        ge=60,
        description="Seconds to cache yfinance responses (10 min default).",
    )
    yfinance_max_retries: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum retry attempts on rate-limit errors.",
    )
    yfinance_timeout: float = Field(
        default=15.0,
        gt=0,
        description="Per-request timeout in seconds for yfinance calls.",
    )

    # ── Validators ────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        """Ensure log_level is a valid stdlib level name."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return upper

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_less_than_chunk(cls, v: int, info) -> int:  # type: ignore[override]
        """Ensure chunk_overlap < chunk_size to avoid infinite loops."""
        chunk_size = info.data.get("chunk_size", 800)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})"
            )
        return v

    # ── Computed properties ───────────────────────────────────

    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.app_env == Environment.PRODUCTION

    @property
    def api_key(self) -> str:
        """Return the resolved Anthropic API key.

        Resolution order: Streamlit secrets → env var → .env file.

        Returns:
            Raw API key string (never empty).

        Raises:
            RuntimeError: If no key is found in any configured source.
        """
        key = _resolve_anthropic_key() or self.anthropic_api_key.get_secret_value()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not configured.\n"
                "  • Streamlit Cloud: App → Settings → Secrets\n"
                "  • Local dev: add ANTHROPIC_API_KEY=sk-ant-... to .env"
            )
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton.

    Using ``lru_cache`` ensures the ``.env`` file is read only once and
    that all modules share the exact same configuration object.

    Returns:
        The application :class:`Settings` instance.
    """
    return Settings()


# Convenience module-level alias — ``from config.settings import settings``
settings: Settings = get_settings()
