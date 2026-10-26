from datetime import date
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore"
    )
    database_url: str = "postgresql+psycopg://aerovista:aerovista_demo@localhost:55432/aerovista"
    analytics_database_url: str = (
        "postgresql+psycopg://airline_reader:reader_demo@localhost:55432/aerovista"
    )
    openai_api_key: SecretStr = SecretStr("")
    ai_provider: str = "openai"
    openai_model: str = "gpt-6-luna"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_reasoning_effort: str = "medium"
    demo_reference_date: date = date(2026, 10, 26)
    query_timeout_ms: int = Field(default=5000, ge=100, le=15000)
    max_result_rows: int = Field(default=200, ge=1, le=500)
    ai_timeout_seconds: int = Field(default=90, ge=5, le=180)
    scheduler_enabled: bool = True
    scheduler_poll_seconds: int = Field(default=30, ge=1, le=3600)


settings = Settings()
