"""Backtesting engine for simulating strategy performance on historical data."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from backend.services.market_data import MarketDataService
from backend.strategies.base_strategy import BaseStrategy, Signal, TradeSignal
from backend.strategies.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)

# Risk-free rate for India (annualized)
RISK_FREE_RATE = 0.06
TRADING_DAYS_PER_YEAR = 252


@dataclass
class BacktestTrade:
    """A single completed round-trip trade in the backtest."""

    entry_date: str
    exit_date: str
    ticker: str
    side: str  # BUY or SELL
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float = 0.0
    return_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_date": self.entry_date,
            "exit_date": self.exit_date,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 2),
            "exit_price": round(self.exit_price, 2),
            "pnl": round(self.pnl, 2),
            "return_pct": round(self.return_pct, 4),
        }


class BacktestEngine:
    """Simulates strategy execution on historical OHLCV data.

    Runs a strategy's signal generation over each bar of historical data,
    simulates order fills at the close price, and computes performance metrics.
    """

    def __init__(self) -> None:
        self._market_service = MarketDataService()
        self._strategy_engine = StrategyEngine()

    async def run(
        self,
        strategy_name: str,
        ticker: str,
        start_date: date,
        end_date: date,
        initial_capital: float = 100_000.0,
        params: dict[str, Any] | None = None,
        exchange: str = "NSE",
    ) -> dict[str, Any]:
        """Run a full backtest and return results with metrics.

        Args:
            strategy_name: Name of the strategy to backtest.
            ticker: Trading symbol.
            start_date: Backtest start date.
            end_date: Backtest end date.
            initial_capital: Starting capital.
            params: Strategy-specific parameter overrides.
            exchange: Exchange code (default NSE).

        Returns:
            Dict with keys: metrics, equity_curve, trades.

        Raises:
            ValueError: If strategy not found or no data available.
        """
        params = params or {}

        # Resolve the strategy
        strategy = self._resolve_strategy(strategy_name, params)

        # Fetch historical data
        df = self._fetch_data(ticker, start_date, end_date, exchange)
        if df.empty:
            raise ValueError(
                f"No historical data available for {ticker} "
                f"between {start_date} and {end_date}"
            )

        # Simulate
        trades, equity_curve = self._simulate(strategy, df, ticker, initial_capital)

        # Calculate metrics
        metrics = self._calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": [t.to_dict() for t in trades],
        }

    def _resolve_strategy(
        self, strategy_name: str, params: dict[str, Any]
    ) -> BaseStrategy:
        """Load the strategy by name."""
        strategies = self._strategy_engine.load_strategies()
        if not strategies or strategy_name not in strategies:
            raise ValueError(
                f"Strategy '{strategy_name}' not found. "
                f"Available: {list(strategies.keys()) if strategies else []}"
            )

        strategy = strategies[strategy_name]
        if params:
            strategy.update_params(params)
        return strategy

    def _fetch_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        exchange: str,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data and return as a DataFrame."""
        delta_days = (end_date - start_date).days
        raw_data = self._market_service.get_historical_data(
            ticker=ticker,
            duration=str(delta_days),
            interval="ONE_DAY",
            exchange=exchange,
        )

        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(
            raw_data,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df["volume"] = df["volume"].astype(int)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def _simulate(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        ticker: str,
        initial_capital: float,
    ) -> tuple[list[BacktestTrade], list[dict[str, Any]]]:
        """Walk through the data bar-by-bar and simulate trades.

        Returns:
            Tuple of (completed_trades, equity_curve_points).
        """
        capital = initial_capital
        position: dict[str, Any] | None = None  # {side, quantity, entry_price, entry_date}
        trades: list[BacktestTrade] = []
        equity_curve: list[dict[str, Any]] = []
        peak_equity = initial_capital

        for i in range(1, len(df)):
            # Feed the strategy a slice up to the current bar
            window = df.iloc[: i + 1].copy()
            current_bar = df.iloc[i]
            current_date = str(current_bar["timestamp"].date())
            close_price = float(current_bar["close"])

            signal = strategy.generate_signal(window, ticker)

            # Process signals
            if position is None:
                # No position -- look for entry
                if signal.signal == Signal.BUY:
                    qty = signal.quantity if signal.quantity > 0 else max(
                        1, int(capital * 0.95 / close_price)
                    )
                    position = {
                        "side": "BUY",
                        "quantity": qty,
                        "entry_price": close_price,
                        "entry_date": current_date,
                    }
                elif signal.signal == Signal.SELL:
                    qty = signal.quantity if signal.quantity > 0 else max(
                        1, int(capital * 0.95 / close_price)
                    )
                    position = {
                        "side": "SELL",
                        "quantity": qty,
                        "entry_price": close_price,
                        "entry_date": current_date,
                    }
            else:
                # In position -- check for exit
                should_exit = False
                if position["side"] == "BUY" and signal.signal == Signal.SELL:
                    should_exit = True
                elif position["side"] == "SELL" and signal.signal == Signal.BUY:
                    should_exit = True

                # Check stop loss
                if not should_exit and signal.stop_loss is not None:
                    if position["side"] == "BUY" and close_price <= signal.stop_loss:
                        should_exit = True
                    elif position["side"] == "SELL" and close_price >= signal.stop_loss:
                        should_exit = True

                # Check target
                if not should_exit and signal.target is not None:
                    if position["side"] == "BUY" and close_price >= signal.target:
                        should_exit = True
                    elif position["side"] == "SELL" and close_price <= signal.target:
                        should_exit = True

                if should_exit:
                    if position["side"] == "BUY":
                        pnl = (close_price - position["entry_price"]) * position["quantity"]
                    else:
                        pnl = (position["entry_price"] - close_price) * position["quantity"]

                    return_pct = pnl / (position["entry_price"] * position["quantity"])
                    capital += pnl

                    trades.append(
                        BacktestTrade(
                            entry_date=position["entry_date"],
                            exit_date=current_date,
                            ticker=ticker,
                            side=position["side"],
                            quantity=position["quantity"],
                            entry_price=position["entry_price"],
                            exit_price=close_price,
                            pnl=pnl,
                            return_pct=return_pct,
                        )
                    )
                    position = None

            # Compute current equity
            unrealized = 0.0
            if position is not None:
                if position["side"] == "BUY":
                    unrealized = (close_price - position["entry_price"]) * position["quantity"]
                else:
                    unrealized = (position["entry_price"] - close_price) * position["quantity"]

            equity = capital + unrealized
            peak_equity = max(peak_equity, equity)
            drawdown = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0

            equity_curve.append(
                {
                    "date": current_date,
                    "equity": round(equity, 2),
                    "drawdown": round(drawdown, 4),
                }
            )

        # Close any open position at the last bar
        if position is not None:
            close_price = float(df.iloc[-1]["close"])
            current_date = str(df.iloc[-1]["timestamp"].date())

            if position["side"] == "BUY":
                pnl = (close_price - position["entry_price"]) * position["quantity"]
            else:
                pnl = (position["entry_price"] - close_price) * position["quantity"]

            return_pct = pnl / (position["entry_price"] * position["quantity"])
            capital += pnl

            trades.append(
                BacktestTrade(
                    entry_date=position["entry_date"],
                    exit_date=current_date,
                    ticker=ticker,
                    side=position["side"],
                    quantity=position["quantity"],
                    entry_price=position["entry_price"],
                    exit_price=close_price,
                    pnl=pnl,
                    return_pct=return_pct,
                )
            )

        return trades, equity_curve

    def _calculate_metrics(
        self,
        trades: list[BacktestTrade],
        equity_curve: list[dict[str, Any]],
        initial_capital: float,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Calculate comprehensive backtest performance metrics."""
        final_capital = equity_curve[-1]["equity"] if equity_curve else initial_capital
        net_profit = final_capital - initial_capital
        total_trades = len(trades)

        # CAGR
        years = max((end_date - start_date).days / 365.25, 1 / 365.25)
        if final_capital > 0 and initial_capital > 0:
            cagr = (final_capital / initial_capital) ** (1 / years) - 1
        else:
            cagr = 0.0

        # Daily returns for Sharpe calculation
        if len(equity_curve) >= 2:
            equities = [initial_capital] + [pt["equity"] for pt in equity_curve]
            daily_returns = np.diff(equities) / equities[:-1]
            daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR

            excess_returns = daily_returns - daily_rf
            if np.std(excess_returns) > 0:
                sharpe_ratio = (
                    np.mean(excess_returns) / np.std(excess_returns)
                ) * math.sqrt(TRADING_DAYS_PER_YEAR)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Max drawdown
        max_drawdown = 0.0
        if equity_curve:
            max_drawdown = max(pt["drawdown"] for pt in equity_curve)

        # Win rate
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

        # Average win/loss ratio
        avg_win = (gross_profit / len(winning_trades)) if winning_trades else 0.0
        avg_loss = (gross_loss / len(losing_trades)) if losing_trades else 0.0
        avg_win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else float("inf") if avg_win > 0 else 0.0

        # Cap inf values for JSON serialization
        if math.isinf(profit_factor):
            profit_factor = 999.99
        if math.isinf(avg_win_loss_ratio):
            avg_win_loss_ratio = 999.99

        return {
            "cagr": round(cagr * 100, 4),
            "sharpe_ratio": round(float(sharpe_ratio), 4),
            "max_drawdown": round(max_drawdown, 4),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 4),
            "avg_win_loss_ratio": round(avg_win_loss_ratio, 4),
            "total_trades": total_trades,
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(final_capital, 2),
            "net_profit": round(net_profit, 2),
            "net_profit_pct": round(net_profit / initial_capital * 100, 4) if initial_capital > 0 else 0.0,
        }
