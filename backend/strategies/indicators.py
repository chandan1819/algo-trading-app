"""
Shared technical indicator functions for NSE India trading strategies.
All functions operate on pandas Series/DataFrames using vectorized operations.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Tuple


def EMA(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average using TradingView method.

    TradingView initializes EMA with an SMA seed for the first `period` values,
    then applies the standard EMA formula going forward.
    """
    multiplier = 2.0 / (period + 1)
    ema = pd.Series(np.nan, index=series.index, dtype=float)

    # SMA seed
    if len(series) < period:
        return ema

    ema.iloc[period - 1] = series.iloc[:period].mean()

    for i in range(period, len(series)):
        ema.iloc[i] = series.iloc[i] * multiplier + ema.iloc[i - 1] * (1 - multiplier)

    return ema


def SMA(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def RMA(series: pd.Series, period: int) -> pd.Series:
    """Running Moving Average (Wilder's smoothing), used for RSI calculation.

    Also known as SMMA. Uses SMA as seed value then applies:
        rma = (prev_rma * (period - 1) + current_value) / period
    """
    rma = pd.Series(np.nan, index=series.index, dtype=float)

    if len(series) < period:
        return rma

    rma.iloc[period - 1] = series.iloc[:period].mean()

    for i in range(period, len(series)):
        rma.iloc[i] = (rma.iloc[i - 1] * (period - 1) + series.iloc[i]) / period

    return rma


def RSI(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = RMA(gain, period)
    avg_loss = RMA(loss, period)

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def MACD(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD indicator.

    Returns:
        (macd_line, signal_line, histogram)
    """
    fast_ema = EMA(series, fast)
    slow_ema = EMA(series, slow)

    macd_line = fast_ema - slow_ema
    signal_line = EMA(macd_line.dropna().reset_index(drop=True), signal)

    # Re-align signal_line index with macd_line
    valid_macd = macd_line.dropna()
    signal_aligned = pd.Series(np.nan, index=series.index, dtype=float)
    if len(signal_line.dropna()) > 0:
        start_idx = valid_macd.index[0]
        offset = signal - 1
        for j, val in enumerate(signal_line.dropna()):
            pos = valid_macd.index[offset + j] if (offset + j) < len(valid_macd) else None
            if pos is not None:
                signal_aligned.iloc[pos] = val

    histogram = macd_line - signal_aligned

    return macd_line, signal_aligned, histogram


def BollingerBands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands.

    Returns:
        (upper_band, middle_band, lower_band, bandwidth)
    """
    middle = SMA(series, period)
    rolling_std = series.rolling(window=period, min_periods=period).std()

    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std
    bandwidth = (upper - lower) / middle

    return upper, middle, lower, bandwidth


def VWAP(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price.

    Expects DataFrame with columns: high, low, close, volume.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()

    vwap = cumulative_tp_vol / cumulative_vol
    return vwap


def ATR(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range.

    Expects DataFrame with columns: high, low, close.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = RMA(true_range, period)
    return atr


def SuperTrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """SuperTrend indicator.

    Returns:
        (supertrend_line, direction)
        direction: 1 = uptrend (bullish), -1 = downtrend (bearish)
    """
    atr = ATR(df, period)
    hl2 = (df["high"] + df["low"]) / 2.0

    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    supertrend = pd.Series(np.nan, index=df.index, dtype=float)
    direction = pd.Series(0, index=df.index, dtype=int)

    close = df["close"]

    # Find first valid index where ATR is available
    first_valid = atr.first_valid_index()
    if first_valid is None:
        return supertrend, direction

    supertrend.iloc[first_valid] = upper_band.iloc[first_valid]
    direction.iloc[first_valid] = -1

    final_upper = upper_band.copy()
    final_lower = lower_band.copy()

    for i in range(first_valid + 1, len(df)):
        # Adjust bands based on previous values
        if final_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
            pass  # keep current upper
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if final_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
            pass  # keep current lower
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if direction.iloc[i - 1] == -1:
            if close.iloc[i] > final_upper.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]
        else:
            if close.iloc[i] < final_lower.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]

    return supertrend, direction


def support_resistance_levels(
    df: pd.DataFrame,
    lookback: int = 20,
) -> Tuple[list, list]:
    """Identify key support and resistance levels using swing highs/lows.

    Returns:
        (support_levels, resistance_levels) as sorted lists of price floats.
    """
    high = df["high"].values
    low = df["low"].values

    supports = []
    resistances = []

    for i in range(lookback, len(df) - lookback):
        # Swing high: highest high in the lookback window on both sides
        if high[i] == max(high[i - lookback : i + lookback + 1]):
            resistances.append(float(high[i]))

        # Swing low: lowest low in the lookback window on both sides
        if low[i] == min(low[i - lookback : i + lookback + 1]):
            supports.append(float(low[i]))

    # Remove near-duplicate levels (within 0.5% of each other)
    supports = _deduplicate_levels(sorted(supports))
    resistances = _deduplicate_levels(sorted(resistances))

    return supports, resistances


def _deduplicate_levels(levels: list, tolerance: float = 0.005) -> list:
    """Remove levels that are within `tolerance` percentage of each other."""
    if not levels:
        return levels

    deduped = [levels[0]]
    for level in levels[1:]:
        if abs(level - deduped[-1]) / deduped[-1] > tolerance:
            deduped.append(level)

    return deduped
