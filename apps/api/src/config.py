from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_env: str = "development"
    api_cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://studio:studio@localhost:5432/studio"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "studio"
    s3_secret_key: str = "studio12345"
    s3_bucket: str = "studio-files"
    s3_region: str = "us-east-1"

    jwt_secret: str = "change-me-in-production-please-use-a-random-32-byte-secret"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    celery_task_always_eager: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
