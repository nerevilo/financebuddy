from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    app_name: str = "FinTrack API"
    debug: bool = True

    # Teller API
    teller_app_id: str = "app_pn55bmnf8k4papve7o000"
    teller_cert_path: str = "./certificate.pem"
    teller_key_path: str = "./private_key.pem"
    teller_env: str = "sandbox"  # sandbox, development, production
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars (like NEXT_PUBLIC_*)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
