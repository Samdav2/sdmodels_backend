from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # Project
    PROJECT_NAME: str = "SDModels API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sdmodels:sdmodels@localhost:5432/sdmodels"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT - RSA Encryption
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str = "private_key.pem"
    JWT_PUBLIC_KEY_PATH: str = "public_key.pem"
    # Fallback for base64 encoded keys in env
    JWT_PRIVATE_KEY: Optional[str] = os.getenv("JWT_PRIVATE_KEY")
    JWT_PUBLIC_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days

    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:8000,http://localhost:3001"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # File Storage
    STORAGE_BACKEND: str = "s3"  # Options: "s3", "opendrive", "azure"

    # S3/CloudFlare R2 Storage
    S3_BUCKET_NAME: str = "sdmodels-storage"
    S3_ACCESS_KEY: str = "dev-access-key"
    S3_SECRET_KEY: str = "dev-secret-key"
    S3_REGION: str = "us-east-1"
    CDN_URL: str = "https://cdn.sdmodels.com"

    # OpenDrive Storage
    OPENDRIVE_USERNAME: str = ""
    OPENDRIVE_PASSWORD: str = ""
    OPENDRIVE_PARTNER_ID: Optional[str] = "OpenDrive"

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "sdmodels"

    # Upload Limits
    MAX_MODEL_SIZE: int = 104857600  # 100MB
    MAX_IMAGE_SIZE: int = 10485760   # 10MB
    MAX_AVATAR_SIZE: int = 2097152   # 2MB

    # Payment - Paystack
    PAYSTACK_SECRET_KEY: str = "sk_test_dev"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_dev"
    PAYSTACK_WEBHOOK_SECRET: str = "whsec_dev"

    # Payment - NOWPayments (Crypto)
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_API_URL: str = "https://api.nowpayments.io/v1"
    NOWPAYMENTS_IPN_SECRET: str = ""

    # Payment - General
    PLATFORM_FEE_PERCENTAGE: float = 7.5
    MIN_DEPOSIT_AMOUNT: float = 10.0
    MIN_WITHDRAWAL_AMOUNT: float = 20.0

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "noreply@sdmodels.com"
    SMTP_PASSWORD: str = "dev-password"
    EMAILS_FROM_EMAIL: str = "noreply@sdmodels.com"
    EMAILS_FROM_NAME: str = "SDModels"

    # OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    DISCORD_CLIENT_ID: Optional[str] = None
    DISCORD_CLIENT_SECRET: Optional[str] = None

    # Admin
    ADMIN_EMAIL: str = "admin@sdmodels.com"
    ADMIN_PASSWORD: str = "ChangeThisPassword123!"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"


settings = Settings()
