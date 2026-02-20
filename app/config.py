from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    algorithm: str
    secret_key: str
    access_token_expire_minutes: int
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


@lru_cache
def get_settings():
    return Settings()

settings = get_settings()