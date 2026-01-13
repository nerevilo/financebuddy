from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from enum import Enum
import os


class TellerEnvironment(str, Enum):
    """Valid Teller API environments."""
    SANDBOX = "sandbox"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # App
    app_name: str = "FinTrack API"
    debug: bool = False

    # Teller API
    teller_app_id: str = "app_pn55bmnf8k4papve7o000"
    teller_cert_path: str = "./certificate.pem"
    teller_key_path: str = "./private_key.pem"
    teller_env: TellerEnvironment = TellerEnvironment.SANDBOX
    teller_api_url: str = "https://api.teller.io"

    # Ntropy API (ML Transaction Enrichment)
    ntropy_api_key: str = ""  # Add your API key in .env
    use_ntropy: bool = False  # Enable when you have an API key
    ntropy_api_url: str = "https://api.ntropy.com/v3"

    # OpenAI API (for LLM enrichment with search tools)
    openai_api_key: str = ""

    # Tavily API (AI-optimized search)
    tavily_api_key: str = ""

    # Anthropic API (Claude Haiku - cheapest LLM)
    anthropic_api_key: str = ""

    # Google Gemini API (FREE tier - 1,500 requests/day)
    gemini_api_key: str = ""
    use_gemini: bool = True

    # Database (defaults to SQLite, but should use DATABASE_URL from .env)
    database_url: str = "sqlite:///./fintrack.db"  # Will be overridden by .env

    # JWT Authentication
    secret_key: str = "your-super-secret-key-change-in-production"  # Override in .env
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Redis Cache (optional - app works without it)
    redis_url: Optional[str] = None  # e.g., "redis://localhost:6379/0"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Ensure secret_key is not the default value in non-debug mode."""
        default_key = "your-super-secret-key-change-in-production"
        # Check if debug is False and secret_key is the default
        # Note: info.data contains already validated fields
        debug = info.data.get("debug", False)
        if not debug and v == default_key:
            raise ValueError(
                "secret_key must be changed from the default value in non-debug mode. "
                "Set a secure SECRET_KEY in your .env file."
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars (like NEXT_PUBLIC_*)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
