"""Application logging: rotating file log under the per-user data folder."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.paths import app_data_dir

_configured = False


def log_file_path() -> Path:
    folder = app_data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "movie_splitter.log"


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("msp")
    if _configured:
        return logger
    logger.setLevel(logging.DEBUG)
    try:
        handler = RotatingFileHandler(log_file_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    _configured = True
    return logger
