"""Logger setup. Forces UTF-8 — otherwise on Windows you get UnicodeEncodeError
errors when printing Cyrillic and emoji."""
import io
import logging
import sys
from pathlib import Path
from datetime import datetime


def _force_utf8_stdout():
    """On Windows stdout defaults to cp1252 and can't print Cyrillic/emoji.
    This function reconfigures stdout to UTF-8."""
    try:
        # Python 3.7+: TextIOWrapper has a reconfigure method.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback — replace stdout/stderr manually.
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

    # Restarting within a single session can create duplicate handlers.
    if logger.handlers:
        return logger

    # Console — write to the already reconfigured UTF-8 stdout.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File — explicitly set UTF-8.
    log_file = log_dir / f"{datetime.now():%Y%m%d}_trading.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
