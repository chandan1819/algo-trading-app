"""Market data API routes."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.instrument_service import InstrumentService
from backend.services.market_data import MarketDataService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market"])

market_service = MarketDataService()
instrument_service = InstrumentService()


class LTPResponse(BaseModel):
    ticker: str
    ltp: float
    exchange: str


class HistoricalBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalResponse(BaseModel):
    ticker: str
    bars: list[HistoricalBar]
    count: int


class InstrumentResult(BaseModel):
    symbol: str
    token: str
    name: str
    exchange: str
    instrument_type: Optional[str] = None
    lot_size: Optional[str] = None


@router.get("/ltp/{ticker}", response_model=LTPResponse)
async def get_ltp(ticker: str, exchange: str = Query("NSE")):
    """Get the last traded price for a ticker."""
    try:
        ltp = market_service.get_ltp(ticker, exchange)
        return LTPResponse(ticker=ticker, ltp=ltp, exchange=exchange)
    except Exception as e:
        logger.error("Error fetching LTP for %s: %s", ticker, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch LTP: {e}")


@router.get("/historical/{ticker}", response_model=HistoricalResponse)
async def get_historical(
    ticker: str,
    duration: str = Query("30", description="Duration in days or period string"),
    interval: str = Query("ONE_DAY", description="Candle interval"),
    exchange: str = Query("NSE"),
):
    """Get historical OHLCV data for a ticker."""
    try:
        df = market_service.get_historical_data(
            ticker=ticker,
            duration_days=int(duration),
            interval=interval,
            exchange=exchange,
        )
        bars = [
            HistoricalBar(
                timestamp=str(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for _, row in df.iterrows()
        ]
        return HistoricalResponse(ticker=ticker, bars=bars, count=len(bars))
    except Exception as e:
        logger.error("Error fetching historical data for %s: %s", ticker, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch historical data: {e}"
        )


@router.get("/instruments/search", response_model=list[InstrumentResult])
async def search_instruments(
    query: str = Query(..., min_length=1, description="Search term"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search instruments by name or symbol."""
    try:
        results = instrument_service.search_instruments(
            query=query, exchange=exchange, limit=limit
        )
        return [
            InstrumentResult(
                symbol=r.get("symbol", ""),
                token=str(r.get("token", "")),
                name=r.get("name", ""),
                exchange=r.get("exch_seg", ""),
                instrument_type=r.get("instrumenttype"),
                lot_size=r.get("lotsize"),
            )
            for r in results
        ]
    except Exception as e:
        logger.error("Error searching instruments: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Instrument search failed: {e}"
        )
