import time
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: int


class TradingStrategy:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.last_signals = {}

    def process_ai_analysis(self, analysis: Dict[str, Any], market_price: float) -> Signal:

        signal_type = analysis.get("signal", "HOLD")


        stop_loss = market_price * (1 - self.config["stop_loss_pct"] / 100)
        take_profit = market_price * (1 + self.config["take_profit_pct"] / 100)

        if signal_type == "SELL":
            stop_loss = market_price * (1 + self.config["stop_loss_pct"] / 100)
            take_profit = market_price * (1 - self.config["take_profit_pct"] / 100)

        signal = Signal(
            symbol=self.config["symbol"],
            signal_type=signal_type,
            confidence=70.0,
            entry_price=market_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=int(time.time())
        )


        if self._should_execute_signal(signal):
            self.last_signals[signal.symbol] = signal
            return signal
        return None

    def _should_execute_signal(self, signal: Signal) -> bool:

        if signal.signal_type == "HOLD":
            return False

        last_signal = self.last_signals.get(signal.symbol)
        if not last_signal:
            return True


        time_diff = signal.timestamp - last_signal.timestamp
        if time_diff < 300:
            return False

        return True