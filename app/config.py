from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CancelFill – Intelligent Cancellation Recovery & Waitlist Platform"
    VERSION: str = "0.1.0 (Review-1)"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./cancelfill.db"
    DEFAULT_HOLD_DURATION_SECONDS: int = 900
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 15
    JWT_SECRET: str = "dev-secret-key-change-in-production"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
