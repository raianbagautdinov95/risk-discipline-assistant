# config/settings.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class OKXConfig:
    api_key: str = os.getenv("OKX_API_KEY", "")
    api_secret: str = os.getenv("OKX_API_SECRET", "")
    passphrase: str = os.getenv("OKX_PASSPHRASE", "")
    testnet: bool = os.getenv("OKX_TESTNET", "false").lower() == "true"  # false = Live

@dataclass
class TradingConfig:
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    max_positions: int = 3
    trade_amount_usdt: float = 100.0
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0

@dataclass
class AIConfig:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    model: str = "deepseek-chat"
    max_tokens: int = 2000
    temperature: float = 0.7