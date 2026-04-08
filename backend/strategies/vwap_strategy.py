"""VWAP Intraday Strategy.

BUY when price crosses above VWAP with above-average volume.
SELL when price crosses below VWAP.
Only trades during NSE market hours (9:15 AM - 3:15 PM IST).
Exits all positions before 3:15 PM.
"""

from __future__ import annotations

import pandas as pd
from datetime import time

from .base_strategy import BaseStrategy, Signal, TradeSignal
from .indicators import VWAP, ATR, SMA


# NSE market hours in IST
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
EXIT_CUTOFF = time(15, 15)


class VWAPStrategy(BaseStrategy):
    def __init__(self, params: dict | None = None):
        defaults = self.get_default_params()
        if params:
            defaults.update(params)
        super().__init__("vwap_intraday", defaults)

    def get_default_params(self) -> dict:
        return {
            "volume_avg_period": 20,
            "volume_multiplier": 1.2,
            "atr_period": 14,
            "atr_sl_multiplier": 1.5,
            "risk_reward_ratio": 2.0,
        }

    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        if len(df) < self.params["volume_avg_period"] + 2:
            return self._hold(ticker, df)

        price = df["close"].iloc[-1]

        # Check market hours if datetime index is available
        if isinstance(df.index, pd.DatetimeIndex):
            current_time = df.index[-1].time()

            if current_time < MARKET_OPEN or current_time > MARKET_CLOSE:
                return TradeSignal(
                    signal=Signal.HOLD,
                    ticker=ticker,
                    price=price,
                    strategy_name=self.name,
                    reason="Outside market hours",
                )

            # Exit before 3:15 PM
            if current_time >= EXIT_CUTOFF:
                return TradeSignal(
                    signal=Signal.SELL,
                    ticker=ticker,
                    price=price,
                    strategy_name=self.name,
                    reason="End-of-day exit before 3:15 PM IST",
                )

        vwap = VWAP(df)
        atr = ATR(df, self.params["atr_period"])
        avg_volume = SMA(df["volume"], self.params["volume_avg_period"])

        curr_vwap = vwap.iloc[-1]
        prev_vwap = vwap.iloc[-2]
        curr_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]
        curr_atr = atr.iloc[-1]
        curr_volume = df["volume"].iloc[-1]
        curr_avg_vol = avg_volume.iloc[-1]

        if pd.isna(curr_vwap) or pd.isna(prev_vwap):
            return self._hold(ticker, df)

        volume_ok = (
            pd.notna(curr_avg_vol)
            and curr_avg_vol > 0
            and curr_volume > curr_avg_vol * self.params["volume_multiplier"]
        )

        sl_distance = self.params["atr_sl_multiplier"] * curr_atr if pd.notna(curr_atr) else price * 0.01

        # BUY: price crosses above VWAP with volume confirmation
        crossed_above = curr_close > curr_vwap and prev_close <= prev_vwap
        if crossed_above and volume_ok:
            stop_loss = price - sl_distance
            target = price + sl_distance * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.BUY,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason="Price crossed above VWAP with above-average volume",
            )

        # SELL: price crosses below VWAP
        crossed_below = curr_close < curr_vwap and prev_close >= prev_vwap
        if crossed_below:
            stop_loss = price + sl_distance
            target = price - sl_distance * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.SELL,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason="Price crossed below VWAP",
            )

        return self._hold(ticker, df)

    def _hold(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        price = df["close"].iloc[-1] if len(df) > 0 else 0.0
        return TradeSignal(
            signal=Signal.HOLD,
            ticker=ticker,
            price=price,
            strategy_name=self.name,
            reason="No VWAP crossover detected",
        )
