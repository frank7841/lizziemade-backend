from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "LizzieMade API"
    app_env: str = "development"
    debug: bool = True
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Paystack
    paystack_secret_key: str = ""
    paystack_callback_url: str = ""

    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Email
    resend_api_key: str = ""
    email_from: str = "noreply@lizziemade.com"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
