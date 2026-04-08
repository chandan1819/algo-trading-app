"""WebSocket service for live market data from Angel One."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from backend.core.config import settings
from backend.services.smartapi_auth import SmartAPIAuth

logger = logging.getLogger(__name__)

# Angel One WebSocket subscription modes.
SNAP_QUOTE_MODE = 3
QUOTE_MODE = 2
LTP_MODE = 1


class WebSocketService:
    """Manages a persistent WebSocket connection for live tick data.

    Uses Angel One SmartWebSocketV2 under the hood.
    """

    def __init__(
        self,
        auth: Optional[SmartAPIAuth] = None,
        on_tick: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._auth = auth or SmartAPIAuth()
        self._ws: Optional[SmartWebSocketV2] = None
        self._latest_ticks: Dict[str, Dict[str, Any]] = {}
        self._tick_lock = threading.Lock()
        self._user_on_tick = on_tick
        self._connected = False
        self._subscribed_tokens: List[Dict[str, Any]] = []

    # ── public API ────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Establish the WebSocket connection to Angel One."""
        auth_token = self._auth.get_auth_token()
        feed_token = self._auth.get_feed_token()
        client_id = settings.ANGEL_CLIENT_ID

        self._ws = SmartWebSocketV2(
            auth_token,
            settings.ANGEL_API_KEY,
            client_id,
            feed_token,
        )

        self._ws.on_open = self._on_open
        self._ws.on_data = self._on_data
        self._ws.on_error = self._on_error
        self._ws.on_close = self._on_close

        logger.info("Starting WebSocket connection...")
        self._ws.connect()

    def connect_async(self) -> threading.Thread:
        """Start the WebSocket connection in a background thread.

        Returns:
            The daemon thread running the connection.
        """
        thread = threading.Thread(target=self.connect, daemon=True, name="ws-feed")
        thread.start()
        return thread

    def subscribe(
        self,
        tokens: List[str],
        exchange: str = "NSE",
        mode: int = SNAP_QUOTE_MODE,
    ) -> None:
        """Subscribe to live data for the given instrument tokens.

        Args:
            tokens: List of symbol tokens (as strings).
            exchange: Exchange segment.
            mode: Subscription mode (1=LTP, 2=Quote, 3=SnapQuote).
        """
        exchange_code = self._exchange_code(exchange)
        token_list = [
            {
                "exchangeType": exchange_code,
                "tokens": tokens,
            }
        ]

        self._subscribed_tokens.extend(token_list)

        if self._ws and self._connected:
            try:
                self._ws.subscribe("abc123", mode, token_list)
                logger.info(
                    "Subscribed to %d tokens on %s (mode=%d).",
                    len(tokens),
                    exchange,
                    mode,
                )
            except Exception as exc:
                logger.error("Subscribe failed: %s", exc)
                raise
        else:
            logger.info(
                "Queued subscription for %d tokens (WebSocket not yet connected).",
                len(tokens),
            )

    def unsubscribe(
        self,
        tokens: List[str],
        exchange: str = "NSE",
        mode: int = SNAP_QUOTE_MODE,
    ) -> None:
        """Unsubscribe from live data for the given tokens."""
        exchange_code = self._exchange_code(exchange)
        token_list = [
            {
                "exchangeType": exchange_code,
                "tokens": tokens,
            }
        ]

        if self._ws and self._connected:
            try:
                self._ws.unsubscribe("abc123", mode, token_list)
                logger.info("Unsubscribed from %d tokens.", len(tokens))
            except Exception as exc:
                logger.error("Unsubscribe failed: %s", exc)

    def get_latest_tick(self, token: str) -> Optional[Dict[str, Any]]:
        """Return the most recent tick data for a given token."""
        with self._tick_lock:
            return self._latest_ticks.get(token)

    def get_all_ticks(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of all latest ticks."""
        with self._tick_lock:
            return dict(self._latest_ticks)

    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close_connection()
                logger.info("WebSocket connection closed.")
            except Exception as exc:
                logger.warning("Error closing WebSocket: %s", exc)
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── callbacks ─────────────────────────────────────────────────────────

    def _on_open(self, wsapp: Any) -> None:
        logger.info("WebSocket connection opened.")
        self._connected = True

        # Subscribe to any tokens that were queued before the connection opened.
        if self._subscribed_tokens:
            try:
                self._ws.subscribe("abc123", SNAP_QUOTE_MODE, self._subscribed_tokens)  # type: ignore[union-attr]
                logger.info(
                    "Replayed %d queued subscriptions.", len(self._subscribed_tokens)
                )
            except Exception as exc:
                logger.error("Failed to replay subscriptions: %s", exc)

    def _on_data(self, wsapp: Any, message: Any) -> None:
        try:
            token = str(message.get("token", ""))
            if token:
                with self._tick_lock:
                    self._latest_ticks[token] = message

            if self._user_on_tick:
                self._user_on_tick(message)

        except Exception as exc:
            logger.error("Error processing tick data: %s", exc)

    def _on_error(self, wsapp: Any, error: Any) -> None:
        logger.error("WebSocket error: %s", error)
        self._connected = False

    def _on_close(self, wsapp: Any, close_status_code: Any, close_msg: Any) -> None:
        logger.info(
            "WebSocket closed (code=%s, msg=%s).", close_status_code, close_msg
        )
        self._connected = False

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _exchange_code(exchange: str) -> int:
        """Map exchange name to Angel One numeric exchange type."""
        mapping = {
            "NSE": 1,
            "NFO": 2,
            "BSE": 3,
            "BFO": 4,
            "MCX": 5,
            "CDS": 13,
        }
        code = mapping.get(exchange.upper())
        if code is None:
            raise ValueError(f"Unknown exchange: {exchange}")
        return code
