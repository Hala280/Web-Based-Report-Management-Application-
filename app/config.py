"""Application configuration loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings.

    All values are required and must come from the environment or a local
    .env file. Never hardcode secrets here — see .env.example for the
    expected shape.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_DB_CONN: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int
    CRED_ENCRYPTION_KEY: str
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the environment is parsed once."""
    return Settings()
