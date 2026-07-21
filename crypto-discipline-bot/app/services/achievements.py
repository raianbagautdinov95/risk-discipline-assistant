from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trade, User, UserRecord


@dataclass
class Achievement:
    code: str
    title: str
    body: str


_ALLOWED_MILESTONES = [10, 25, 50, 100, 250, 500]
_WIN_MILESTONES = [5, 10, 25, 50, 100]


async def _get_or_create_record(session: AsyncSession, user: User) -> UserRecord:
    rec = (
        await session.execute(
            select(UserRecord).where(UserRecord.user_id == user.id)
        )
    ).scalar_one_or_none()
    if rec is None:
        rec = UserRecord(user_id=user.id)
        session.add(rec)
        await session.flush()
    return rec


def _longest_win_streak(trades: list[Trade]) -> int:
    closed = [t for t in trades if t.outcome in ("WIN", "LOSS")]
    closed.sort(key=lambda t: t.created_at)
    best = cur = 0
    for t in closed:
        if t.outcome == "WIN":
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def _longest_discipline_streak(trades: list[Trade]) -> int:
    if not trades:
        return 0
    by_day: dict[str, int] = {}
    for t in trades:
        d = t.created_at.date().isoformat()
        by_day[d] = by_day.get(d, 0) + (1 if t.decision == "FORBIDDEN" else 0)

    days = sorted(by_day.keys())
    best = cur = 0
    prev = None
    for d in days:
        if by_day[d] > 0:
            cur = 0
            prev = d
            continue
        if prev is None:
            cur = 1
        else:
            prev_date = date.fromisoformat(prev)
            this_date = date.fromisoformat(d)
            cur = (cur + 1) if (this_date - prev_date).days == 1 else 1
        if cur > best:
            best = cur
        prev = d
    return best


def _best_pnl(trades: list[Trade]) -> float:
    pnls = [t.pnl_percent for t in trades if t.pnl_percent is not None]
    return max(pnls) if pnls else 0.0


async def detect_after_close(
    session: AsyncSession, user: User
) -> list[Achievement]:
    rec = await _get_or_create_record(session, user)
    trades = (
        await session.execute(select(Trade).where(Trade.user_id == user.id))
    ).scalars().all()

    new_win_streak = _longest_win_streak(list(trades))
    new_discipline = _longest_discipline_streak(list(trades))
    new_best_pnl = _best_pnl(list(trades))
    allowed_count = sum(1 for t in trades if t.decision == "ALLOWED")
    win_count = sum(1 for t in trades if t.outcome == "WIN")

    out: list[Achievement] = []

    if new_win_streak > rec.best_win_streak and new_win_streak >= 3:
        prev = rec.best_win_streak
        rec.best_win_streak = new_win_streak
        out.append(Achievement(
            code="WIN_STREAK",
            title=f"🔥 {new_win_streak} WINs in a row — personal record!",
            body=f"Previous best: {prev}. "
                 "Don't break the streak — lock in a pause or take partial profit.",
        ))

    if new_discipline > rec.best_discipline_streak and new_discipline >= 3:
        prev = rec.best_discipline_streak
        rec.best_discipline_streak = new_discipline
        out.append(Achievement(
            code="DISCIPLINE_STREAK",
            title=f"🛡 {new_discipline} days of discipline — a record!",
            body=f"Previous: {prev}. The best trader isn't the best analyst — "
                 "it's the most disciplined one.",
        ))

    if new_best_pnl > rec.best_pnl_percent and new_best_pnl >= 1.0:
        prev = rec.best_pnl_percent
        rec.best_pnl_percent = new_best_pnl
        out.append(Achievement(
            code="BEST_PNL",
            title=f"💎 Best trade: +{new_best_pnl:.2f}%",
            body=f"Previous record: +{prev:.2f}%. "
                 "Write down what worked — repeat the conditions.",
        ))

    for m in _ALLOWED_MILESTONES:
        if allowed_count >= m and rec.allowed_milestone < m:
            rec.allowed_milestone = m
            out.append(Achievement(
                code=f"ALLOWED_{m}",
                title=f"✅ {m} checked trades",
                body="Your statistical base is growing — every check makes "
                     "the next decisions smarter.",
            ))
            break

    for m in _WIN_MILESTONES:
        if win_count >= m and rec.win_milestone < m:
            rec.win_milestone = m
            out.append(Achievement(
                code=f"WINS_{m}",
                title=f"🏆 {m} winning trades",
                body="You're consistently making yourself money. "
                     "The key is to keep the discipline going.",
            ))
            break

    await session.flush()
    return out
