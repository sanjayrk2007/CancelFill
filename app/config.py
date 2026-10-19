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
    FRONTEND_URL: str = "http://localhost:5173"

    # Password reset
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Notifications. Each channel falls back to logging to the console when unconfigured.
    NOTIFICATION_DISPATCH_INTERVAL_SECONDS: int = 5
    NOTIFICATION_MAX_ATTEMPTS: int = 5
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "CancelFill <no-reply@cancelfill.local>"
    SMTP_USE_TLS: bool = True
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@cancelfill.local"

    # Payments: none | mock | razorpay
    PAYMENT_PROVIDER: str = "none"
    PAYMENT_CURRENCY: str = "INR"
    PAYMENT_WINDOW_SECONDS: int = 600
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    MOCK_PAYMENT_SECRET: str = "mock-payment-secret"
    # Customer cancellations get a full refund only if made at least this long before the slot starts.
    REFUND_CUTOFF_HOURS: int = 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
