"""Технические индикаторы и анализ структуры рынка.
Использует библиотеку ta (pure-python, без C-зависимостей)."""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator

from ai.patterns import (
    detect_divergence,
    detect_candle_pattern,
    detect_bollinger_squeeze,
    is_at_key_level,
)


def compute_indicators(df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
    """Добавляет в DataFrame колонки с индикаторами. Возвращает новый DataFrame."""
    if df is None or len(df) < 50:
        raise ValueError("Нужно минимум 50 свечей для корректного расчёта индикаторов")

    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    volume = out["volume"]

    # --- Моментум ---
    out["rsi"] = RSIIndicator(close=close, window=14).rsi()

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    out["stoch_k"] = stoch.stoch()
    out["stoch_d"] = stoch.stoch_signal()

    # --- Тренд ---
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    out["macd"] = macd.macd()
    out["macd_signal"] = macd.macd_signal()
    out["macd_diff"] = macd.macd_diff()

    out["ema_20"] = EMAIndicator(close=close, window=20).ema_indicator()
    out["ema_50"] = EMAIndicator(close=close, window=50).ema_indicator()
    out["ema_200"] = EMAIndicator(close=close, window=min(200, len(close) - 1)).ema_indicator()

    adx = ADXIndicator(high=high, low=low, close=close, window=14)
    out["adx"] = adx.adx()
    out["di_plus"] = adx.adx_pos()
    out["di_minus"] = adx.adx_neg()

    # --- Волатильность ---
    bb = BollingerBands(close=close, window=20, window_dev=2)
    out["bb_upper"] = bb.bollinger_hband()
    out["bb_lower"] = bb.bollinger_lband()
    out["bb_mid"] = bb.bollinger_mavg()
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_mid"]

    atr = AverageTrueRange(high=high, low=low, close=close, window=atr_period)
    out["atr"] = atr.average_true_range()

    # --- Объём ---
    out["obv"] = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    out["volume_ma_20"] = volume.rolling(window=20).mean()
    out["volume_spike"] = volume / out["volume_ma_20"]  # >1.5 = аномально высокий объём

    return out


def detect_trend(df: pd.DataFrame) -> str:
    """Определяет направление тренда по EMA и ADX.
    Возвращает: 'UP', 'DOWN' или 'SIDEWAYS'.
    """
    last = df.iloc[-1]

    # Слабый тренд, если ADX < 20.
    if pd.isna(last["adx"]) or last["adx"] < 20:
        return "SIDEWAYS"

    # Восходящий: цена выше EMA50, EMA20 > EMA50, DI+ > DI-
    if last["close"] > last["ema_50"] and last["ema_20"] > last["ema_50"] and last["di_plus"] > last["di_minus"]:
        return "UP"
    if last["close"] < last["ema_50"] and last["ema_20"] < last["ema_50"] and last["di_minus"] > last["di_plus"]:
        return "DOWN"
    return "SIDEWAYS"


def find_support_resistance(df: pd.DataFrame, lookback: int = 50) -> Dict[str, float]:
    """Простой поиск ближайшей поддержки/сопротивления по локальным экстремумам."""
    recent = df.tail(lookback)
    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    return {"support": support, "resistance": resistance}


def indicator_snapshot(df: pd.DataFrame) -> Dict[str, Any]:
    """Свёртка последней свечи в удобный dict для передачи в движок сигналов и в AI."""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    sr = find_support_resistance(df, lookback=50)

    # Продвинутые паттерны.
    rsi_div = detect_divergence(df, indicator="rsi", lookback=50)
    macd_div = detect_divergence(df, indicator="macd_diff", lookback=50)
    candle = detect_candle_pattern(df)
    squeeze = detect_bollinger_squeeze(df, lookback=30)

    price = float(last["close"])
    atr_val = float(last["atr"]) if not pd.isna(last["atr"]) else 0.0
    at_level = is_at_key_level(price, sr["support"], sr["resistance"], atr_val)

    return {
        # Timestamp последней свечи (секунды). Нужен для cooldown в движке сигналов.
        "timestamp": int(last["timestamp"]) // 1000 if "timestamp" in df.columns else None,
        "price": float(last["close"]),
        "open": float(last["open"]),
        "high": float(last["high"]),
        "low": float(last["low"]),
        "volume": float(last["volume"]),

        "rsi": float(last["rsi"]) if not pd.isna(last["rsi"]) else None,
        "stoch_k": float(last["stoch_k"]) if not pd.isna(last["stoch_k"]) else None,
        "stoch_d": float(last["stoch_d"]) if not pd.isna(last["stoch_d"]) else None,

        "macd": float(last["macd"]) if not pd.isna(last["macd"]) else None,
        "macd_signal": float(last["macd_signal"]) if not pd.isna(last["macd_signal"]) else None,
        "macd_diff": float(last["macd_diff"]) if not pd.isna(last["macd_diff"]) else None,
        "macd_diff_prev": float(prev["macd_diff"]) if not pd.isna(prev["macd_diff"]) else None,

        "ema_20": float(last["ema_20"]) if not pd.isna(last["ema_20"]) else None,
        "ema_50": float(last["ema_50"]) if not pd.isna(last["ema_50"]) else None,
        "ema_200": float(last["ema_200"]) if not pd.isna(last["ema_200"]) else None,

        "adx": float(last["adx"]) if not pd.isna(last["adx"]) else None,
        "di_plus": float(last["di_plus"]) if not pd.isna(last["di_plus"]) else None,
        "di_minus": float(last["di_minus"]) if not pd.isna(last["di_minus"]) else None,

        "bb_upper": float(last["bb_upper"]) if not pd.isna(last["bb_upper"]) else None,
        "bb_lower": float(last["bb_lower"]) if not pd.isna(last["bb_lower"]) else None,
        "bb_width": float(last["bb_width"]) if not pd.isna(last["bb_width"]) else None,

        "atr": float(last["atr"]) if not pd.isna(last["atr"]) else None,
        "volume_spike": float(last["volume_spike"]) if not pd.isna(last["volume_spike"]) else None,

        "trend": detect_trend(df),
        "support": sr["support"],
        "resistance": sr["resistance"],

        # Продвинутые паттерны.
        "rsi_divergence": rsi_div,       # 'BULLISH' | 'BEARISH' | None
        "macd_divergence": macd_div,     # 'BULLISH' | 'BEARISH' | None
        "candle_pattern": candle,        # например 'BULLISH_ENGULFING' или None
        "bollinger_squeeze": squeeze,    # True/False — готовность к импульсу
        "at_key_level": at_level,        # 'SUPPORT' | 'RESISTANCE' | None
    }
