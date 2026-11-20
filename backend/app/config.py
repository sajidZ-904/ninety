import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Ninety Level 10 Meeting Platform"
    APP_NOW: str = "2026-11-11T15:00:00Z"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ninety.db")
    COMPANY_TIMEZONE: str = "America/Chicago"
    CORS_ORIGINS: list[str] = ["*"]
    SECRET_KEY: str = "ninety-secret-key-assessment"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
