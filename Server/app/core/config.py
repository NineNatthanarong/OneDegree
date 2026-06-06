from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Degree Plan Curriculum API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./degreeplan.db"
    seed_data_path: str = "curriculum_database.json"
    cors_allow_origins: str = "*"
    default_page_size: int = 50
    max_page_size: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

