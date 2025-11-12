from typing import Dict, Optional
from config.risk_config import RiskLimits


class PositionSizer:
    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits

    def calculate_position_size(
            self,
            account_balance: float,
            entry_price: float,
            stop_loss_price: float,
            confidence: float = 70.0
    ) -> Dict[str, float]:



        risk_amount = account_balance * (self.risk_limits.risk_per_trade / 100)


        risk_per_coin = abs(entry_price - stop_loss_price)

        if risk_per_coin == 0:
            return {"size": 0, "risk_amount": 0}


        position_size = risk_amount / risk_per_coin


        max_position_value = account_balance * (self.risk_limits.max_position_size_pct / 100)
        max_position_size = max_position_value / entry_price

        final_size = min(position_size, max_position_size)


        confidence_factor = confidence / 100
        final_size *= confidence_factor

        return {
            "size": round(final_size, 6),
            "risk_amount": round(risk_amount, 2),
            "position_value": round(final_size * entry_price, 2)
        }