"""Pydantic schemas used by API and services."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class TradeRequest(BaseModel):
    """Input for trade discipline check."""

    pair: str = Field(..., examples=["BTC/USDT"])
    direction: Literal["long", "short"]
    entry_price: float = Field(..., gt=0)
    stop_loss: float | None = Field(None, gt=0)
    take_profit: float | None = Field(None, gt=0)
    deposit: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0)
    leverage: int = Field(1, ge=1)

    reason: str | None = None
    setup: str | None = None
    emotion: str | None = None
    losses_today: float = 0.0
    consecutive_losses: int = 0


class RiskCalc(BaseModel):
    """Deterministic numeric calculations."""

    risk_money: float
    sl_distance: float | None
    tp_distance: float | None
    rr_ratio: float | None
    position_size: float | None
    leveraged_risk: float
    leverage_critical: bool


class RuleViolation(BaseModel):
    code: str
    message: str
    blocking: bool = True


class CoachReport(BaseModel):
    summary: str
    pros: list[str]
    cons: list[str]
    recommendation: Literal["enter", "wait", "reduce_risk", "skip"]


class OfficerReport(BaseModel):
    summary: str
    violations: list[str]
    decision: Literal["ALLOWED", "FORBIDDEN", "WAIT"]


class TradeResponse(BaseModel):
    decision: Literal["ALLOWED", "FORBIDDEN", "WAIT"]
    score: float
    calc: RiskCalc
    violations: list[RuleViolation]
    coach: CoachReport | None = None
    officer: OfficerReport | None = None
    recommendation: str
    formatted_message: str
    disclaimer: str


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pair: str
    direction: str
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    deposit: float
    leverage: int
    risk_percent: float
    decision: str
    score: float
    rr_ratio: float | None
    outcome: str
    pnl_percent: float | None
    exit_price: float | None
    closed_at: datetime | None
    notes: str | None
    reason: str | None
    setup: str | None
    emotion: str | None
    forbid_reasons: str | None
    coach_summary: str | None
    officer_summary: str | None
    created_at: datetime


class CloseTradeRequest(BaseModel):
    outcome: Literal["WIN", "LOSS", "BREAKEVEN", "CANCELED"]
    pnl_percent: float | None = None
    exit_price: float | None = Field(None, gt=0)
    notes: str | None = None


class PositionCalcRequest(BaseModel):
    deposit: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    leverage: int = 1


class PositionCalcResult(BaseModel):
    risk_money: float
    sl_distance: float
    position_size_units: float
    position_value_usdt: float
    leverage: int
    margin_required: float
    rr_required_for_2x: float


class StatsOut(BaseModel):
    total: int
    allowed: int
    forbidden: int
    wait: int
    avg_rr: float
    avg_risk: float
    common_forbid_reasons: list[tuple[str, int]]

    # Real outcome stats — only count trades where /close was called.
    closed: int = 0
    wins: int = 0
    losses: int = 0
    breakevens: int = 0
    win_rate_pct: float = 0.0
    avg_pnl_percent: float = 0.0
    total_pnl_percent: float = 0.0


class UserSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_risk_percent: float
    max_leverage: int
    min_rr: float
    daily_loss_limit: float


class UserSettingsUpdate(BaseModel):
    max_risk_percent: float | None = Field(None, gt=0, le=100)
    max_leverage: int | None = Field(None, ge=1, le=125)
    min_rr: float | None = Field(None, gt=0)
    daily_loss_limit: float | None = Field(None, gt=0, le=100)
