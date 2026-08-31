from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CancelFill – Intelligent Cancellation Recovery & Waitlist Platform"
    VERSION: str = "0.1.0 (Review-1)"
    API_V1_STR: str = "/api/v1"
    
    # Database connection URL (Defaults to local SQLite for instant out-of-the-box running; override with PostgreSQL DATABASE_URL in .env for production DB)
    DATABASE_URL: str = "sqlite:///./cancelfill.db"
    
    # Default temporary hold duration in minutes
    DEFAULT_HOLD_DURATION_MINUTES: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
