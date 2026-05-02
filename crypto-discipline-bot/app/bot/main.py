from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import router
from app.bot.notifier import signal_notifier_loop
from app.bot.scheduler import scheduler_loop
from app.config import settings


async def main() -> None:
    logging.basicConfig(level=settings.log_level)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.getLogger(__name__).info("Bot is starting...")

    notifier_task = asyncio.create_task(signal_notifier_loop(bot, interval_sec=60))
    scheduler_task = asyncio.create_task(scheduler_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        notifier_task.cancel()
        scheduler_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
