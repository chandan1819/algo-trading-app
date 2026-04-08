"""Instrument management service for Angel One SmartAPI."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SCRIPMASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)


class InstrumentService:
    """Fetches, caches, and looks up Angel One instrument master data."""

    def __init__(self) -> None:
        self._instruments: List[Dict[str, Any]] = []
        # Quick lookup maps: (exchange, trading_symbol) -> token
        self._symbol_to_token: Dict[tuple[str, str], str] = {}
        # Reverse: (exchange, token) -> trading_symbol
        self._token_to_symbol: Dict[tuple[str, str], str] = {}
        self._loaded_at: float = 0.0
        self._lock = threading.Lock()
        # Refresh interval -- 12 hours by default.
        self._cache_ttl: float = 12 * 60 * 60

    # ── public API ────────────────────────────────────────────────────────

    def load_instruments(self, force: bool = False) -> int:
        """Download the full ScripMaster JSON and build lookup maps.

        Args:
            force: Bypass cache TTL and reload regardless.

        Returns:
            Number of instruments loaded.
        """
        with self._lock:
            if not force and self._is_cache_valid():
                return len(self._instruments)
            return self._fetch_and_index()

    def token_lookup(self, ticker: str, exchange: str = "NSE") -> Optional[str]:
        """Return the symbol token for a given trading symbol and exchange."""
        self._ensure_loaded()
        return self._symbol_to_token.get((exchange, ticker.upper()))

    def symbol_lookup(self, token: str, exchange: str = "NSE") -> Optional[str]:
        """Return the trading symbol for a given token and exchange."""
        self._ensure_loaded()
        return self._token_to_symbol.get((exchange, str(token)))

    def search_instruments(
        self, query: str, exchange: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search instruments by name / symbol substring.

        Args:
            query: Case-insensitive substring to search for.
            exchange: Optional exchange filter (e.g. "NSE", "BSE", "NFO").
            limit: Maximum number of results.

        Returns:
            List of matching instrument dicts.
        """
        self._ensure_loaded()
        query_upper = query.upper()
        results: List[Dict[str, Any]] = []

        for inst in self._instruments:
            if exchange and inst.get("exch_seg") != exchange:
                continue
            name = inst.get("name", "").upper()
            symbol = inst.get("symbol", "").upper()
            if query_upper in name or query_upper in symbol:
                results.append(inst)
                if len(results) >= limit:
                    break

        return results

    def get_all_instruments(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all cached instruments, optionally filtered by exchange."""
        self._ensure_loaded()
        if exchange is None:
            return list(self._instruments)
        return [i for i in self._instruments if i.get("exch_seg") == exchange]

    # ── internals ─────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if not self._is_cache_valid():
            self.load_instruments()

    def _is_cache_valid(self) -> bool:
        if not self._instruments:
            return False
        return (time.time() - self._loaded_at) < self._cache_ttl

    def _fetch_and_index(self) -> int:
        max_retries = 3
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Downloading ScripMaster (attempt %d/%d)...", attempt, max_retries
                )
                with httpx.Client(timeout=60.0) as client:
                    resp = client.get(SCRIPMASTER_URL)
                    resp.raise_for_status()
                    data: List[Dict[str, Any]] = resp.json()

                self._instruments = data
                self._symbol_to_token.clear()
                self._token_to_symbol.clear()

                for inst in data:
                    exch = inst.get("exch_seg", "")
                    token = str(inst.get("token", ""))
                    symbol = inst.get("symbol", "").upper()
                    if exch and token and symbol:
                        self._symbol_to_token[(exch, symbol)] = token
                        self._token_to_symbol[(exch, token)] = symbol

                self._loaded_at = time.time()
                logger.info(
                    "ScripMaster loaded: %d instruments indexed.", len(data)
                )
                return len(data)

            except Exception as exc:
                last_exc = exc
                logger.error(
                    "ScripMaster download attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        raise RuntimeError(
            "Failed to load ScripMaster after retries."
        ) from last_exc
