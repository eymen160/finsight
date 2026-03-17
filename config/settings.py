"""
FinSight — Application Settings
===================================
Env var resolution order (first non-empty wins):
  1. Environment variable / .env file
  2. Hard-coded default

The Streamlit-specific st.secrets fallback has been removed —
it caused import errors when running under FastAPI/Uvicorn.
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: SecretStr = Field(default="")

    # CORRECT model names as of 2026:
    #   claude-opus-4-5          → most capable, slowest
    #   claude-sonnet-4-5        → balanced (recommended)
    #   claude-haiku-4-5-20251001 → fastest, cheapest
    claude_model: str = Field(default="claude-sonnet-4-5")
    max_tokens:   int = Field(default=1024, ge=256, le=8192)  # 1024 not 2048 → 2x faster

    # ── App ───────────────────────────────────────────────────
    app_env:     Environment = Field(default=Environment.DEVELOPMENT)
    log_level:   str         = Field(default="INFO")
    app_title:   str         = Field(default="FinSight")
    app_version: str         = Field(default="0.1.0")

    # ── RAG ───────────────────────────────────────────────────
    chunk_size:       int = Field(default=800,  ge=100, le=4000)
    chunk_overlap:    int = Field(default=100,  ge=0,   le=500)
    top_k_results:    int = Field(default=5,    ge=1,   le=20)
    faiss_index_path: str = Field(default="/tmp/finsight_faiss")

    # ── yfinance ──────────────────────────────────────────────
    yfinance_cache_ttl:   int   = Field(default=600,  ge=60)
    yfinance_max_retries: int   = Field(default=3,    ge=1, le=5)
    yfinance_timeout:     float = Field(default=10.0, gt=0)  # 10s not 15s

    # ── Validators ────────────────────────────────────────────
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
    def _overlap_lt_chunk(cls, v: int, info) -> int:
        size = info.data.get("chunk_size", 800)
        if v >= size:
            raise ValueError(f"chunk_overlap ({v}) must be < chunk_size ({size})")
        return v

    # ── Computed ──────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def api_key(self) -> str:
        """Resolved API key — raises RuntimeError if missing."""
        key = (
            os.getenv("ANTHROPIC_API_KEY", "")
            or self.anthropic_api_key.get_secret_value()
        )
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not configured.\n"
                "  Render/Vercel: set in Dashboard → Environment Variables\n"
                "  Local: set ANTHROPIC_API_KEY in .env"
            )
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
