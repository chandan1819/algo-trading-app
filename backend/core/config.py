"""Application configuration loaded from environment variables."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the algo trading application.

    All values are loaded from a .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Angel One SmartAPI credentials ───────────────────────────────────
    ANGEL_API_KEY: str
    ANGEL_CLIENT_ID: str
    ANGEL_PASSWORD: str
    ANGEL_TOTP_SECRET: str

    # ── Database ─────────────────────────────────────────────────────────
    DB_URL: str = "sqlite+aiosqlite:///./trading.db"

    # ── Telegram notifications (optional) ────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # ── Email notifications (optional) ───────────────────────────────────
    EMAIL_HOST: Optional[str] = None
    EMAIL_PORT: Optional[int] = None
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None

    # ── Risk management defaults ─────────────────────────────────────────
    MAX_LOSS_PER_DAY: float = 5000.0
    MAX_TRADES_PER_DAY: int = 20
    CAPITAL_PER_TRADE: float = 50000.0
    MAX_DRAWDOWN_PCT: float = 5.0

    # ── Redis (optional) ─────────────────────────────────────────────────
    REDIS_URL: Optional[str] = None

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


settings = Settings()  # type: ignore[call-arg]
