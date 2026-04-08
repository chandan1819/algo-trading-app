"""Market data service for Angel One SmartAPI."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import pandas as pd

from backend.services.instrument_service import InstrumentService
from backend.services.smartapi_auth import SmartAPIAuth

logger = logging.getLogger(__name__)


class CandleInterval(str, Enum):
    """Supported candle intervals for Angel One historical data."""

    ONE_MINUTE = "ONE_MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"


class MarketDataService:
    """Fetches historical and live market data via SmartAPI."""

    def __init__(
        self,
        auth: Optional[SmartAPIAuth] = None,
        instrument_service: Optional[InstrumentService] = None,
    ) -> None:
        self._auth = auth or SmartAPIAuth()
        self._instruments = instrument_service or InstrumentService()

    # ── public API ────────────────────────────────────────────────────────

    def get_historical_data(
        self,
        ticker: str,
        duration_days: int = 30,
        interval: str | CandleInterval = CandleInterval.ONE_DAY,
        exchange: str = "NSE",
    ) -> pd.DataFrame:
        """Fetch OHLCV candle data and return a pandas DataFrame.

        Args:
            ticker: Trading symbol (e.g. "RELIANCE-EQ", "SBIN-EQ").
            duration_days: Number of days of history to fetch.
            interval: Candle interval -- one of CandleInterval values.
            exchange: Exchange segment (default "NSE").

        Returns:
            DataFrame with columns [date, open, high, low, close, volume].
        """
        token = self._resolve_token(ticker, exchange)
        interval_str = (
            interval.value if isinstance(interval, CandleInterval) else interval
        )

        to_date = datetime.now()
        from_date = to_date - timedelta(days=duration_days)

        params = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": interval_str,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }

        session = self._auth.get_session()
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            try:
                resp = session.getCandleData(params)

                if not resp or not resp.get("status"):
                    msg = resp.get("message", "Unknown error") if resp else "No response"
                    raise RuntimeError(f"getCandleData failed: {msg}")

                data = resp["data"]
                df = pd.DataFrame(
                    data,
                    columns=["date", "open", "high", "low", "close", "volume"],
                )
                df["date"] = pd.to_datetime(df["date"])
                logger.info(
                    "Fetched %d candles for %s (%s, %s).",
                    len(df),
                    ticker,
                    exchange,
                    interval_str,
                )
                return df

            except Exception as exc:
                logger.error(
                    "getCandleData attempt %d/%d for %s failed: %s",
                    attempt,
                    max_retries,
                    ticker,
                    exc,
                )
                if attempt == max_retries:
                    raise
                # Re-authenticate in case of token expiry.
                session = self._auth.refresh_session()

        # Should not reach here, but satisfy the type checker.
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    def get_ltp(self, ticker: str, exchange: str = "NSE") -> float:
        """Return the last traded price for a given ticker.

        Args:
            ticker: Trading symbol.
            exchange: Exchange segment.

        Returns:
            Last traded price as a float.
        """
        token = self._resolve_token(ticker, exchange)
        session = self._auth.get_session()

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                resp = session.ltpData(exchange, ticker, token)

                if not resp or not resp.get("status"):
                    msg = resp.get("message", "Unknown error") if resp else "No response"
                    raise RuntimeError(f"ltpData failed: {msg}")

                ltp = float(resp["data"]["ltp"])
                logger.debug("LTP for %s (%s): %.2f", ticker, exchange, ltp)
                return ltp

            except Exception as exc:
                logger.error(
                    "ltpData attempt %d/%d for %s failed: %s",
                    attempt,
                    max_retries,
                    ticker,
                    exc,
                )
                if attempt == max_retries:
                    raise
                session = self._auth.refresh_session()

        raise RuntimeError(f"Failed to get LTP for {ticker}")

    # ── internals ─────────────────────────────────────────────────────────

    def _resolve_token(self, ticker: str, exchange: str) -> str:
        token = self._instruments.token_lookup(ticker, exchange)
        if token is None:
            raise ValueError(
                f"Symbol token not found for ticker={ticker}, exchange={exchange}. "
                "Ensure the instrument master has been loaded."
            )
        return token
