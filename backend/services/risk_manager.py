"""Risk management service for the algo trading application."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Tuple

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RiskState:
    """Mutable daily risk tracking state."""

    daily_pnl: float = 0.0
    trade_count: int = 0
    peak_capital: float = 0.0
    current_capital: float = 0.0


class RiskManager:
    """Enforces risk limits before every trade.

    Tracks daily P&L, trade count, and drawdown against configurable
    thresholds from application settings.
    """

    def __init__(self, initial_capital: float | None = None) -> None:
        capital = initial_capital or settings.CAPITAL_PER_TRADE
        self._state = RiskState(
            peak_capital=capital,
            current_capital=capital,
        )
        self._lock = threading.Lock()

    # ── public checks ─────────────────────────────────────────────────────

    def check_daily_loss_limit(self) -> Tuple[bool, str]:
        """Check whether the daily loss has exceeded MAX_LOSS_PER_DAY.

        Returns:
            (is_within_limit, reason)
        """
        with self._lock:
            if self._state.daily_pnl <= -abs(settings.MAX_LOSS_PER_DAY):
                reason = (
                    f"Daily loss limit breached: PnL={self._state.daily_pnl:.2f}, "
                    f"limit=-{settings.MAX_LOSS_PER_DAY:.2f}"
                )
                logger.warning(reason)
                return False, reason
            return True, "Daily loss within limit."

    def check_trade_count(self) -> Tuple[bool, str]:
        """Check whether the daily trade count has exceeded MAX_TRADES_PER_DAY.

        Returns:
            (is_within_limit, reason)
        """
        with self._lock:
            if self._state.trade_count >= settings.MAX_TRADES_PER_DAY:
                reason = (
                    f"Daily trade count limit reached: {self._state.trade_count}/"
                    f"{settings.MAX_TRADES_PER_DAY}"
                )
                logger.warning(reason)
                return False, reason
            return True, "Trade count within limit."

    def check_drawdown(self) -> Tuple[bool, str]:
        """Check whether the portfolio drawdown exceeds MAX_DRAWDOWN_PCT.

        Returns:
            (is_within_limit, reason)
        """
        with self._lock:
            if self._state.peak_capital <= 0:
                return True, "No capital tracked yet."

            drawdown_pct = (
                (self._state.peak_capital - self._state.current_capital)
                / self._state.peak_capital
                * 100
            )

            if drawdown_pct >= settings.MAX_DRAWDOWN_PCT:
                reason = (
                    f"Max drawdown breached: {drawdown_pct:.2f}% >= "
                    f"{settings.MAX_DRAWDOWN_PCT:.2f}%"
                )
                logger.warning(reason)
                return False, reason
            return True, f"Drawdown at {drawdown_pct:.2f}%."

    def can_trade(self) -> Tuple[bool, str]:
        """Composite risk check -- returns (allowed, reason).

        Runs all individual checks and returns False with the first
        failing reason, or True if all pass.
        """
        checks = [
            self.check_daily_loss_limit,
            self.check_trade_count,
            self.check_drawdown,
        ]
        for check in checks:
            ok, reason = check()
            if not ok:
                return False, reason
        return True, "All risk checks passed."

    # ── state updates ─────────────────────────────────────────────────────

    def update_daily_pnl(self, pnl: float) -> None:
        """Add a realized P&L amount to the daily tally and update capital.

        Args:
            pnl: Profit (positive) or loss (negative) from a trade.
        """
        with self._lock:
            self._state.daily_pnl += pnl
            self._state.trade_count += 1
            self._state.current_capital += pnl

            if self._state.current_capital > self._state.peak_capital:
                self._state.peak_capital = self._state.current_capital

            logger.info(
                "PnL updated: trade_pnl=%.2f, daily_pnl=%.2f, "
                "trades=%d, capital=%.2f, peak=%.2f",
                pnl,
                self._state.daily_pnl,
                self._state.trade_count,
                self._state.current_capital,
                self._state.peak_capital,
            )

    def reset_daily_counters(self) -> None:
        """Reset daily P&L and trade count -- call at market open."""
        with self._lock:
            self._state.daily_pnl = 0.0
            self._state.trade_count = 0
            logger.info("Daily risk counters reset.")

    # ── position sizing ───────────────────────────────────────────────────

    @staticmethod
    def calculate_position_size(
        capital: float,
        risk_per_trade: float,
        stop_loss_pct: float,
    ) -> int:
        """Calculate the number of shares to trade using fixed-fractional sizing.

        Uses a simplified Kelly-criterion-inspired approach:
            risk_amount = capital * risk_per_trade
            position_size = risk_amount / (price * stop_loss_pct)

        Since we don't have the price here, we return the rupee risk amount
        divided by the stop-loss percentage to get the max position value,
        then the caller divides by the share price.

        Args:
            capital: Available trading capital.
            risk_per_trade: Fraction of capital to risk (e.g. 0.02 for 2%).
            stop_loss_pct: Stop-loss distance as a fraction (e.g. 0.01 for 1%).

        Returns:
            Maximum position value (in currency units). Divide by share price
            to get the number of shares.
        """
        if stop_loss_pct <= 0:
            logger.warning("stop_loss_pct must be > 0; returning 0.")
            return 0
        if risk_per_trade <= 0:
            return 0

        risk_amount = capital * risk_per_trade
        position_value = risk_amount / stop_loss_pct
        qty = int(position_value // 1)  # floor to integer
        logger.debug(
            "Position size: capital=%.2f, risk=%.4f, sl=%.4f -> value=%.2f, qty=%d",
            capital,
            risk_per_trade,
            stop_loss_pct,
            position_value,
            qty,
        )
        return qty

    # ── accessors ─────────────────────────────────────────────────────────

    @property
    def state(self) -> RiskState:
        return self._state
