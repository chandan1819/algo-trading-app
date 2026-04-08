"""Dashboard data API routes."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_session
from backend.models.models import DailyPnL, Trade
from backend.services.risk_manager import RiskManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

risk_manager = RiskManager()


class DailyPnLResponse(BaseModel):
    date: str
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    max_drawdown: float


class OverallStats(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    profitable_days: int
    loss_days: int
    avg_daily_pnl: float
    max_drawdown: float
    best_day: float
    worst_day: float


class TradeLogEntry(BaseModel):
    id: int
    order_id: str
    ticker: str
    transaction_type: str
    quantity: int
    price: float
    strategy_name: str | None = None
    executed_at: str


class TradeLogResponse(BaseModel):
    trades: list[TradeLogEntry]
    total: int
    page: int
    page_size: int


class RiskStatus(BaseModel):
    can_trade: bool
    daily_loss_used: float
    daily_loss_limit: float
    daily_loss_pct: float
    trades_today: int
    max_trades_per_day: int
    max_drawdown_pct: float
    capital_per_trade: float


@router.get("/pnl", response_model=list[DailyPnLResponse])
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365, description="Number of past days"),
    session: AsyncSession = Depends(get_session),
):
    """Get daily PnL summary for the past N days."""
    try:
        since = date.today() - timedelta(days=days)
        result = await session.execute(
            select(DailyPnL)
            .where(DailyPnL.date >= since)
            .order_by(DailyPnL.date.desc())
        )
        records = result.scalars().all()
        return [
            DailyPnLResponse(
                date=str(r.date),
                realized_pnl=r.realized_pnl,
                unrealized_pnl=r.unrealized_pnl,
                total_trades=r.total_trades,
                max_drawdown=r.max_drawdown,
            )
            for r in records
        ]
    except Exception as e:
        logger.error("Error fetching PnL data: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch PnL data: {e}")


@router.get("/stats", response_model=OverallStats)
async def get_overall_stats(session: AsyncSession = Depends(get_session)):
    """Get overall trading statistics."""
    try:
        result = await session.execute(select(DailyPnL))
        records = result.scalars().all()

        if not records:
            return OverallStats(
                total_trades=0,
                total_pnl=0.0,
                win_rate=0.0,
                profitable_days=0,
                loss_days=0,
                avg_daily_pnl=0.0,
                max_drawdown=0.0,
                best_day=0.0,
                worst_day=0.0,
            )

        total_trades = sum(r.total_trades for r in records)
        total_pnl = sum(r.realized_pnl for r in records)
        profitable_days = sum(1 for r in records if r.realized_pnl > 0)
        loss_days = sum(1 for r in records if r.realized_pnl < 0)
        pnl_values = [r.realized_pnl for r in records]
        drawdowns = [r.max_drawdown for r in records]

        return OverallStats(
            total_trades=total_trades,
            total_pnl=round(total_pnl, 2),
            win_rate=round(profitable_days / len(records) * 100, 2) if records else 0.0,
            profitable_days=profitable_days,
            loss_days=loss_days,
            avg_daily_pnl=round(total_pnl / len(records), 2) if records else 0.0,
            max_drawdown=round(min(drawdowns), 2) if drawdowns else 0.0,
            best_day=round(max(pnl_values), 2),
            worst_day=round(min(pnl_values), 2),
        )
    except Exception as e:
        logger.error("Error fetching stats: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {e}")


@router.get("/trade-log", response_model=TradeLogResponse)
async def get_trade_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ticker: str | None = Query(None),
    strategy: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Get paginated trade log."""
    try:
        query = select(Trade)

        if ticker:
            query = query.where(Trade.ticker == ticker)
        if strategy:
            query = query.where(Trade.strategy_name == strategy)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = (
            query.order_by(desc(Trade.executed_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(query)
        trades = result.scalars().all()

        return TradeLogResponse(
            trades=[
                TradeLogEntry(
                    id=t.id,
                    order_id=t.order_id,
                    ticker=t.ticker,
                    transaction_type=t.transaction_type,
                    quantity=t.quantity,
                    price=t.price,
                    strategy_name=t.strategy_name,
                    executed_at=t.executed_at.isoformat(),
                )
                for t in trades
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error("Error fetching trade log: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch trade log: {e}"
        )


@router.get("/risk-status", response_model=RiskStatus)
async def get_risk_status():
    """Get current risk management status."""
    try:
        can_trade_ok, _ = risk_manager.can_trade()
        state = risk_manager.state
        daily_loss_abs = abs(state.daily_pnl) if state.daily_pnl < 0 else 0.0
        daily_loss_pct = (
            (daily_loss_abs / settings.MAX_LOSS_PER_DAY * 100)
            if settings.MAX_LOSS_PER_DAY > 0
            else 0.0
        )

        return RiskStatus(
            can_trade=can_trade_ok,
            daily_loss_used=round(daily_loss_abs, 2),
            daily_loss_limit=settings.MAX_LOSS_PER_DAY,
            daily_loss_pct=round(daily_loss_pct, 2),
            trades_today=state.trade_count,
            max_trades_per_day=settings.MAX_TRADES_PER_DAY,
            max_drawdown_pct=settings.MAX_DRAWDOWN_PCT,
            capital_per_trade=settings.CAPITAL_PER_TRADE,
        )
    except Exception as e:
        logger.error("Error fetching risk status: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch risk status: {e}"
        )
