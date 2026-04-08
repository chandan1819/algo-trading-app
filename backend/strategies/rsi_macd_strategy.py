"""RSI + MACD Combined Strategy.

Uses RSI for momentum confirmation and MACD for trend direction.
BUY when RSI is oversold AND MACD line crosses above signal line.
SELL when RSI is overbought AND MACD line crosses below signal line.
"""

import pandas as pd

from .base_strategy import BaseStrategy, Signal, TradeSignal
from .indicators import RSI, MACD, ATR


class RSIMACDStrategy(BaseStrategy):
    def __init__(self, params: dict | None = None):
        defaults = self.get_default_params()
        if params:
            defaults.update(params)
        super().__init__("rsi_macd", defaults)

    def get_default_params(self) -> dict:
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "atr_period": 14,
            "atr_sl_multiplier": 2.0,
            "risk_reward_ratio": 2.0,
        }

    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        min_bars = self.params["macd_slow"] + self.params["macd_signal"] + 2
        if len(df) < min_bars:
            return self._hold(ticker, df)

        rsi = RSI(df["close"], self.params["rsi_period"])
        macd_line, signal_line, _ = MACD(
            df["close"],
            self.params["macd_fast"],
            self.params["macd_slow"],
            self.params["macd_signal"],
        )
        atr = ATR(df, self.params["atr_period"])

        curr_rsi = rsi.iloc[-1]
        curr_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        curr_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        curr_atr = atr.iloc[-1]
        price = df["close"].iloc[-1]

        # Check for NaN values in critical indicators
        if pd.isna(curr_rsi) or pd.isna(curr_macd) or pd.isna(curr_signal) or pd.isna(prev_signal):
            return self._hold(ticker, df)

        # BUY: RSI oversold + MACD bullish crossover
        macd_cross_up = curr_macd > curr_signal and prev_macd <= prev_signal
        if curr_rsi < self.params["rsi_oversold"] and macd_cross_up:
            sl_distance = self.params["atr_sl_multiplier"] * curr_atr if pd.notna(curr_atr) else price * 0.02
            stop_loss = price - sl_distance
            target = price + sl_distance * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.BUY,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason=f"RSI oversold ({curr_rsi:.1f}) + MACD bullish crossover",
            )

        # SELL: RSI overbought + MACD bearish crossover
        macd_cross_down = curr_macd < curr_signal and prev_macd >= prev_signal
        if curr_rsi > self.params["rsi_overbought"] and macd_cross_down:
            sl_distance = self.params["atr_sl_multiplier"] * curr_atr if pd.notna(curr_atr) else price * 0.02
            stop_loss = price + sl_distance
            target = price - sl_distance * self.params["risk_reward_ratio"]

            return TradeSignal(
                signal=Signal.SELL,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason=f"RSI overbought ({curr_rsi:.1f}) + MACD bearish crossover",
            )

        return self._hold(ticker, df)

    def _hold(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        price = df["close"].iloc[-1] if len(df) > 0 else 0.0
        return TradeSignal(
            signal=Signal.HOLD,
            ticker=ticker,
            price=price,
            strategy_name=self.name,
            reason="No RSI+MACD confluence signal",
        )
