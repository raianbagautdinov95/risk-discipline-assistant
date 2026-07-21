from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import RiskCalc, RuleViolation, TradeRequest


# Keyword detection for free-text input, so a trade description in plain
# English is still caught by the rule engine.
_REVENGE_PATTERNS = [
    r"\brevenge\b",
    r"\btilt(ed|ing)?\b",
    r"\bwin\s+(it\s+)?back\b",
    r"\bget\s+(it\s+)?back\b",
    r"\bmake\s+(it\s+|the\s+money\s+)?back\b",
    r"\brecover\s+(my\s+)?loss(es)?\b",
]

_BAD_EMOTIONS = [
    "anger",
    "panic",
    "greed",
    "fomo",
    "fear of missing",
]


@dataclass
class UserPolicy:
    max_risk_percent: float = 1.0
    max_leverage: int = 5
    min_rr: float = 2.0
    daily_loss_limit: float = 2.0


def calculate(req: TradeRequest) -> RiskCalc:
    risk_money = req.deposit * (req.risk_percent / 100.0)

    sl_distance: float | None = None
    tp_distance: float | None = None
    rr: float | None = None
    position_size: float | None = None

    if req.stop_loss is not None:
        sl_distance = abs(req.entry_price - req.stop_loss)
        if sl_distance > 0:
            position_size = risk_money / sl_distance

    if req.take_profit is not None:
        tp_distance = abs(req.take_profit - req.entry_price)

    if sl_distance and tp_distance and sl_distance > 0:
        rr = tp_distance / sl_distance

    leveraged_risk = req.risk_percent * max(req.leverage, 1)

    return RiskCalc(
        risk_money=round(risk_money, 4),
        sl_distance=round(sl_distance, 8) if sl_distance is not None else None,
        tp_distance=round(tp_distance, 8) if tp_distance is not None else None,
        rr_ratio=round(rr, 3) if rr is not None else None,
        position_size=round(position_size, 6) if position_size is not None else None,
        leveraged_risk=round(leveraged_risk, 3),
        leverage_critical=req.leverage > 5,
    )


def detect_revenge_trading(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(re.search(p, lowered) for p in _REVENGE_PATTERNS)


def detect_bad_emotion(emotion: str | None) -> bool:
    if not emotion:
        return False
    lowered = emotion.lower()
    return any(token in lowered for token in _BAD_EMOTIONS)


def check_rules(req: TradeRequest, calc: RiskCalc, policy: UserPolicy) -> list[RuleViolation]:
    violations: list[RuleViolation] = []

    if req.stop_loss is None:
        violations.append(RuleViolation(
            code="NO_STOP_LOSS",
            message="Trading without a stop-loss is forbidden.",
        ))

    if req.risk_percent > policy.max_risk_percent:
        violations.append(RuleViolation(
            code="RISK_TOO_HIGH",
            message=f"Risk {req.risk_percent}% exceeds the "
                    f"{policy.max_risk_percent}% per-trade limit.",
        ))

    if calc.rr_ratio is not None and calc.rr_ratio < policy.min_rr:
        violations.append(RuleViolation(
            code="RR_TOO_LOW",
            message=f"R:R = {calc.rr_ratio} is below the 1:{policy.min_rr} minimum.",
        ))

    if req.leverage > policy.max_leverage:
        violations.append(RuleViolation(
            code="LEVERAGE_TOO_HIGH",
            message=f"Leverage x{req.leverage} exceeds the x{policy.max_leverage} limit.",
        ))

    if req.losses_today >= policy.daily_loss_limit:
        violations.append(RuleViolation(
            code="DAILY_LOSS_REACHED",
            message=f"Daily loss limit reached: -{req.losses_today}% "
                    f"(limit -{policy.daily_loss_limit}%). Done for today.",
        ))

    if req.consecutive_losses >= 2:
        violations.append(RuleViolation(
            code="CONSECUTIVE_LOSSES",
            message=f"{req.consecutive_losses} losing trades in a row — a break is mandatory.",
        ))

    text_blob = " ".join(filter(None, [req.reason, req.emotion, req.setup]))
    if detect_revenge_trading(text_blob):
        violations.append(RuleViolation(
            code="REVENGE_TRADING",
            message="Signs of revenge trading detected — trying to win losses back.",
        ))

    if detect_bad_emotion(req.emotion):
        violations.append(RuleViolation(
            code="BAD_EMOTION",
            message="Emotional state is not suitable for trading "
                    "(anger / panic / greed / FOMO).",
        ))

    return violations


def is_blocked(violations: list[RuleViolation]) -> bool:
    return any(v.blocking for v in violations)
