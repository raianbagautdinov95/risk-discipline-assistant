"""Продвинутые паттерны:
- Дивергенции между ценой и RSI/MACD
- Свечные паттерны (engulfing, hammer, shooting star, doji)
- Боллинджер-сжатие (squeeze) — низкая волатильность перед импульсом

Все функции работают на уже посчитанном DataFrame с индикаторами.
"""
from typing import Optional, Dict, List
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------- #
# ДИВЕРГЕНЦИИ                                                            #
# ---------------------------------------------------------------------- #

def _find_pivots(series: pd.Series, window: int = 3) -> Dict[str, List[int]]:
    """Ищет локальные максимумы и минимумы (pivots).
    Pivot high в точке i: series[i] — максимум в окне [i-window, i+window].
    Возвращает {'highs': [индексы], 'lows': [индексы]}."""
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
    """Ищет дивергенцию между ценой и индикатором на последних `lookback` свечах.

    Возвращает:
      'BULLISH' — цена сделала Lower Low, индикатор сделал Higher Low (разворот вверх)
      'BEARISH' — цена сделала Higher High, индикатор сделал Lower High (разворот вниз)
      None — дивергенции нет
    """
    if indicator not in df.columns:
        return None

    recent = df.tail(lookback).reset_index(drop=True)
    if len(recent) < 2 * window + 2:
        return None

    price_pivots = _find_pivots(recent["close"], window=window)
    ind_series = recent[indicator]

    # Бычья: два последних минимума цены — lower low, а индикатор — higher low.
    lows = price_pivots["lows"]
    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]
        # Проверяем, что второй минимум — не слишком близко к последнему пивоту
        if i2 - i1 >= window:
            price_lower = recent["close"].iloc[i2] < recent["close"].iloc[i1]
            ind_higher = ind_series.iloc[i2] > ind_series.iloc[i1]
            if price_lower and ind_higher:
                return "BULLISH"

    # Медвежья: lower high на индикаторе при higher high на цене.
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
# СВЕЧНЫЕ ПАТТЕРНЫ                                                       #
# ---------------------------------------------------------------------- #

def detect_candle_pattern(df: pd.DataFrame) -> Optional[str]:
    """Детектирует паттерн на последней закрытой свече.

    Возвращает:
      'BULLISH_ENGULFING', 'BEARISH_ENGULFING',
      'HAMMER', 'SHOOTING_STAR', 'DOJI'
      или None.
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

    # Doji — тело < 10% диапазона.
    if l_body / l_range < 0.1:
        return "DOJI"

    # Engulfing: тела направлены противоположно, второе тело полностью перекрывает первое.
    prev_bullish = prev["close"] > prev["open"]
    last_bullish = last["close"] > last["open"]

    if not prev_bullish and last_bullish:
        # Бычий engulfing.
        if last["open"] < prev["close"] and last["close"] > prev["open"] and l_body > p_body:
            return "BULLISH_ENGULFING"

    if prev_bullish and not last_bullish:
        # Медвежий engulfing.
        if last["open"] > prev["close"] and last["close"] < prev["open"] and l_body > p_body:
            return "BEARISH_ENGULFING"

    # Hammer / Shooting star: длинная тень в одну сторону, маленькое тело.
    upper_shadow = last["high"] - max(last["close"], last["open"])
    lower_shadow = min(last["close"], last["open"]) - last["low"]

    if l_body > 0:
        # Hammer — длинная нижняя тень (в 2+ раза больше тела), верхняя не больше 30% от нижней.
        if lower_shadow >= 2 * l_body and upper_shadow <= lower_shadow * 0.3:
            return "HAMMER"
        # Shooting star — длинная верхняя тень, нижняя не больше 30% от верхней.
        if upper_shadow >= 2 * l_body and lower_shadow <= upper_shadow * 0.3:
            return "SHOOTING_STAR"

    return None


def is_at_key_level(price: float, support: float, resistance: float,
                    atr: float) -> Optional[str]:
    """Определяет, что цена у важного уровня.
    Возвращает 'SUPPORT', 'RESISTANCE' или None."""
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
    """Squeeze — когда текущая ширина BB в нижних 20% от диапазона за lookback свечей.
    После сжатия часто следует импульсное движение."""
    if "bb_width" not in df.columns:
        return False
    recent = df["bb_width"].tail(lookback).dropna()
    if len(recent) < 10:
        return False
    current = recent.iloc[-1]
    percentile_20 = np.percentile(recent, 20)
    # Явное приведение к Python bool — иначе JSON не умеет сериализовать numpy.bool_.
    return bool(current <= percentile_20)
