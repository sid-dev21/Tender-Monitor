"""Application configuration loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Built SPA (`npm run build`). When present, the API also serves the frontend,
# making the whole app single-origin — see app/main.py. Absent in development,
# where Vite serves the SPA on its own port.
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def frontend_is_bundled() -> bool:
    """True when this server also serves the SPA (checked at call time, not
    import time, so a build produced after startup is still picked up)."""
    return (FRONTEND_DIST / "index.html").is_file()


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
    # 5173 is Vite's default; it falls back to 5174+ when another dev server
    # already holds the port (e.g. a second checkout of this project running in
    # parallel), so both are allowed in dev. In prod, CORS_ORIGINS is set
    # explicitly in the environment to the deployed frontend origin only.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "tender_monitor"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-in-prod-this-is-not-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    reset_token_expire_minutes: int = 30  # password-reset link validity

    # Public URL of the frontend, used to build the reset-password link in emails.
    frontend_base_url: str = "http://localhost:5173"

    # --- SMTP (email notifications; deferred feature, config present) ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@tender-monitor.bf"
    smtp_use_tls: bool = False

    # --- Scraping ---
    # Hard cap on PDFs fetched per run: portals can link hundreds of documents
    # (dgmp.gouv.ml links 541), which would take hours and hammer the site.
    max_pdfs_per_run: int = 20
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

    # --- LLM relevance scoring (Ollama) ---
    # On-demand, user-triggered semantic scoring over the keyword-filtered subset.
    # Explicitly NOT part of the scrape hot path (two-speed principle, CLAUDE.md).
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b-instruct"
    ollama_timeout_s: float = 60.0
    # Bounds worst-case latency of POST /api/tenders/score. Inference is CPU-only
    # (no CUDA on the dev laptop, none on the VPS), so each tender costs several
    # seconds and this cap is what keeps a live demo bearable. Measure with
    # `python -m scripts.check_ollama` and tune per machine.
    score_max_tenders: int = 8

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Use this everywhere instead of instantiating Settings()."""
    return Settings()
