from __future__ import annotations

from app.schemas import (
    CoachReport,
    OfficerReport,
    RiskCalc,
    RuleViolation,
    TradeRequest,
    TradeResponse,
)
from app.services import risk_engine
from app.services.ai_coach import AICoach
from app.services.ai_risk_officer import AIRiskOfficer

DISCLAIMER = (
    "This is not financial advice. The bot helps you control risk "
    "and discipline. The decision and responsibility are yours."
)

DECISION_LABELS = {
    "ALLOWED": "ALLOWED",
    "FORBIDDEN": "FORBIDDEN",
    "WAIT": "WAIT",
}


def _score_trade(
    req: TradeRequest,
    calc: RiskCalc,
    violations: list[RuleViolation],
    policy: risk_engine.UserPolicy,
) -> float:
    score = 10.0
    score -= 3.0 * sum(1 for v in violations if v.blocking)

    if calc.rr_ratio is None:
        score -= 2.0
    elif calc.rr_ratio < policy.min_rr:
        score -= 2.0
    elif calc.rr_ratio >= 3.0:
        score += 1.0

    if req.risk_percent > policy.max_risk_percent:
        score -= 1.5
    elif req.risk_percent <= policy.max_risk_percent / 2:
        score += 0.5

    if req.leverage > policy.max_leverage:
        score -= 1.5
    elif req.leverage > 3:
        score -= 0.5

    return max(0.0, min(10.0, round(score, 1)))


def _format_message(
    decision: str,
    score: float,
    calc: RiskCalc,
    req: TradeRequest,
    violations: list[RuleViolation],
    coach: CoachReport | None,
    officer: OfficerReport | None,
    recommendation: str,
) -> str:
    label = DECISION_LABELS.get(decision, decision)
    lines: list[str] = [
        f"DECISION: {label}",
        f"Trade score: {score}/10",
        "",
        "Calculations:",
        f"• risk in money: {calc.risk_money}",
        f"• risk in %: {req.risk_percent}%",
        f"• R:R: {calc.rr_ratio if calc.rr_ratio is not None else '—'}",
        f"• leverage: x{req.leverage}{' (CRITICAL)' if calc.leverage_critical else ''}",
        f"• position size: "
        f"{calc.position_size if calc.position_size is not None else '—'}",
        "",
        "Reasons:",
    ]

    if violations:
        for i, v in enumerate(violations, 1):
            lines.append(f"{i}. {v.message}")
    elif officer and officer.violations:
        for i, msg in enumerate(officer.violations, 1):
            lines.append(f"{i}. {msg}")
    else:
        lines.append("1. No hard rule violations found.")
    lines.append("")

    lines.append("Discipline:")
    if officer:
        lines.append(f"• Risk Officer: {officer.summary}")
    if coach:
        cons = "; ".join(coach.cons) if coach.cons else "—"
        pros = "; ".join(coach.pros) if coach.pros else "—"
        lines.append(f"• Coach (pros): {pros}")
        lines.append(f"• Coach (cons): {cons}")

    lines += ["", f"Recommendation: {recommendation}", "", f"⚠️ {DISCLAIMER}"]
    return "\n".join(lines)


async def decide(
    req: TradeRequest,
    policy: risk_engine.UserPolicy,
    coach_client: AICoach | None,
    officer_client: AIRiskOfficer | None,
) -> TradeResponse:
    calc = risk_engine.calculate(req)
    violations = risk_engine.check_rules(req, calc, policy)
    rules_block = risk_engine.is_blocked(violations)

    coach: CoachReport | None = None
    officer: OfficerReport | None = None

    if officer_client is not None:
        officer = await officer_client.review(req, calc, violations)
    if coach_client is not None and not rules_block:
        coach = await coach_client.coach(req, calc, violations)

    final = "ALLOWED"
    if rules_block:
        final = "FORBIDDEN"
    elif officer and officer.decision == "FORBIDDEN":
        final = "FORBIDDEN"
    elif officer and officer.decision == "WAIT":
        final = "WAIT"
    elif coach and coach.recommendation == "skip":
        final = "WAIT"

    score = _score_trade(req, calc, violations, policy)

    if final == "FORBIDDEN":
        recommendation = "skip this trade"
    elif final == "WAIT":
        recommendation = "wait for a better entry"
    else:
        recommendation = (
            "reduce the risk and enter"
            if (coach and coach.recommendation == "reduce_risk")
            else "enter as planned"
        )

    formatted = _format_message(
        final, score, calc, req, violations, coach, officer, recommendation
    )

    return TradeResponse(
        decision=final,
        score=score,
        calc=calc,
        violations=violations,
        coach=coach,
        officer=officer,
        recommendation=recommendation,
        formatted_message=formatted,
        disclaimer=DISCLAIMER,
    )
