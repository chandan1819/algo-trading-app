"""Support/Resistance Breakout Strategy.

Identifies support and resistance levels from historical price action.
BUY when price breaks above resistance with volume surge.
SELL when price breaks below support with volume surge.
Confirms breakout using close price (not wicks).
"""

from __future__ import annotations

import pandas as pd

from .base_strategy import BaseStrategy, Signal, TradeSignal
from .indicators import support_resistance_levels, ATR, SMA


class BreakoutStrategy(BaseStrategy):
    def __init__(self, params: dict | None = None):
        defaults = self.get_default_params()
        if params:
            defaults.update(params)
        super().__init__("sr_breakout", defaults)

    def get_default_params(self) -> dict:
        return {
            "lookback": 20,
            "volume_avg_period": 20,
            "volume_surge_multiplier": 1.5,
            "atr_period": 14,
            "sl_buffer_pct": 0.002,  # 0.2% buffer below broken level for stop loss
            "risk_reward_ratio": 2.0,
            "proximity_pct": 0.005,  # price must be within 0.5% of level to count
        }

    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        min_bars = self.params["lookback"] * 2 + 2
        if len(df) < min_bars:
            return self._hold(ticker, df)

        supports, resistances = support_resistance_levels(df, self.params["lookback"])
        atr = ATR(df, self.params["atr_period"])
        avg_volume = SMA(df["volume"], self.params["volume_avg_period"])

        price = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        curr_atr = atr.iloc[-1]
        curr_volume = df["volume"].iloc[-1]
        curr_avg_vol = avg_volume.iloc[-1]

        volume_surge = (
            pd.notna(curr_avg_vol)
            and curr_avg_vol > 0
            and curr_volume > curr_avg_vol * self.params["volume_surge_multiplier"]
        )

        # Check resistance breakout (BUY)
        for resistance in resistances:
            # Close above resistance now, close was at or below previously
            broke_above = price > resistance and prev_close <= resistance

            # Also check proximity: previous close was near resistance
            near_resistance = (
                abs(prev_close - resistance) / resistance <= self.params["proximity_pct"]
                or prev_close < resistance
            )

            if broke_above and near_resistance and volume_surge:
                buffer = resistance * self.params["sl_buffer_pct"]
                stop_loss = resistance - buffer
                risk = price - stop_loss
                target = price + risk * self.params["risk_reward_ratio"]

                return TradeSignal(
                    signal=Signal.BUY,
                    ticker=ticker,
                    price=price,
                    stop_loss=round(stop_loss, 2),
                    target=round(target, 2),
                    strategy_name=self.name,
                    reason=f"Breakout above resistance {resistance:.2f} with volume surge",
                )

        # Check support breakdown (SELL)
        for support in reversed(supports):
            broke_below = price < support and prev_close >= support

            near_support = (
                abs(prev_close - support) / support <= self.params["proximity_pct"]
                or prev_close > support
            )

            if broke_below and near_support and volume_surge:
                buffer = support * self.params["sl_buffer_pct"]
                stop_loss = support + buffer
                risk = stop_loss - price
                target = price - risk * self.params["risk_reward_ratio"]

                return TradeSignal(
                    signal=Signal.SELL,
                    ticker=ticker,
                    price=price,
                    stop_loss=round(stop_loss, 2),
                    target=round(target, 2),
                    strategy_name=self.name,
                    reason=f"Breakdown below support {support:.2f} with volume surge",
                )

        return self._hold(ticker, df)

    def _hold(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        price = df["close"].iloc[-1] if len(df) > 0 else 0.0
        return TradeSignal(
            signal=Signal.HOLD,
            ticker=ticker,
            price=price,
            strategy_name=self.name,
            reason="No S/R breakout detected",
        )
