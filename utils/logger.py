import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "trading_bot") -> logging.Logger:



    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)


    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)


    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = log_dir / f"{datetime.now():%Y%m%d}_trading.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger