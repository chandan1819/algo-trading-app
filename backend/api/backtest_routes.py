"""Backtesting API routes."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.backtesting.engine import BacktestEngine
from backend.core.database import get_session
from backend.models.models import BacktestResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy_name: str
    ticker: str
    start_date: date
    end_date: date
    initial_capital: float = Field(100000.0, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)
    exchange: str = "NSE"


class BacktestMetrics(BaseModel):
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_win_loss_ratio: float
    total_trades: int
    initial_capital: float
    final_capital: float
    net_profit: float
    net_profit_pct: float


class EquityPoint(BaseModel):
    date: str
    equity: float
    drawdown: float


class BacktestTradeDetail(BaseModel):
    entry_date: str
    exit_date: str
    ticker: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float


class BacktestResponse(BaseModel):
    id: Optional[int] = None
    strategy_name: str
    ticker: str
    start_date: str
    end_date: str
    metrics: BacktestMetrics
    equity_curve: list[EquityPoint]
    trades: list[BacktestTradeDetail]


class BacktestSummary(BaseModel):
    id: int
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    created_at: str


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    session: AsyncSession = Depends(get_session),
):
    """Run a backtest for a given strategy and ticker."""
    try:
        engine = BacktestEngine()
        result = await engine.run(
            strategy_name=request.strategy_name,
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            params=request.params,
            exchange=request.exchange,
        )

        # Persist result to database
        db_result = BacktestResult(
            strategy_name=request.strategy_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_capital=result["metrics"]["final_capital"],
            cagr=result["metrics"]["cagr"],
            sharpe_ratio=result["metrics"]["sharpe_ratio"],
            max_drawdown=result["metrics"]["max_drawdown"],
            win_rate=result["metrics"]["win_rate"],
            total_trades=result["metrics"]["total_trades"],
            parameters=request.params,
        )
        session.add(db_result)
        await session.flush()

        return BacktestResponse(
            id=db_result.id,
            strategy_name=request.strategy_name,
            ticker=request.ticker,
            start_date=str(request.start_date),
            end_date=str(request.end_date),
            metrics=BacktestMetrics(**result["metrics"]),
            equity_curve=[EquityPoint(**pt) for pt in result["equity_curve"]],
            trades=[BacktestTradeDetail(**t) for t in result["trades"]],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Backtest failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")


@router.get("/results", response_model=list[BacktestSummary])
async def list_backtest_results(session: AsyncSession = Depends(get_session)):
    """List all past backtest results."""
    try:
        result = await session.execute(
            select(BacktestResult).order_by(desc(BacktestResult.created_at))
        )
        records = result.scalars().all()
        return [
            BacktestSummary(
                id=r.id,
                strategy_name=r.strategy_name,
                start_date=str(r.start_date),
                end_date=str(r.end_date),
                initial_capital=r.initial_capital,
                final_capital=r.final_capital,
                cagr=r.cagr,
                sharpe_ratio=r.sharpe_ratio,
                max_drawdown=r.max_drawdown,
                win_rate=r.win_rate,
                total_trades=r.total_trades,
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ]
    except Exception as e:
        logger.error("Error fetching backtest results: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch backtest results: {e}"
        )


@router.get("/results/{result_id}", response_model=BacktestSummary)
async def get_backtest_result(
    result_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific backtest result by ID."""
    try:
        result = await session.execute(
            select(BacktestResult).where(BacktestResult.id == result_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Backtest result not found")

        return BacktestSummary(
            id=record.id,
            strategy_name=record.strategy_name,
            start_date=str(record.start_date),
            end_date=str(record.end_date),
            initial_capital=record.initial_capital,
            final_capital=record.final_capital,
            cagr=record.cagr,
            sharpe_ratio=record.sharpe_ratio,
            max_drawdown=record.max_drawdown,
            win_rate=record.win_rate,
            total_trades=record.total_trades,
            created_at=record.created_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching backtest result %d: %s", result_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch backtest result: {e}"
        )
