import time
from typing import Dict, Any, Optional
from collections import defaultdict


class RiskMonitor:
    def __init__(self, max_daily_loss: float = 100.0):
        self.max_daily_loss = max_daily_loss
        self.daily_loss = 0.0
        self.last_reset_day = time.strftime("%Y-%m-%d")
        self.trade_history = defaultdict(list)

    def check_trade_allowed(self, proposed_risk: float) -> bool:

        self._reset_daily_if_needed()

        potential_loss = self.daily_loss + proposed_risk
        return potential_loss <= self.max_daily_loss

    def record_trade(self, trade_result: Dict[str, Any]):

        self._reset_daily_if_needed()

        if trade_result["pnl"] < 0:
            self.daily_loss += abs(trade_result["pnl"])

        self.trade_history[time.strftime("%Y-%m-%d")].append(trade_result)

    def get_risk_status(self) -> Dict[str, Any]:

        self._reset_daily_if_needed()

        return {
            "daily_loss": round(self.daily_loss, 2),
            "max_daily_loss": self.max_daily_loss,
            "remaining_allowance": round(self.max_daily_loss - self.daily_loss, 2),
            "risk_used_pct": round((self.daily_loss / self.max_daily_loss) * 100, 2),
            "trades_today": len(self.trade_history[time.strftime("%Y-%m-%d")])
        }

    def _reset_daily_if_needed(self):

        current_day = time.strftime("%Y-%m-%d")
        if current_day != self.last_reset_day:
            self.daily_loss = 0.0
            self.last_reset_day = current_day