"""Bot settings. No exchange keys — the bot doesn't trade, it only analyzes."""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


# Top 10 coins by market cap (stable, liquid on OKX).
# Symbols in OKX format: BASE-USDT
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
    # Triple multi-timeframe: 4H — macro trend, 1H — mid trend, 15m — entry.
    htf_timeframe: str = "4H"         # top filter (can be "" to disable)
    trend_timeframe: str = "1H"       # mid-level direction filter
    entry_timeframe: str = "15m"      # precise entry
    symbols: List[str] = field(default_factory=lambda: DEFAULT_SYMBOLS.copy())

    # Risk-management parameters within the signal (for computing SL/TP).
    atr_period: int = 14
    stop_loss_atr_mult: float = 1.5   # SL = entry - 1.5 * ATR (for LONG)
    take_profit_atr_mult: float = 3.0 # TP = entry + 3.0 * ATR → R:R = 1:2

    # How many candles we pull to compute indicators.
    candles_limit: int = 200

    # How often to scan the market (sec). 900 = 15 minutes — matches entry_timeframe.
    scan_interval_sec: int = 900

    # Minimum signal "confidence" required to show it (0..100).
    # After backtesting we raised it from 60 → 72: this genuinely filters out noise.
    min_confidence: float = 72.0

    # Cooldown: after a signal for a symbol, we don't issue a signal of the same
    # direction for the next N candles. This protects against a series of entries
    # on a single setup. 8 x 15m = 2 hours — a standard for intraday.
    cooldown_bars: int = 8

    # Require at least one "strong" pattern: an RSI/MACD divergence
    # or a candlestick pattern at a key level.
    # If False, a signal may be issued on simple indicator consensus alone.
    require_strong_confluence: bool = True


@dataclass
class AIConfig:
    """DeepSeek is used as an optional second opinion."""
    enabled: bool = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    model: str = "deepseek-chat"
    max_tokens: int = 500
    temperature: float = 0.3  # lower = more consistent


@dataclass
class NotifyConfig:
    """Notification settings."""
    console: bool = True
    save_history: bool = True
    telegram_enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
