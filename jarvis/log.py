"""Logs em arquivo rotativo, em %LOCALAPPDATA%\\SuperJarvis\\logs."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from jarvis.config import data_dir


def setup(level: int = logging.INFO) -> None:
    log_dir = data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "jarvis.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
