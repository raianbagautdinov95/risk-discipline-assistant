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
    "Это не финансовая рекомендация. Бот помогает контролировать риск "
    "и дисциплину. Решение и ответственность — за тобой."
)

DECISION_LABELS = {
    "ALLOWED": "РАЗРЕШЕНО",
    "FORBIDDEN": "ЗАПРЕЩЕНО",
    "WAIT": "ЖДАТЬ",
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
        f"РЕШЕНИЕ: {label}",
        f"Оценка сделки: {score}/10",
        "",
        "Расчёты:",
        f"• риск в деньгах: {calc.risk_money}",
        f"• риск в %: {req.risk_percent}%",
        f"• R:R: {calc.rr_ratio if calc.rr_ratio is not None else '—'}",
        f"• плечо: x{req.leverage}{' (КРИТИЧНО)' if calc.leverage_critical else ''}",
        f"• размер позиции: "
        f"{calc.position_size if calc.position_size is not None else '—'}",
        "",
        "Причины решения:",
    ]

    if violations:
        for i, v in enumerate(violations, 1):
            lines.append(f"{i}. {v.message}")
    elif officer and officer.violations:
        for i, msg in enumerate(officer.violations, 1):
            lines.append(f"{i}. {msg}")
    else:
        lines.append("1. Жёстких нарушений правил не обнаружено.")
    lines.append("")

    lines.append("Дисциплина:")
    if officer:
        lines.append(f"• Risk Officer: {officer.summary}")
    if coach:
        cons = "; ".join(coach.cons) if coach.cons else "—"
        pros = "; ".join(coach.pros) if coach.pros else "—"
        lines.append(f"• Coach (плюсы): {pros}")
        lines.append(f"• Coach (минусы): {cons}")

    lines += ["", f"Рекомендация: {recommendation}", "", f"⚠️ {DISCLAIMER}"]
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
        recommendation = "пропустить сделку"
    elif final == "WAIT":
        recommendation = "ждать лучшую точку входа"
    else:
        recommendation = (
            "снизить риск и входить"
            if (coach and coach.recommendation == "reduce_risk")
            else "входить по плану"
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
