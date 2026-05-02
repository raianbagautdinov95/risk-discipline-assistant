"""End-to-end decision engine tests with stubbed AI clients."""
from __future__ import annotations

import asyncio

import pytest

from app.schemas import CoachReport, OfficerReport, RiskCalc, RuleViolation, TradeRequest
from app.services.decision_engine import decide
from app.services.risk_engine import UserPolicy


class StubCoach:
    def __init__(self, recommendation: str = "enter") -> None:
        self.recommendation = recommendation

    async def coach(self, req: TradeRequest, calc: RiskCalc, violations: list[RuleViolation]) -> CoachReport:
        return CoachReport(
            summary="stub summary",
            pros=["x"],
            cons=["y"],
            recommendation=self.recommendation,
        )


class StubOfficer:
    def __init__(self, decision: str = "ALLOWED") -> None:
        self.decision = decision

    async def review(self, req: TradeRequest, calc: RiskCalc, violations: list[RuleViolation]) -> OfficerReport:
        return OfficerReport(
            summary="stub officer",
            violations=[v.message for v in violations if v.blocking],
            decision=self.decision,
        )


def _trade(**over) -> TradeRequest:
    base = dict(
        pair="BTC/USDT",
        direction="long",
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=103.0,
        deposit=1000.0,
        risk_percent=1.0,
        leverage=1,
        reason="setup pass",
        setup="breakout",
        emotion="спокоен",
        losses_today=0.0,
        consecutive_losses=0,
    )
    base.update(over)
    return TradeRequest(**base)


POLICY = UserPolicy()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.asyncio
async def test_clean_trade_allowed():
    resp = await decide(_trade(), POLICY, StubCoach(), StubOfficer())
    assert resp.decision == "ALLOWED"
    assert resp.calc.rr_ratio == 3.0
    assert resp.score >= 7.0


@pytest.mark.asyncio
async def test_rule_engine_vetoes_even_if_ai_allows():
    # AI says ALLOWED but no SL -> rules force FORBIDDEN
    resp = await decide(
        _trade(stop_loss=None, take_profit=None),
        POLICY,
        StubCoach(recommendation="enter"),
        StubOfficer(decision="ALLOWED"),
    )
    assert resp.decision == "FORBIDDEN"
    assert any(v.code == "NO_STOP_LOSS" for v in resp.violations)


@pytest.mark.asyncio
async def test_officer_can_veto_clean_trade():
    resp = await decide(
        _trade(),
        POLICY,
        StubCoach(recommendation="enter"),
        StubOfficer(decision="FORBIDDEN"),
    )
    assert resp.decision == "FORBIDDEN"


@pytest.mark.asyncio
async def test_officer_wait_translates_to_wait():
    resp = await decide(
        _trade(),
        POLICY,
        StubCoach(recommendation="enter"),
        StubOfficer(decision="WAIT"),
    )
    assert resp.decision == "WAIT"


@pytest.mark.asyncio
async def test_coach_skip_yields_wait_when_rules_clean():
    resp = await decide(
        _trade(),
        POLICY,
        StubCoach(recommendation="skip"),
        StubOfficer(decision="ALLOWED"),
    )
    assert resp.decision == "WAIT"


@pytest.mark.asyncio
async def test_revenge_trading_in_reason_blocks():
    resp = await decide(
        _trade(reason="хочу отыграться"),
        POLICY,
        StubCoach(),
        StubOfficer(decision="ALLOWED"),
    )
    assert resp.decision == "FORBIDDEN"
    assert any(v.code == "REVENGE_TRADING" for v in resp.violations)


@pytest.mark.asyncio
async def test_response_message_contains_disclaimer():
    resp = await decide(_trade(), POLICY, StubCoach(), StubOfficer())
    assert "Это не финансовая рекомендация" in resp.formatted_message
    assert "не финансовая рекомендация" in resp.disclaimer
