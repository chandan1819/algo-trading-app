"""Strategy management API routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.models.models import StrategyConfig
from backend.strategies.base_strategy import Signal
from backend.strategies.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/strategies", tags=["strategies"])

strategy_engine = StrategyEngine()


class StrategyStatus(BaseModel):
    name: str
    enabled: bool
    parameters: dict[str, Any]


class ToggleResponse(BaseModel):
    name: str
    enabled: bool
    message: str


class UpdateConfigRequest(BaseModel):
    parameters: dict[str, Any]


class RunResponse(BaseModel):
    status: str
    message: str
    signals_generated: int


class SignalDetail(BaseModel):
    signal: str
    ticker: str
    price: float
    stop_loss: float | None = None
    target: float | None = None
    strategy_name: str
    reason: str
    quantity: int


@router.get("", response_model=list[StrategyStatus])
async def list_strategies(session: AsyncSession = Depends(get_session)):
    """List all strategies with their current status."""
    try:
        result = await session.execute(select(StrategyConfig))
        configs = result.scalars().all()

        strategies = []
        for cfg in configs:
            strategies.append(
                StrategyStatus(
                    name=cfg.name,
                    enabled=cfg.enabled,
                    parameters=cfg.parameters,
                )
            )

        # Include loaded strategies that may not be in the database yet
        loaded = strategy_engine.load_strategies()
        db_names = {s.name for s in strategies}
        for name in loaded:
            if name not in db_names:
                strategies.append(
                    StrategyStatus(name=name, enabled=False, parameters={})
                )

        return strategies
    except Exception as e:
        logger.error("Error listing strategies: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to list strategies: {e}"
        )


@router.put("/{name}/toggle", response_model=ToggleResponse)
async def toggle_strategy(name: str, session: AsyncSession = Depends(get_session)):
    """Enable or disable a strategy."""
    try:
        result = await session.execute(
            select(StrategyConfig).where(StrategyConfig.name == name)
        )
        config = result.scalar_one_or_none()

        if config is None:
            config = StrategyConfig(name=name, enabled=True, parameters={})
            session.add(config)
        else:
            config.enabled = not config.enabled

        await session.flush()

        return ToggleResponse(
            name=name,
            enabled=config.enabled,
            message=f"Strategy '{name}' {'enabled' if config.enabled else 'disabled'}",
        )
    except Exception as e:
        logger.error("Error toggling strategy %s: %s", name, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle strategy: {e}"
        )


@router.put("/{name}/config", response_model=StrategyStatus)
async def update_strategy_config(
    name: str,
    request: UpdateConfigRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update strategy parameters."""
    try:
        result = await session.execute(
            select(StrategyConfig).where(StrategyConfig.name == name)
        )
        config = result.scalar_one_or_none()

        if config is None:
            config = StrategyConfig(
                name=name, enabled=False, parameters=request.parameters
            )
            session.add(config)
        else:
            config.parameters = {**config.parameters, **request.parameters}

        await session.flush()

        return StrategyStatus(
            name=config.name,
            enabled=config.enabled,
            parameters=config.parameters,
        )
    except Exception as e:
        logger.error("Error updating strategy config for %s: %s", name, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update strategy config: {e}"
        )


@router.post("/run", response_model=RunResponse)
async def run_strategies():
    """Manually trigger a strategy run cycle."""
    try:
        signals = strategy_engine.run_strategies()
        return RunResponse(
            status="success",
            message="Strategy run completed",
            signals_generated=len(signals) if signals else 0,
        )
    except Exception as e:
        logger.error("Error running strategies: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Strategy run failed: {e}"
        )


@router.get("/signals", response_model=list[SignalDetail])
async def get_recent_signals():
    """Get recent trading signals generated by strategies."""
    try:
        signals = strategy_engine.run_strategies()
        if not signals:
            return []
        return [
            SignalDetail(
                signal=s.signal.value,
                ticker=s.ticker,
                price=s.price,
                stop_loss=s.stop_loss,
                target=s.target,
                strategy_name=s.strategy_name,
                reason=s.reason,
                quantity=s.quantity,
            )
            for s in signals
            if s.signal != Signal.HOLD
        ]
    except Exception as e:
        logger.error("Error fetching signals: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch signals: {e}"
        )
