from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, computed_field


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True

    # raw env value for production/staging
    database_url: str | None = None

    secret_key: str = "dev-secret-key-change-me"
    refresh_secret_key: str = "dev-refresh-secret-key-change-me"

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_hosts: str = "localhost,127.0.0.1, testserver"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "test", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of: {', '.join(sorted(allowed))}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [x.strip() for x in self.backend_cors_origins.split(",") if x.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts.split(",") if x.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @computed_field
    @property
    def resolved_database_url(self) -> str:
        if self.is_development:
            return "sqlite:///./data/dev.db"
        if self.is_test:
            return "sqlite:///./data/test.db"
        if not self.database_url:
            raise ValueError("DATABASE_URL is required in production")
        return self.database_url

    def validate_for_production(self) -> None:
        if not self.is_production:
            return

        weak_values = {
            "dev-secret-key-change-me",
            "dev-refresh-secret-key-change-me",
            "change-me",
            "secret",
        }

        if self.secret_key in weak_values or len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY is too weak for production")

        if self.refresh_secret_key in weak_values or len(self.refresh_secret_key) < 32:
            raise ValueError("REFRESH_SECRET_KEY is too weak for production")

        if self.resolved_database_url.startswith("sqlite"):
            raise ValueError("SQLite should not be used in production")


settings = Settings()
settings.validate_for_production()