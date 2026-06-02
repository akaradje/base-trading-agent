"""Structured Logging — JSON file (rotating) + human-readable console.

ใช้งาน:
    from basebot.logging import setup_logging
    logger = setup_logging()
    logger.info("bot started")
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler


class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines for structured parsing."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(log_file: str = "state/bot.log", level: int = logging.INFO) -> logging.Logger:
    """สร้าง logger สำหรับ basebot — JSON file + console.

    Args:
        log_file: path สำหรับ log file (จะสร้าง dir อัตโนมัติ)
        level: log level เริ่มต้น (default INFO)

    Returns:
        logging.Logger ชื่อ "basebot"
    """
    logger = logging.getLogger("basebot")

    # ป้องกัน handler ซ้ำเมื่อเรียกหลายครั้ง
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # สร้าง directory ถ้ายังไม่มี
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Rotating file: 10MB, 10 backups, UTF-8, JSON
    fh = RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=10, encoding="utf-8"
    )
    fh.setLevel(level)
    fh.setFormatter(JsonFormatter())
    logger.addHandler(fh)

    # Console: human-readable
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)

    return logger
