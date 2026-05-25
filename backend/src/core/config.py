from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONTINUUM_",
        case_sensitive=False
    )

    environment: Literal["local", "development", "staging", "production"] = "local"
    project_name: str = "Continuum API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/continuum"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    s3_bucket_name: str = "continuum-documents-local"
    kms_key_id: str = "alias/continuum-local"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
