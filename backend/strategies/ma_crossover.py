"""Moving Average Crossover Strategy.

Generates BUY when the fast EMA crosses above the slow EMA
and SELL when the fast EMA crosses below the slow EMA.
"""

import pandas as pd

from .base_strategy import BaseStrategy, Signal, TradeSignal
from .indicators import EMA, ATR


class MACrossoverStrategy(BaseStrategy):
    def __init__(self, params: dict | None = None):
        defaults = self.get_default_params()
        if params:
            defaults.update(params)
        super().__init__("ma_crossover", defaults)

    def get_default_params(self) -> dict:
        return {
            "fast_period": 9,
            "slow_period": 21,
            "atr_period": 14,
            "atr_sl_multiplier": 1.5,
            "risk_reward_ratio": 2.0,
        }

    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        if len(df) < self.params["slow_period"] + 2:
            return self._hold(ticker, df)

        fast_ema = EMA(df["close"], self.params["fast_period"])
        slow_ema = EMA(df["close"], self.params["slow_period"])
        atr = ATR(df, self.params["atr_period"])

        curr_fast = fast_ema.iloc[-1]
        prev_fast = fast_ema.iloc[-2]
        curr_slow = slow_ema.iloc[-1]
        prev_slow = slow_ema.iloc[-2]
        curr_atr = atr.iloc[-1]
        price = df["close"].iloc[-1]

        # Crossover detection: current above AND previous below or equal
        if curr_fast > curr_slow and prev_fast <= prev_slow:
            # BUY signal - bullish crossover
            swing_low = df["low"].iloc[-self.params["slow_period"]:].min()
            atr_stop = price - self.params["atr_sl_multiplier"] * curr_atr
            stop_loss = max(swing_low, atr_stop) if pd.notna(curr_atr) else swing_low

            risk = price - stop_loss
            target = price + risk * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.BUY,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason=f"Fast EMA({self.params['fast_period']}) crossed above Slow EMA({self.params['slow_period']})",
            )

        elif curr_fast < curr_slow and prev_fast >= prev_slow:
            # SELL signal - bearish crossover
            swing_high = df["high"].iloc[-self.params["slow_period"]:].max()
            atr_stop = price + self.params["atr_sl_multiplier"] * curr_atr
            stop_loss = min(swing_high, atr_stop) if pd.notna(curr_atr) else swing_high

            risk = stop_loss - price
            target = price - risk * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.SELL,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason=f"Fast EMA({self.params['fast_period']}) crossed below Slow EMA({self.params['slow_period']})",
            )

        return self._hold(ticker, df)

    def _hold(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        price = df["close"].iloc[-1] if len(df) > 0 else 0.0
        return TradeSignal(
            signal=Signal.HOLD,
            ticker=ticker,
            price=price,
            strategy_name=self.name,
            reason="No crossover detected",
        )
