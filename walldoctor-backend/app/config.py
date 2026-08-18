"""
Central configuration. All values are read from environment variables
(via a local .env file in development) so no secret ever lives in code.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./walldoctor.db"

    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    cors_origins: str = "http://localhost:5500"

    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
