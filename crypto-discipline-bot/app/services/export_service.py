from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trade, User


COLUMNS = [
    "id", "created_at", "pair", "direction", "leverage",
    "entry_price", "stop_loss", "take_profit",
    "deposit", "risk_percent", "rr_ratio",
    "decision", "score",
    "outcome", "exit_price", "pnl_percent", "closed_at",
    "reason", "setup", "emotion",
    "forbid_reasons", "notes",
]


async def export_trades_csv(session: AsyncSession, user: User) -> bytes:
    rows = (
        await session.execute(
            select(Trade)
            .where(Trade.user_id == user.id)
            .order_by(Trade.created_at.asc())
        )
    ).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(COLUMNS)
    for t in rows:
        writer.writerow([
            t.id,
            t.created_at.isoformat() if t.created_at else "",
            t.pair, t.direction, t.leverage,
            t.entry_price, t.stop_loss, t.take_profit,
            t.deposit, t.risk_percent, t.rr_ratio,
            t.decision, t.score,
            t.outcome, t.exit_price, t.pnl_percent,
            t.closed_at.isoformat() if t.closed_at else "",
            (t.reason or "").replace("\n", " "),
            (t.setup or "").replace("\n", " "),
            (t.emotion or "").replace("\n", " "),
            (t.forbid_reasons or "").replace("\n", " "),
            (t.notes or "").replace("\n", " "),
        ])
    return ("﻿" + buf.getvalue()).encode("utf-8")
