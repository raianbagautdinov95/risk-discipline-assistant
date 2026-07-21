"""Unit tests for the risk engine — math + hard rules."""
from __future__ import annotations

import pytest

from app.schemas import TradeRequest
from app.services.risk_engine import (
    UserPolicy,
    calculate,
    check_rules,
    detect_bad_emotion,
    detect_revenge_trading,
    is_blocked,
)


DEFAULT_POLICY = UserPolicy()


def _trade(**overrides) -> TradeRequest:
    base = dict(
        pair="BTC/USDT",
        direction="long",
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=103.0,
        deposit=1000.0,
        risk_percent=1.0,
        leverage=1,
        reason="ok",
        setup="breakout",
        emotion="calm",
        losses_today=0.0,
        consecutive_losses=0,
    )
    base.update(overrides)
    return TradeRequest(**base)


# --------------------------- calculations ---------------------------------

def test_calculate_basic_long():
    calc = calculate(_trade())
    assert calc.risk_money == 10.0  # 1% of 1000
    assert calc.sl_distance == 1.0
    assert calc.tp_distance == 3.0
    assert calc.rr_ratio == 3.0
    assert calc.position_size == 10.0   # 10 risk / 1 distance
    assert calc.leveraged_risk == 1.0
    assert calc.leverage_critical is False


def test_calculate_short_uses_abs_distances():
    req = _trade(direction="short", entry_price=100.0, stop_loss=101.0, take_profit=98.0)
    calc = calculate(req)
    assert calc.sl_distance == 1.0
    assert calc.tp_distance == 2.0
    assert calc.rr_ratio == 2.0


def test_calculate_no_stop_loss_returns_none_position_size():
    calc = calculate(_trade(stop_loss=None))
    assert calc.sl_distance is None
    assert calc.position_size is None
    assert calc.rr_ratio is None


def test_leverage_marked_critical_above_5():
    calc = calculate(_trade(leverage=10))
    assert calc.leverage_critical is True
    assert calc.leveraged_risk == 10.0


# --------------------------- hard rules -----------------------------------

def test_no_stop_loss_blocks():
    req = _trade(stop_loss=None, take_profit=None)
    calc = calculate(req)
    violations = check_rules(req, calc, DEFAULT_POLICY)
    codes = [v.code for v in violations]
    assert "NO_STOP_LOSS" in codes
    assert is_blocked(violations) is True


def test_risk_above_limit_blocks():
    req = _trade(risk_percent=2.5)
    calc = calculate(req)
    violations = check_rules(req, calc, DEFAULT_POLICY)
    assert any(v.code == "RISK_TOO_HIGH" for v in violations)
    assert is_blocked(violations)


def test_rr_below_minimum_blocks():
    # entry=100, SL=99 (dist=1), TP=100.5 (dist=0.5) -> RR = 0.5
    req = _trade(stop_loss=99.0, take_profit=100.5)
    calc = calculate(req)
    violations = check_rules(req, calc, DEFAULT_POLICY)
    assert calc.rr_ratio == 0.5
    assert any(v.code == "RR_TOO_LOW" for v in violations)


def test_high_leverage_blocks():
    req = _trade(leverage=10)
    calc = calculate(req)
    violations = check_rules(req, calc, DEFAULT_POLICY)
    assert any(v.code == "LEVERAGE_TOO_HIGH" for v in violations)


def test_daily_loss_limit_blocks():
    req = _trade(losses_today=2.5)
    violations = check_rules(req, calculate(req), DEFAULT_POLICY)
    assert any(v.code == "DAILY_LOSS_REACHED" for v in violations)


def test_consecutive_losses_blocks():
    req = _trade(consecutive_losses=2)
    violations = check_rules(req, calculate(req), DEFAULT_POLICY)
    assert any(v.code == "CONSECUTIVE_LOSSES" for v in violations)


@pytest.mark.parametrize(
    "text",
    [
        "I want revenge on this market",
        "need to win it back today",
        "totally tilted right now",
        "gotta make the money back",
        "I need to recover my losses",
    ],
)
def test_revenge_trading_detected(text: str):
    assert detect_revenge_trading(text) is True


def test_revenge_trading_negative_cases():
    assert detect_revenge_trading("clean breakout setup") is False
    assert detect_revenge_trading(None) is False


@pytest.mark.parametrize(
    "emotion",
    ["anger", "FOMO", "panic", "greed", "I have anger", "feeling greed"],
)
def test_bad_emotion_detected(emotion: str):
    assert detect_bad_emotion(emotion) is True


def test_good_emotion_passes():
    req = _trade(emotion="calm")
    violations = check_rules(req, calculate(req), DEFAULT_POLICY)
    assert is_blocked(violations) is False


def test_clean_trade_passes_all_rules():
    req = _trade()
    violations = check_rules(req, calculate(req), DEFAULT_POLICY)
    assert violations == []
    assert is_blocked(violations) is False
