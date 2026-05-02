from __future__ import annotations

from app.schemas import PositionCalcRequest, PositionCalcResult


def calculate_position(req: PositionCalcRequest) -> PositionCalcResult:
    risk_money = req.deposit * (req.risk_percent / 100.0)
    sl_distance = abs(req.entry_price - req.stop_loss)
    if sl_distance <= 0:
        raise ValueError("Stop-loss distance must be > 0")

    position_size_units = risk_money / sl_distance
    position_value = position_size_units * req.entry_price
    margin = position_value / max(req.leverage, 1)
    rr2_distance = sl_distance * 2

    return PositionCalcResult(
        risk_money=round(risk_money, 4),
        sl_distance=round(sl_distance, 8),
        position_size_units=round(position_size_units, 8),
        position_value_usdt=round(position_value, 2),
        leverage=req.leverage,
        margin_required=round(margin, 2),
        rr_required_for_2x=round(rr2_distance, 8),
    )
