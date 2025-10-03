import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_dir: str) -> None:
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"), when="D", interval=1, backupCount=1
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


