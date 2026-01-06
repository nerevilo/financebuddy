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

    # Database
    database_url: str = "sqlite:///./fintrack.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
