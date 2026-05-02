from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select

from app.bot.keyboards import trade_from_signal_kb
from app.config import settings as cfg
from app.database import AsyncSessionLocal
from app.models import User
from app.services.signal_client import SignalClient

logger = logging.getLogger(__name__)


def _signal_key(s: dict) -> str:
    return f"{s.get('symbol','?')}:{s.get('timestamp', 0)}"


def _format(s: dict) -> str:
    arrow = "🟢 BUY" if s.get("action") == "BUY" else "🔴 SELL"
    sym = s.get("symbol", "?")
    conf = s.get("confidence")
    rr = s.get("risk_reward")
    pct = conf if (isinstance(conf, (int, float)) and conf > 1) else (conf or 0) * 100
    return (
        f"📡 НОВЫЙ СИГНАЛ\n"
        f"{arrow}  {sym}\n"
        f"  entry: {s.get('entry')}   SL: {s.get('stop_loss')}   "
        f"TP: {s.get('take_profit')}\n"
        f"  R:R={rr:.2f}   confidence={pct:.0f}%   "
        f"тренд 1H: {s.get('trend_1h','?')}\n"
        f"  • " + " · ".join((s.get('reasons') or [])[:3])
    )


async def signal_notifier_loop(bot: Bot, interval_sec: int = 60) -> None:
    client = SignalClient(cfg.signal_bot_url)
    delivered: set[str] = set()
    logger.info(
        "Signal notifier started, interval=%ds, signal_bot=%s",
        interval_sec, cfg.signal_bot_url,
    )

    while True:
        try:
            signals = await client.get_active()
        except Exception as exc:
            logger.debug("notifier: signal-bot unreachable: %s", exc)
            await asyncio.sleep(interval_sec)
            continue

        fresh = []
        for s in signals or []:
            action = (s.get("action") or "HOLD").upper()
            if action not in ("BUY", "SELL"):
                continue
            key = _signal_key(s)
            if key in delivered:
                continue
            fresh.append((key, s))

        if fresh:
            async with AsyncSessionLocal() as session:
                users = (await session.execute(select(User))).scalars().all()
            for key, s in fresh:
                text = _format(s)
                kb = trade_from_signal_kb(s.get("symbol", ""))
                for u in users:
                    try:
                        await bot.send_message(
                            chat_id=u.telegram_id, text=text, reply_markup=kb,
                        )
                    except Exception as exc:
                        logger.warning(
                            "notifier: failed to send to %s: %s", u.telegram_id, exc,
                        )
                delivered.add(key)
            if len(delivered) > 200:
                delivered = set(list(delivered)[-200:])

        await asyncio.sleep(interval_sec)
