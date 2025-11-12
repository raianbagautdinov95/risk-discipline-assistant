from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_daily_loss: float = 100.0  # USDT
    max_position_size_pct: float = 10.0  # % of capital
    max_leverage: int = 10
    risk_per_trade: float = 1.0  # % of capital


@dataclass
class AccountLimits:
    min_capital_required: float = 1000.0
    max_drawdown_threshold: float = 15.0  # %