from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trade, User


async def list_users(session: AsyncSession) -> list[User]:
    rows = (await session.execute(select(User))).scalars().all()
    return list(rows)


async def pending_trades(
    session: AsyncSession,
    user: User,
    older_than_minutes: int = 60,
) -> list[Trade]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    rows = (
        await session.execute(
            select(Trade)
            .where(
                Trade.user_id == user.id,
                Trade.decision == "ALLOWED",
                Trade.outcome == "NONE",
                Trade.created_at <= cutoff,
            )
            .order_by(Trade.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def trades_in_last_days(
    session: AsyncSession,
    user: User,
    days: int = 7,
) -> list[Trade]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await session.execute(
            select(Trade)
            .where(Trade.user_id == user.id, Trade.created_at >= cutoff)
            .order_by(Trade.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


def format_pending(trades: list[Trade]) -> str:
    if not trades:
        return ""
    lines = [f"🌙 Open trades: {len(trades)}", ""]
    for t in trades:
        age = datetime.now(timezone.utc) - t.created_at
        if age.days >= 1:
            ago = f"{age.days}d"
        else:
            ago = f"{age.seconds // 3600}h {(age.seconds // 60) % 60}m"
        lines.append(
            f"#{t.id}  {t.pair} {t.direction}  •  opened {ago} ago"
        )
    lines.append("")
    lines.append("Close them once the trade has played out:")
    lines.append("/close <id> win|loss|breakeven [pnl%]")
    lines.append("Example: /close 47 win 2.5")
    return "\n".join(lines)


def build_weekly_payload(trades: list[Trade]) -> dict[str, Any]:
    closed = [t for t in trades if t.outcome in ("WIN", "LOSS")]
    wins = [t for t in closed if t.outcome == "WIN"]
    losses = [t for t in closed if t.outcome == "LOSS"]
    forbidden = [t for t in trades if t.decision == "FORBIDDEN"]

    pnl_total = sum(t.pnl_percent or 0 for t in closed)
    pnl_avg = pnl_total / len(closed) if closed else 0
    win_rate = len(wins) * 100 / max(len(wins) + len(losses), 1)

    by_pair: dict[str, dict[str, Any]] = {}
    for t in closed:
        bucket = by_pair.setdefault(
            t.pair, {"wins": 0, "losses": 0, "pnl": 0.0},
        )
        if t.outcome == "WIN":
            bucket["wins"] += 1
        else:
            bucket["losses"] += 1
        bucket["pnl"] += t.pnl_percent or 0

    samples = [
        {
            "pair": t.pair,
            "direction": t.direction,
            "decision": t.decision,
            "outcome": t.outcome,
            "pnl_percent": t.pnl_percent,
            "rr": t.rr_ratio,
            "risk_percent": t.risk_percent,
            "leverage": t.leverage,
            "emotion": t.emotion,
            "setup": t.setup,
            "reason": t.reason,
            "hour": t.created_at.hour,
            "weekday": t.created_at.strftime("%A"),
            "forbid_reasons": t.forbid_reasons,
        }
        for t in trades[-30:]
    ]

    return {
        "period_days": 7,
        "totals": {
            "total_checks": len(trades),
            "allowed": sum(1 for t in trades if t.decision == "ALLOWED"),
            "forbidden": len(forbidden),
            "wait": sum(1 for t in trades if t.decision == "WAIT"),
            "closed": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(win_rate, 1),
            "total_pnl_percent": round(pnl_total, 2),
            "avg_pnl_percent": round(pnl_avg, 2),
        },
        "by_pair": {
            k: {**v, "pnl": round(v["pnl"], 2)} for k, v in by_pair.items()
        },
        "trades_sample": samples,
    }


WEEKLY_REVIEW_SYSTEM_PROMPT = """You are a trading coach who reviews a student's weekly journal.
You will receive JSON with a summary and a sample of trades.
Always answer in English.

Your task — find 1-2 SPECIFIC patterns (with numbers!) and give 1 clear recommendation.

Forbidden:
- promising profit or a result
- using the words "guarantee", "100%", "you will definitely earn"
- generic phrases like "stay disciplined" — numbers are required

Answer format, STRICTLY JSON:
{
  "summary": "1-2 sentences with the main takeaway for the week",
  "patterns": ["specific pattern 1 with numbers", "specific pattern 2"],
  "recommendation": "1 clear action for next week",
  "good": "what was done well this week"
}

Example of a good pattern: "All 3 LOSSes were ETH longs in the morning (10-12 UTC), while the evening ETH long win-rate is 75%."
Example of a bad pattern: "You have discipline problems."

If data is scarce (fewer than 5 closed trades) — honestly say "not enough data for conclusions".
"""
