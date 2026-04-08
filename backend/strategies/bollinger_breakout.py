"""Bollinger Bands Breakout Strategy.

Supports two modes:
  - Breakout: BUY when price closes above upper band with volume confirmation,
              SELL when price closes below lower band.
  - Mean reversion: BUY at lower band, SELL at upper band.

Includes bandwidth squeeze detection for anticipating breakouts.
"""

import pandas as pd

from .base_strategy import BaseStrategy, Signal, TradeSignal
from .indicators import BollingerBands, ATR, SMA


class BollingerBreakoutStrategy(BaseStrategy):
    def __init__(self, params: dict | None = None):
        defaults = self.get_default_params()
        if params:
            defaults.update(params)
        super().__init__("bollinger_breakout", defaults)

    def get_default_params(self) -> dict:
        return {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "volume_avg_period": 20,
            "volume_surge_multiplier": 1.5,
            "atr_period": 14,
            "atr_sl_multiplier": 1.5,
            "mode": "breakout",  # "breakout" or "mean_reversion"
            "squeeze_threshold": 0.04,  # bandwidth below this signals a squeeze
        }

    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        min_bars = max(self.params["bb_period"], self.params["volume_avg_period"]) + 2
        if len(df) < min_bars:
            return self._hold(ticker, df)

        upper, middle, lower, bandwidth = BollingerBands(
            df["close"], self.params["bb_period"], self.params["bb_std_dev"]
        )
        atr = ATR(df, self.params["atr_period"])
        avg_volume = SMA(df["volume"], self.params["volume_avg_period"])

        price = df["close"].iloc[-1]
        curr_upper = upper.iloc[-1]
        curr_lower = lower.iloc[-1]
        curr_middle = middle.iloc[-1]
        curr_bandwidth = bandwidth.iloc[-1]
        curr_atr = atr.iloc[-1]
        curr_volume = df["volume"].iloc[-1]
        curr_avg_vol = avg_volume.iloc[-1]

        if pd.isna(curr_upper) or pd.isna(curr_lower):
            return self._hold(ticker, df)

        is_squeeze = pd.notna(curr_bandwidth) and curr_bandwidth < self.params["squeeze_threshold"]
        volume_surge = (
            pd.notna(curr_avg_vol)
            and curr_avg_vol > 0
            and curr_volume > curr_avg_vol * self.params["volume_surge_multiplier"]
        )

        if self.params["mode"] == "breakout":
            return self._breakout_signal(
                ticker, price, curr_upper, curr_lower, curr_middle,
                curr_atr, volume_surge, is_squeeze, df,
            )
        else:
            return self._mean_reversion_signal(
                ticker, price, curr_upper, curr_lower, curr_middle,
                curr_atr, df,
            )

    def _breakout_signal(
        self, ticker, price, upper, lower, middle, atr, volume_surge, is_squeeze, df,
    ) -> TradeSignal:
        sl_distance = self.params["atr_sl_multiplier"] * atr if pd.notna(atr) else price * 0.02

        # BUY: close above upper band with volume confirmation
        if price > upper and volume_surge:
            stop_loss = middle
            target = price + (price - stop_loss)

            reason = "Price broke above upper Bollinger Band with volume surge"
            if is_squeeze:
                reason += " (post-squeeze breakout)"

            return TradeSignal(
                signal=Signal.BUY,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason=reason,
            )

        # SELL: close below lower band
        if price < lower:
            stop_loss = middle
            target = price - (stop_loss - price)

            return TradeSignal(
                signal=Signal.SELL,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason="Price broke below lower Bollinger Band",
            )

        # Alert on squeeze (but HOLD)
        if is_squeeze:
            return TradeSignal(
                signal=Signal.HOLD,
                ticker=ticker,
                price=price,
                strategy_name=self.name,
                reason="Bollinger Band squeeze detected - breakout anticipated",
            )

        return self._hold(ticker, df)

    def _mean_reversion_signal(
        self, ticker, price, upper, lower, middle, atr, df,
    ) -> TradeSignal:
        sl_distance = self.params["atr_sl_multiplier"] * atr if pd.notna(atr) else price * 0.02

        # BUY at lower band (expect reversion to mean)
        if price <= lower:
            stop_loss = price - sl_distance
            target = middle

            return TradeSignal(
                signal=Signal.BUY,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason="Price at lower Bollinger Band - mean reversion expected",
            )

        # SELL at upper band (expect reversion to mean)
        if price >= upper:
            stop_loss = price + sl_distance
            target = middle

            return TradeSignal(
                signal=Signal.SELL,
                ticker=ticker,
                price=price,
                stop_loss=round(stop_loss, 2),
                target=round(target, 2),
                strategy_name=self.name,
                reason="Price at upper Bollinger Band - mean reversion expected",
            )

        return self._hold(ticker, df)

    def _hold(self, ticker: str, df: pd.DataFrame) -> TradeSignal:
        price = df["close"].iloc[-1] if len(df) > 0 else 0.0
        return TradeSignal(
            signal=Signal.HOLD,
            ticker=ticker,
            price=price,
            strategy_name=self.name,
            reason="Price within Bollinger Bands",
        )
