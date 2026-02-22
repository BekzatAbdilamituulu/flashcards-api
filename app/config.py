<<<<<<< HEAD
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
=======
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # defaults for local/dev/tests
    algorithm: str = "HS256"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./data/app.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
>>>>>>> 93af5e0 (github test)
    )


@lru_cache
<<<<<<< HEAD
def get_settings():
    return Settings()

=======
def get_settings() -> Settings:
    return Settings()


>>>>>>> 93af5e0 (github test)
settings = get_settings()