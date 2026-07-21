from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyPlan, User


INTENT_LABELS = {
    "watch": "👀 Watch calmly",
    "few": "📊 Up to 3 trades",
    "active": "🔥 Actively hunt",
    "off": "🛌 Not trading today",
}

INTENT_DESCRIPTIONS = {
    "watch": "observation only, no entries",
    "few": "no more than 3 trades, no emotions",
    "active": "actively hunting for setups",
    "off": "day off, no trading",
}


def is_valid_intent(value: str) -> bool:
    return value in INTENT_LABELS


async def upsert_plan(
    session: AsyncSession,
    user: User,
    intent: str,
    plan_date: date | None = None,
    note: str | None = None,
) -> DailyPlan:
    plan_date = plan_date or date.today()
    existing = (
        await session.execute(
            select(DailyPlan).where(
                DailyPlan.user_id == user.id,
                DailyPlan.plan_date == plan_date,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = DailyPlan(
            user_id=user.id,
            plan_date=plan_date,
            intent=intent,
            note=note,
        )
        session.add(existing)
    else:
        existing.intent = intent
        if note is not None:
            existing.note = note
    await session.flush()
    return existing


async def get_plan(
    session: AsyncSession, user: User, plan_date: date | None = None,
) -> DailyPlan | None:
    plan_date = plan_date or date.today()
    return (
        await session.execute(
            select(DailyPlan).where(
                DailyPlan.user_id == user.id,
                DailyPlan.plan_date == plan_date,
            )
        )
    ).scalar_one_or_none()
