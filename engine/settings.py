from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "l9-service"
    app_port: int = 8000
    debug: bool = False
    api_key: str = ""
    redis_url: str = "redis://redis:6379"
    log_level: str = "INFO"
