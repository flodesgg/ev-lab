"""Logging with file rotation into logs/.

Only the file gets log lines: the terminal belongs to the trainer UI, and a log line in
the middle of a timed drill would be noise (and could leak an answer).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ev_lab.config import LoggingConfig

_FORMAT = "%(asctime)s %(levelname)s %(name)s [run=%(run_id)s] %(message)s"


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


def setup_logging(cfg: LoggingConfig, log_dir: Path, run_id: str) -> logging.Logger:
    """Configure the 'ev_lab' logger with a rotating file handler. Idempotent."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ev_lab")
    logger.setLevel(cfg.level)
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()

    handler = RotatingFileHandler(
        log_dir / cfg.file, maxBytes=cfg.max_bytes, backupCount=cfg.backup_count
    )
    handler.setFormatter(logging.Formatter(_FORMAT))
    handler.addFilter(_RunIdFilter(run_id))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
