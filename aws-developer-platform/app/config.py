"""Application configuration loaded from environment or injected by the runtime."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; production secrets are resolved before process startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./platform.db"
    session_secret: SecretStr = SecretStr("development-only-change-me-32-bytes")
    session_idle_minutes: int = 15
    session_absolute_hours: int = 8
    session_warning_minutes: int = 2
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    tfc_base_url: str = "https://app.terraform.io"
    tfc_token_secret_arn: str | None = None
    tfc_webhook_secret: SecretStr | None = None
    github_webhook_secret: SecretStr | None = None
    config_repo: str = "platform-config"
    aws_region: str = "us-east-1"
    project_iam_backend: str = "ministack"
    ministack_endpoint: str = "http://localhost:4566"
    ministack_account_id: str = "000000000000"
    rate_limit_per_minute: int = 60
    global_rate_limit_per_minute: int = 1000


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""

    return Settings()
