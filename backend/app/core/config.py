"""Application configuration loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings. All values come from the environment or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # --- CORS (browser origins allowed to call the API) ---
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "tender_monitor"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-prod-this-is-not-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    # --- SMTP (email notifications; deferred feature, config present) ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@tender-monitor.bf"
    smtp_use_tls: bool = False

    # --- Scraping ---
    scrape_daily_cap_per_domain: int = 200
    rate_limit_min_delay_ms: int = 3000
    rate_limit_max_delay_ms: int = 8000
    playwright_headless: bool = True

    # --- CAPTCHA (deferred; gated) ---
    captcha_enabled: bool = False
    captcha_api_key: str = ""
    captcha_max_cost_per_run: float = 1.0

    # --- Localization for the target region ---
    scrape_timezone: str = "Africa/Ouagadougou"
    scrape_locale: str = "fr-FR"

    keywords_max_per_user: int = 50
    notification_emails_max: int = Field(default=5, description="Hard cap on recipient emails.")

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Use this everywhere instead of instantiating Settings()."""
    return Settings()
