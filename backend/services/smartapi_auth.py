"""SmartAPI authentication service for Angel One broker."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from pyotp import TOTP
from SmartApi import SmartConnect

from backend.core.config import settings

logger = logging.getLogger(__name__)


class SmartAPIAuth:
    """Singleton authentication manager for Angel One SmartAPI.

    Handles login, session management, token refresh, and logout.
    """

    _instance: Optional[SmartAPIAuth] = None
    _lock = threading.Lock()

    def __new__(cls) -> SmartAPIAuth:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._smart_connect: Optional[SmartConnect] = None
        self._auth_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._login_time: float = 0.0
        self._session_lock = threading.Lock()
        # Session is considered stale after 6 hours (Angel One expires ~24h).
        self._session_ttl: float = 6 * 60 * 60

    # ── public API ────────────────────────────────────────────────────────

    def login(self) -> SmartConnect:
        """Authenticate with Angel One and return a ready SmartConnect object."""
        with self._session_lock:
            return self._do_login()

    def get_session(self) -> SmartConnect:
        """Return an active session, re-authenticating if stale."""
        with self._session_lock:
            if self._is_session_valid():
                return self._smart_connect  # type: ignore[return-value]
            logger.info("Session expired or missing -- re-authenticating.")
            return self._do_login()

    def get_feed_token(self) -> str:
        """Return the feed token required for WebSocket connections."""
        if self._feed_token is None:
            self.get_session()
        if self._feed_token is None:
            raise RuntimeError("Feed token unavailable after authentication.")
        return self._feed_token

    def get_auth_token(self) -> str:
        """Return the current JWT auth token."""
        if self._auth_token is None:
            self.get_session()
        if self._auth_token is None:
            raise RuntimeError("Auth token unavailable after authentication.")
        return self._auth_token

    def refresh_session(self) -> SmartConnect:
        """Force a token refresh using the refresh token."""
        with self._session_lock:
            if self._refresh_token and self._smart_connect:
                try:
                    token_data = self._smart_connect.generateToken(
                        self._refresh_token
                    )
                    if token_data and token_data.get("status"):
                        self._auth_token = token_data["data"]["jwtToken"]
                        self._refresh_token = token_data["data"]["refreshToken"]
                        self._feed_token = self._smart_connect.getfeedToken()
                        self._login_time = time.time()
                        logger.info("Session refreshed via refresh token.")
                        return self._smart_connect
                except Exception:
                    logger.warning(
                        "Token refresh failed -- falling back to full login.",
                        exc_info=True,
                    )
            return self._do_login()

    def logout(self) -> None:
        """Log out and invalidate the current session."""
        with self._session_lock:
            if self._smart_connect:
                try:
                    self._smart_connect.terminateSession(settings.ANGEL_CLIENT_ID)
                    logger.info("SmartAPI session terminated.")
                except Exception:
                    logger.warning("Error during session termination.", exc_info=True)
            self._reset_state()

    # ── internals ─────────────────────────────────────────────────────────

    def _do_login(self) -> SmartConnect:
        max_retries = 3
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                obj = SmartConnect(api_key=settings.ANGEL_API_KEY)
                totp = TOTP(settings.ANGEL_TOTP_SECRET).now()

                data = obj.generateSession(
                    clientCode=settings.ANGEL_CLIENT_ID,
                    password=settings.ANGEL_PASSWORD,
                    totp=totp,
                )

                if not data or not data.get("status"):
                    msg = data.get("message", "Unknown error") if data else "No response"
                    raise RuntimeError(f"Login failed: {msg}")

                self._auth_token = data["data"]["jwtToken"]
                self._refresh_token = data["data"]["refreshToken"]
                self._feed_token = obj.getfeedToken()
                self._smart_connect = obj
                self._login_time = time.time()

                logger.info(
                    "SmartAPI login successful (attempt %d) for client %s.",
                    attempt,
                    settings.ANGEL_CLIENT_ID,
                )
                return obj

            except Exception as exc:
                last_exc = exc
                logger.error(
                    "Login attempt %d/%d failed: %s", attempt, max_retries, exc
                )
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        raise RuntimeError(
            f"SmartAPI login failed after {max_retries} attempts."
        ) from last_exc

    def _is_session_valid(self) -> bool:
        if self._smart_connect is None or self._auth_token is None:
            return False
        return (time.time() - self._login_time) < self._session_ttl

    def _reset_state(self) -> None:
        self._smart_connect = None
        self._auth_token = None
        self._refresh_token = None
        self._feed_token = None
        self._login_time = 0.0
