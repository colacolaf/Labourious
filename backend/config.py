import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Labourious")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/labourious.db")

    VAULT_PASSWORD: str = os.getenv("VAULT_PASSWORD", "")
    VAULT_SALT: str = os.getenv("VAULT_SALT", "labourious-salt-v1")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))

    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

    EXCHANGE_API_KEY: str = os.getenv("EXCHANGE_API_KEY", "")
    EXCHANGE_API_SECRET: str = os.getenv("EXCHANGE_API_SECRET", "")
    EXCHANGE_TESTNET: bool = os.getenv("EXCHANGE_TESTNET", "true").lower() == "true"

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production-32-chars-min")

    # Notifications
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: Optional[str] = os.getenv("SMTP_PORT", "465")
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER: Optional[str] = os.getenv("TWILIO_FROM_NUMBER")

settings = Settings()
