"""Настройки бота. Никаких ключей биржи — бот не торгует, только анализирует."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


# Топ-10 монет по капитализации (стабильные, ликвидные на OKX).
# Символы в формате OKX: BASE-USDT
DEFAULT_SYMBOLS: List[str] = [
    "BTC-USDT",
    "ETH-USDT",
    "SOL-USDT",
    "BNB-USDT",
    "XRP-USDT",
    "DOGE-USDT",
    "ADA-USDT",
    "TRX-USDT",
    "AVAX-USDT",
    "LINK-USDT",
]


@dataclass
class TradingConfig:
    # Тройной мультитаймфрейм: 4H — макро-тренд, 1H — средний тренд, 15m — вход.
    htf_timeframe: str = "4H"         # верхний фильтр (может быть "" чтобы отключить)
    trend_timeframe: str = "1H"       # средний фильтр направления
    entry_timeframe: str = "15m"      # точный вход
    symbols: List[str] = field(default_factory=lambda: DEFAULT_SYMBOLS.copy())

    # Параметры управления риском в сигнале (для расчёта SL/TP).
    atr_period: int = 14
    stop_loss_atr_mult: float = 1.5   # SL = entry - 1.5 * ATR (для LONG)
    take_profit_atr_mult: float = 3.0 # TP = entry + 3.0 * ATR → R:R = 1:2

    # Сколько свечей тянем для расчёта индикаторов.
    candles_limit: int = 200

    # Как часто сканировать рынок (сек). 900 = 15 минут — совпадает с entry_timeframe.
    scan_interval_sec: int = 900

    # Минимальная "уверенность" сигнала, чтобы его показать (0..100).
    # После бэктеста подняли с 60 → 72: это реально фильтрует шум.
    min_confidence: float = 72.0

    # Cooldown: после сигнала по символу N следующих свечей мы не выдаём
    # сигнал того же направления. Это защищает от серии входов на одном сетапе.
    # 8 x 15m = 2 часа — стандарт для intraday.
    cooldown_bars: int = 8

    # Требовать хотя бы один "сильный" паттерн: дивергенцию RSI/MACD
    # или свечной паттерн на ключевом уровне.
    # Если False — сигнал может идти только на простом консенсусе индикаторов.
    require_strong_confluence: bool = True


@dataclass
class AIConfig:
    """DeepSeek используется как опциональное второе мнение."""
    enabled: bool = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    model: str = "deepseek-chat"
    max_tokens: int = 500
    temperature: float = 0.3  # ниже = более консистентно


@dataclass
class NotifyConfig:
    """Настройки уведомлений."""
    console: bool = True
    save_history: bool = True
    telegram_enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
