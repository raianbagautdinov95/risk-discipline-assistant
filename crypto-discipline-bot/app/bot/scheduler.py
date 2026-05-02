from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy import select

from app.bot.keyboards import morning_plan_kb
from app.config import settings as cfg
from app.database import AsyncSessionLocal
from app.models import User
from app.services import daily_plan_service, reminders
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


MORNING_CHECKIN_HOUR = 9
DAILY_REMINDER_HOUR = 22
WEEKLY_REVIEW_WEEKDAY = 6
WEEKLY_REVIEW_HOUR = 18


async def _send_morning_checkin(bot: Bot) -> None:
    sent = 0
    text = (
        "🌅 Доброе утро! Какой план на сегодня?\n\n"
        "Выбор фиксируется в твоём журнале. Вечером сравним с реальностью."
    )
    async with AsyncSessionLocal() as session:
        users = await reminders.list_users(session)
        for u in users:
            try:
                await bot.send_message(
                    chat_id=u.telegram_id,
                    text=text,
                    reply_markup=morning_plan_kb(),
                )
                sent += 1
            except Exception as exc:
                logger.warning("morning checkin failed for %s: %s", u.telegram_id, exc)
        await session.commit()
    logger.info("Morning check-in sent to %d user(s).", sent)


async def _send_daily_reminders(bot: Bot) -> None:
    sent = 0
    today = datetime.now(timezone.utc).date()
    async with AsyncSessionLocal() as session:
        users = await reminders.list_users(session)
        for u in users:
            try:
                pending = await reminders.pending_trades(session, u)
                plan = await daily_plan_service.get_plan(session, u, today)
                today_trades = await reminders.trades_in_last_days(session, u, days=1)
                today_attempts = sum(
                    1 for t in today_trades if t.created_at.date() == today
                )
                blocks: list[str] = []

                if plan is not None:
                    plan_label = daily_plan_service.INTENT_LABELS[plan.intent]
                    msg = f"📋 План на сегодня: {plan_label}\n"
                    msg += f"   Реальность: {today_attempts} проверок"
                    if plan.intent == "watch" and today_attempts > 0:
                        msg += "\n   ⚠️ Планировал не торговать — но было " \
                            f"{today_attempts} попытк(а/и)."
                    elif plan.intent == "few" and today_attempts > 3:
                        msg += "\n   ⚠️ План был ≤3 — превышение."
                    elif plan.intent == "off" and today_attempts > 0:
                        msg += "\n   ⚠️ Планировал выходной — а торговал."
                    elif today_attempts <= 3:
                        msg += "\n   ✅ Следуешь плану."
                    blocks.append(msg)

                if pending:
                    blocks.append(reminders.format_pending(pending))

                if not blocks:
                    continue

                await bot.send_message(
                    chat_id=u.telegram_id,
                    text="\n\n".join(blocks),
                )
                sent += 1
            except Exception as exc:
                logger.warning("daily reminder failed for %s: %s", u.telegram_id, exc)
        await session.commit()
    logger.info("Daily reminders sent to %d user(s).", sent)


async def _build_review_text(client: OllamaClient | None, payload: dict) -> str:
    totals = payload["totals"]
    header = (
        "📊 Еженедельный обзор\n"
        f"За 7 дней: {totals['total_checks']} проверок, "
        f"{totals['allowed']} ALLOWED, {totals['forbidden']} FORBIDDEN.\n"
        f"Закрытых: {totals['closed']}  •  Win-rate: {totals['win_rate_pct']}%  "
        f"•  P&L: {totals['total_pnl_percent']:+.2f}%\n"
    )
    if not client:
        return header + "\n💡 Подключи Ollama в .env, чтобы получать AI-инсайты."
    if totals["closed"] < 3:
        return header + (
            "\n💡 Закрытых сделок мало (<3) — для AI-выводов не хватит данных. "
            "Закрой сделки командой /close."
        )

    try:
        data = await client.chat_json(
            system=reminders.WEEKLY_REVIEW_SYSTEM_PROMPT,
            user_payload=payload,
            temperature=0.3,
        )
    except Exception as exc:
        logger.warning("weekly review LLM call failed: %s", exc)
        return header + f"\n⚠️ AI-обзор временно недоступен ({exc.__class__.__name__})."

    summary = str(data.get("summary", "")).strip()
    patterns = [str(p) for p in (data.get("patterns") or [])][:3]
    rec = str(data.get("recommendation", "")).strip()
    good = str(data.get("good", "")).strip()

    body = [header]
    if summary:
        body.append("🎯 " + summary)
    if patterns:
        body.append("\n🔎 Паттерны:")
        for i, p in enumerate(patterns, 1):
            body.append(f"  {i}. {p}")
    if rec:
        body.append(f"\n💡 Рекомендация: {rec}")
    if good:
        body.append(f"\n✅ Что хорошо: {good}")
    body.append(
        "\n⚠️ Это не финансовая рекомендация. Я опираюсь только на твой журнал."
    )
    return "\n".join(body)


async def _send_weekly_reviews(bot: Bot) -> None:
    sent = 0
    client = (
        OllamaClient(cfg.ollama_base_url, cfg.ollama_model_coach)
        if cfg.ollama_base_url else None
    )

    async with AsyncSessionLocal() as session:
        users = await reminders.list_users(session)
        for u in users:
            try:
                trades = await reminders.trades_in_last_days(session, u, days=7)
                if not trades:
                    continue
                payload = reminders.build_weekly_payload(trades)
                review = await _build_review_text(client, payload)
                await bot.send_message(chat_id=u.telegram_id, text=review)
                sent += 1
            except Exception as exc:
                logger.warning("weekly review failed for %s: %s", u.telegram_id, exc)
        await session.commit()
    logger.info("Weekly reviews sent to %d user(s).", sent)


async def scheduler_loop(bot: Bot) -> None:
    last_morning = ""
    last_daily = ""
    last_weekly = ""

    logger.info(
        "Scheduler started: morning=%02d:00, daily=%02d:00, "
        "weekly=Sun %02d:00 (UTC)",
        MORNING_CHECKIN_HOUR, DAILY_REMINDER_HOUR, WEEKLY_REVIEW_HOUR,
    )

    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()

            if now.hour == MORNING_CHECKIN_HOUR and last_morning != today:
                last_morning = today
                await _send_morning_checkin(bot)

            if now.hour == DAILY_REMINDER_HOUR and last_daily != today:
                last_daily = today
                await _send_daily_reminders(bot)

            if (
                now.weekday() == WEEKLY_REVIEW_WEEKDAY
                and now.hour == WEEKLY_REVIEW_HOUR
                and last_weekly != today
            ):
                last_weekly = today
                await _send_weekly_reviews(bot)

        except Exception as exc:
            logger.warning("Scheduler iteration error: %s", exc)

        await asyncio.sleep(60)


async def manual_morning_checkin(bot: Bot, telegram_id: int) -> None:
    await bot.send_message(
        chat_id=telegram_id,
        text="🌅 Какой план на сегодня?\n\nВыбери — вечером сравним с реальностью.",
        reply_markup=morning_plan_kb(),
    )


async def manual_remind(bot: Bot, telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
        ).scalar_one_or_none()
        if user is None:
            return "Сначала отправь /start чтобы зарегистрироваться."
        pending = await reminders.pending_trades(session, user, older_than_minutes=0)
    if not pending:
        return "🎉 Все сделки закрыты — журнал актуален."
    return reminders.format_pending(pending)


async def manual_review(bot: Bot, telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
        ).scalar_one_or_none()
        if user is None:
            return "Сначала отправь /start чтобы зарегистрироваться."
        trades = await reminders.trades_in_last_days(session, user, days=7)
    if not trades:
        return "За последнюю неделю сделок нет."
    payload = reminders.build_weekly_payload(trades)
    client = (
        OllamaClient(cfg.ollama_base_url, cfg.ollama_model_coach)
        if cfg.ollama_base_url else None
    )
    return await _build_review_text(client, payload)
