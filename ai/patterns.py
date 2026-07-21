"""Advanced patterns:
- Divergences between price and RSI/MACD
- Candlestick patterns (engulfing, hammer, shooting star, doji)
- Bollinger squeeze — low volatility before an impulse

All functions operate on an already-computed DataFrame with indicators.
"""
from typing import Optional, Dict, List
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------- #
# DIVERGENCES                                                            #
# ---------------------------------------------------------------------- #

def _find_pivots(series: pd.Series, window: int = 3) -> Dict[str, List[int]]:
    """Finds local maxima and minima (pivots).
    Pivot high at point i: series[i] — the maximum in the window [i-window, i+window].
    Returns {'highs': [indices], 'lows': [indices]}."""
    highs = []
    lows = []
    n = len(series)
    for i in range(window, n - window):
        left = series.iloc[i - window:i]
        right = series.iloc[i + 1:i + window + 1]
        val = series.iloc[i]
        if val >= left.max() and val >= right.max():
            highs.append(i)
        if val <= left.min() and val <= right.min():
            lows.append(i)
    return {"highs": highs, "lows": lows}


def detect_divergence(df: pd.DataFrame, indicator: str = "rsi",
                      lookback: int = 50, window: int = 3) -> Optional[str]:
    """Looks for a divergence between price and the indicator over the last `lookback` candles.

    Returns:
      'BULLISH' — price made a Lower Low, the indicator made a Higher Low (reversal up)
      'BEARISH' — price made a Higher High, the indicator made a Lower High (reversal down)
      None — no divergence
    """
    if indicator not in df.columns:
        return None

    recent = df.tail(lookback).reset_index(drop=True)
    if len(recent) < 2 * window + 2:
        return None

    price_pivots = _find_pivots(recent["close"], window=window)
    ind_series = recent[indicator]

    # Bullish: the last two price lows form a lower low, while the indicator forms a higher low.
    lows = price_pivots["lows"]
    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]
        # Check that the second low is not too close to the last pivot
        if i2 - i1 >= window:
            price_lower = recent["close"].iloc[i2] < recent["close"].iloc[i1]
            ind_higher = ind_series.iloc[i2] > ind_series.iloc[i1]
            if price_lower and ind_higher:
                return "BULLISH"

    # Bearish: a lower high on the indicator alongside a higher high on price.
    highs = price_pivots["highs"]
    if len(highs) >= 2:
        i1, i2 = highs[-2], highs[-1]
        if i2 - i1 >= window:
            price_higher = recent["close"].iloc[i2] > recent["close"].iloc[i1]
            ind_lower = ind_series.iloc[i2] < ind_series.iloc[i1]
            if price_higher and ind_lower:
                return "BEARISH"

    return None


# ---------------------------------------------------------------------- #
# CANDLESTICK PATTERNS                                                   #
# ---------------------------------------------------------------------- #

def detect_candle_pattern(df: pd.DataFrame) -> Optional[str]:
    """Detects a pattern on the last closed candle.

    Returns:
      'BULLISH_ENGULFING', 'BEARISH_ENGULFING',
      'HAMMER', 'SHOOTING_STAR', 'DOJI'
      or None.
    """
    if len(df) < 2:
        return None

    prev = df.iloc[-2]
    last = df.iloc[-1]

    p_body = abs(prev["close"] - prev["open"])
    l_body = abs(last["close"] - last["open"])
    l_range = last["high"] - last["low"]
    if l_range <= 0:
        return None

    # Doji — body < 10% of the range.
    if l_body / l_range < 0.1:
        return "DOJI"

    # Engulfing: bodies point in opposite directions, the second body fully covers the first.
    prev_bullish = prev["close"] > prev["open"]
    last_bullish = last["close"] > last["open"]

    if not prev_bullish and last_bullish:
        # Bullish engulfing.
        if last["open"] < prev["close"] and last["close"] > prev["open"] and l_body > p_body:
            return "BULLISH_ENGULFING"

    if prev_bullish and not last_bullish:
        # Bearish engulfing.
        if last["open"] > prev["close"] and last["close"] < prev["open"] and l_body > p_body:
            return "BEARISH_ENGULFING"

    # Hammer / Shooting star: a long shadow on one side, a small body.
    upper_shadow = last["high"] - max(last["close"], last["open"])
    lower_shadow = min(last["close"], last["open"]) - last["low"]

    if l_body > 0:
        # Hammer — long lower shadow (2+ times the body), upper shadow no more than 30% of the lower.
        if lower_shadow >= 2 * l_body and upper_shadow <= lower_shadow * 0.3:
            return "HAMMER"
        # Shooting star — long upper shadow, lower shadow no more than 30% of the upper.
        if upper_shadow >= 2 * l_body and lower_shadow <= upper_shadow * 0.3:
            return "SHOOTING_STAR"

    return None


def is_at_key_level(price: float, support: float, resistance: float,
                    atr: float) -> Optional[str]:
    """Determines that the price is at an important level.
    Returns 'SUPPORT', 'RESISTANCE' or None."""
    if atr <= 0:
        return None
    threshold = max(atr * 0.8, price * 0.005)
    if abs(price - support) < threshold:
        return "SUPPORT"
    if abs(price - resistance) < threshold:
        return "RESISTANCE"
    return None


# ---------------------------------------------------------------------- #
# BOLLINGER SQUEEZE                                                      #
# ---------------------------------------------------------------------- #

def detect_bollinger_squeeze(df: pd.DataFrame, lookback: int = 30) -> bool:
    """Squeeze — when the current BB width is in the lowest 20% of the range over the last `lookback` candles.
    A squeeze is often followed by an impulsive move."""
    if "bb_width" not in df.columns:
        return False
    recent = df["bb_width"].tail(lookback).dropna()
    if len(recent) < 10:
        return False
    current = recent.iloc[-1]
    percentile_20 = np.percentile(recent, 20)
    # Explicit cast to a Python bool — otherwise JSON can't serialize numpy.bool_.
    return bool(current <= percentile_20)
