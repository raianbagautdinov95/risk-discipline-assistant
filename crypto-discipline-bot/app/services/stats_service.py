from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Trade, User, UserSettings
from app.schemas import (
    CloseTradeRequest,
    StatsOut,
    TradeOut,
    TradeRequest,
    TradeResponse,
)


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
) -> User:
    user = (
        await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.settings))
        )
    ).scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        user.settings = UserSettings()
        session.add(user)
        await session.flush()
        await session.refresh(user, attribute_names=["settings"])
    elif username and user.username != username:
        user.username = username
    return user


async def save_trade(
    session: AsyncSession,
    user: User,
    req: TradeRequest,
    resp: TradeResponse,
) -> Trade:
    forbid_reasons = (
        " | ".join(v.message for v in resp.violations) if resp.violations else None
    )
    trade = Trade(
        user_id=user.id,
        pair=req.pair,
        direction=req.direction,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        deposit=req.deposit,
        risk_percent=req.risk_percent,
        leverage=req.leverage,
        reason=req.reason,
        setup=req.setup,
        emotion=req.emotion,
        losses_today=req.losses_today,
        consecutive_losses=req.consecutive_losses,
        decision=resp.decision,
        score=resp.score,
        rr_ratio=resp.calc.rr_ratio,
        forbid_reasons=forbid_reasons,
        coach_summary=resp.coach.summary if resp.coach else None,
        officer_summary=resp.officer.summary if resp.officer else None,
    )
    session.add(trade)
    await session.flush()
    return trade


async def list_recent_trades(
    session: AsyncSession, user: User, limit: int = 10,
) -> list[TradeOut]:
    rows = (
        await session.execute(
            select(Trade)
            .where(Trade.user_id == user.id)
            .order_by(Trade.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [TradeOut.model_validate(t) for t in rows]


async def close_trade(
    session: AsyncSession,
    user: User,
    trade_id: int,
    payload: CloseTradeRequest,
) -> Trade | None:
    trade = (
        await session.execute(
            select(Trade).where(Trade.id == trade_id, Trade.user_id == user.id)
        )
    ).scalar_one_or_none()
    if trade is None:
        return None
    trade.outcome = payload.outcome
    trade.pnl_percent = payload.pnl_percent
    trade.exit_price = payload.exit_price
    trade.notes = payload.notes
    trade.closed_at = datetime.now(timezone.utc)
    await session.flush()
    return trade


async def compute_stats(session: AsyncSession, user: User) -> StatsOut:
    rows = (
        await session.execute(select(Trade).where(Trade.user_id == user.id))
    ).scalars().all()

    total = len(rows)
    if total == 0:
        return StatsOut(
            total=0, allowed=0, forbidden=0, wait=0,
            avg_rr=0.0, avg_risk=0.0, common_forbid_reasons=[],
        )

    allowed = sum(1 for t in rows if t.decision == "ALLOWED")
    forbidden = sum(1 for t in rows if t.decision == "FORBIDDEN")
    wait = sum(1 for t in rows if t.decision == "WAIT")

    rr_values = [t.rr_ratio for t in rows if t.rr_ratio is not None]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0
    avg_risk = round(sum(t.risk_percent for t in rows) / total, 2)

    counter: Counter[str] = Counter()
    for t in rows:
        if t.decision == "FORBIDDEN" and t.forbid_reasons:
            for piece in t.forbid_reasons.split("|"):
                key = piece.strip()
                if key:
                    counter[key] += 1
    common = counter.most_common(5)

    closed_rows = [t for t in rows if t.outcome in ("WIN", "LOSS", "BREAKEVEN")]
    wins = sum(1 for t in closed_rows if t.outcome == "WIN")
    losses = sum(1 for t in closed_rows if t.outcome == "LOSS")
    breakevens = sum(1 for t in closed_rows if t.outcome == "BREAKEVEN")
    closed = len(closed_rows)
    win_rate = round(wins * 100 / max(wins + losses, 1), 1) if (wins + losses) else 0.0
    pnl_values = [t.pnl_percent for t in closed_rows if t.pnl_percent is not None]
    avg_pnl = round(sum(pnl_values) / len(pnl_values), 2) if pnl_values else 0.0
    total_pnl = round(sum(pnl_values), 2) if pnl_values else 0.0

    return StatsOut(
        total=total,
        allowed=allowed,
        forbidden=forbidden,
        wait=wait,
        avg_rr=avg_rr,
        avg_risk=avg_risk,
        common_forbid_reasons=common,
        closed=closed,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        win_rate_pct=win_rate,
        avg_pnl_percent=avg_pnl,
        total_pnl_percent=total_pnl,
    )
