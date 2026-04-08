"""Strategy Engine - orchestrates multiple trading strategies.

Loads strategy configurations, manages strategy lifecycle, and runs
all enabled strategies against market data in parallel.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .base_strategy import BaseStrategy, TradeSignal, Signal
from .ma_crossover import MACrossoverStrategy
from .rsi_macd_strategy import RSIMACDStrategy
from .bollinger_breakout import BollingerBreakoutStrategy
from .vwap_strategy import VWAPStrategy
from .breakout_strategy import BreakoutStrategy


logger = logging.getLogger("strategy_engine")

# Registry mapping config names to strategy classes
STRATEGY_CLASSES = {
    "ma_crossover": MACrossoverStrategy,
    "rsi_macd": RSIMACDStrategy,
    "bollinger_breakout": BollingerBreakoutStrategy,
    "vwap_intraday": VWAPStrategy,
    "sr_breakout": BreakoutStrategy,
}


class StrategyEngine:
    """Orchestrates loading, managing, and executing trading strategies."""

    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._enabled: dict[str, bool] = {}

    def load_strategies(self, config_path: str | None = None) -> dict[str, BaseStrategy]:
        """Load strategy configurations from a JSON file or use defaults.

        If no config_path is provided, registers all known strategies with
        default parameters.

        Returns:
            Dict mapping strategy name to its BaseStrategy instance.
        """
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Strategy config not found: {config_path}")

            with open(path) as f:
                config = json.load(f)

            for entry in config.get("strategies", []):
                name = entry["name"]
                params = entry.get("params", {})
                enabled = entry.get("enabled", True)

                strategy_cls = STRATEGY_CLASSES.get(name)
                if strategy_cls is None:
                    logger.warning(f"Unknown strategy '{name}' in config, skipping")
                    continue

                strategy = strategy_cls(params)
                self.register_strategy(name, strategy)
                self._enabled[name] = enabled
                logger.info(f"Loaded strategy '{name}' (enabled={enabled})")
        else:
            # Load all known strategies with defaults
            for name, cls in STRATEGY_CLASSES.items():
                if name not in self._strategies:
                    strategy = cls()
                    self.register_strategy(name, strategy)
                    self._enabled[name] = False

        return self._strategies

    def register_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """Register a strategy instance."""
        self._strategies[name] = strategy
        if name not in self._enabled:
            self._enabled[name] = True
        logger.info(f"Registered strategy: {name}")

    def enable_strategy(self, name: str) -> None:
        """Enable a registered strategy."""
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not registered")
        self._enabled[name] = True

    def disable_strategy(self, name: str) -> None:
        """Disable a registered strategy."""
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not registered")
        self._enabled[name] = False

    def get_strategy_status(self) -> dict[str, dict]:
        """Return status of all registered strategies.

        Returns:
            Dict mapping strategy name to its status info including
            enabled state and parameter values.
        """
        status = {}
        for name, strategy in self._strategies.items():
            status[name] = {
                "enabled": self._enabled.get(name, False),
                "params": strategy.params,
                "strategy_class": type(strategy).__name__,
            }
        return status

    async def run_strategies(
        self, market_data: dict[str, pd.DataFrame]
    ) -> list[TradeSignal]:
        """Run all enabled strategies against provided market data in parallel.

        Args:
            market_data: Dict mapping ticker symbol to its OHLCV DataFrame.

        Returns:
            List of TradeSignal objects from all strategies (excluding HOLD).
        """
        tasks = []

        for name, strategy in self._strategies.items():
            if not self._enabled.get(name, False):
                continue

            for ticker, df in market_data.items():
                tasks.append(
                    self._run_single(strategy, df, ticker)
                )

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Strategy execution error: {result}")
                continue
            if result is not None and result.signal != Signal.HOLD:
                signals.append(result)

        return signals

    async def _run_single(
        self, strategy: BaseStrategy, df: pd.DataFrame, ticker: str
    ) -> Optional[TradeSignal]:
        """Run a single strategy in the event loop's executor to avoid blocking."""
        loop = asyncio.get_event_loop()
        try:
            signal = await loop.run_in_executor(
                None, strategy.generate_signal, df, ticker
            )
            return signal
        except Exception as e:
            logger.error(f"Error running {strategy.name} on {ticker}: {e}")
            raise
