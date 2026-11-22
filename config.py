"""Central application configuration.

All runtime settings are read from environment variables (optionally loaded
from a local ``.env`` file). Secrets such as the Gemini API key are only ever
held server-side in this object and are never rendered to the frontend.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

SUPPORTED_PROVIDERS = ("ollama", "gemini")
PRIORITIES = ("High", "Medium", "Low")
SCENARIO_TYPES = ("Positive", "Negative", "Edge Case")

APP_NAME = "AI Test Case Generator Agent"
APP_TAGLINE = "Requirement-aware test design, powered by LLM agents"
APP_VERSION = "1.0.0"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    gemini_api_key: str
    gemini_model: str
    temperature: float
    timeout_seconds: int
    max_test_cases: int
    max_repair_attempts: int
    database_path: Path

    @property
    def active_model(self) -> str:
        return self.ollama_model if self.llm_provider == "ollama" else self.gemini_model

    @property
    def gemini_key_configured(self) -> bool:
        key = self.gemini_api_key.strip()
        return bool(key) and not key.lower().startswith("your_")

    def with_provider(self, provider: str) -> "Settings":
        """Return a copy that uses another provider (explicit user choice only)."""
        provider = provider.lower().strip()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider '{provider}'.")
        return replace(self, llm_provider=provider)


def load_settings() -> Settings:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower() or "ollama"
    db_path = Path(os.getenv("DATABASE_PATH", "data/test_cases.db"))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    return Settings(
        llm_provider=provider,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip(),
        temperature=_float("LLM_TEMPERATURE", 0.2),
        timeout_seconds=_int("LLM_TIMEOUT_SECONDS", 120),
        max_test_cases=_int("MAX_TEST_CASES", 20),
        max_repair_attempts=_int("MAX_REPAIR_ATTEMPTS", 1),
        database_path=db_path,
    )
