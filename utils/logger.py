"""Настройка логгера. Принудительно использует UTF-8 — иначе на Windows
падают ошибки UnicodeEncodeError при выводе кириллицы и эмодзи."""
import io
import logging
import sys
from pathlib import Path
from datetime import datetime


def _force_utf8_stdout():
    """На Windows stdout по умолчанию cp1252 и не умеет печатать кириллицу/эмодзи.
    Эта функция переконфигурирует stdout в UTF-8."""
    try:
        # Python 3.7+: у TextIOWrapper есть метод reconfigure.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback — заменяем stdout/stderr вручную.
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass


def setup_logger(name: str = "trading_bot") -> logging.Logger:
    _force_utf8_stdout()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Перезапуск из одной сессии может создать дубли хендлеров.
    if logger.handlers:
        return logger

    # Консоль — пишем в уже переконфигурированный UTF-8 stdout.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файл — явно задаём UTF-8.
    log_file = log_dir / f"{datetime.now():%Y%m%d}_trading.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
