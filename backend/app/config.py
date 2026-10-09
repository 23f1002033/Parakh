from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # The owner keeps .env at the repo root; backend/.env also works.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    serpapi_key: SecretStr | None = None
    serpapi_mode: Literal["live", "record", "replay"] = "replay"
    database_url: str = "sqlite:///./parakh.db"
    cache_ttl_hours: float = 24
    daily_search_cap: int = 40
    ip_salt: str = ""
    fixture_dir: str = "tests/fixtures/serp"

    @field_validator("serpapi_key", mode="before")
    @classmethod
    def _empty_key_is_none(cls, v):
        return v or None

    @property
    def fixture_path(self) -> Path:
        p = Path(self.fixture_dir)
        return p if p.is_absolute() else BACKEND_DIR / p

    def api_key(self) -> str | None:
        return self.serpapi_key.get_secret_value() if self.serpapi_key else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
