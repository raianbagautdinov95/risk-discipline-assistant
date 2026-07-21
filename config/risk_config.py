"""Risk-management parameters for COMPUTING signals (not for trading).
Used to suggest a reasonable stop-loss and take-profit in the notification."""
from dataclasses import dataclass


@dataclass
class RiskLimits:
    # Minimum acceptable risk/reward ratio. Signals below it are discarded.
    min_risk_reward: float = 1.5

    # Indicator consensus threshold at which a signal is considered strong.
    strong_signal_threshold: float = 75.0
