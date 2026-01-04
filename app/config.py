from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/viral_tracker"
    
    # JWT Authentication
    secret_key: str = "your-super-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Apify
    apify_api_token: str = ""
    
    # Google Sheets
    google_service_account_file: str = "service-account.json"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # App
    environment: str = "development"
    
    class Config:
        env_file = ".env"


settings = Settings()
