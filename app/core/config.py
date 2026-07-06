from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Quiz Backend"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://quiz:quiz@localhost:5432/quiz"
    jwt_secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
