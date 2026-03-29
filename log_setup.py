"""
Centralised logging — adapted from the Nuginix Monitoring pattern.

Features:
  - TimedRotatingFileHandler with ISO-8601 timestamps in rotated filenames
    (e.g. ``server.2026-03-28_14-30-00.log``).
  - A symlink ``server.log`` always points to the current log file so
    ``tail -f logs/server.log`` works across rollovers.
  - Console handler for foreground / debug runs.
  - Size cap between timed rotations (default 50 MB).
"""

import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from config import LOG_DIR, LOG_LEVEL, LOG_MAX_MB, LOG_BACKUP_COUNT, LOG_ROTATE_WHEN

_LOG_FILE = LOG_DIR / "server.log"
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(client)s] %(message)s"
_LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class _RequestContextFilter(logging.Filter):
    """Inject ``client`` (IP) into every log record. Falls back to '-'
    when called outside a request (e.g. during startup)."""

    def filter(self, record):
        if not hasattr(record, "client"):
            record.client = "-"
        return True


class _SymlinkTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that:
    1. Names rotated files with a human-readable timestamp.
    2. Enforces a size cap between timed rotations.
    3. Keeps a ``server.log`` symlink pointing to the active file.
    """

    def __init__(self, filename, when="midnight", interval=1,
                 backupCount=14, max_bytes=0, **kwargs):
        self._max_bytes = max_bytes
        raw = Path(filename)
        self._base_path = raw.parent.resolve() / raw.name

        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        self._actual_file = (
            self._base_path.parent
            / f"{self._base_path.stem}.{ts}{self._base_path.suffix}"
        )
        super().__init__(
            str(self._actual_file), when=when, interval=interval,
            backupCount=backupCount, encoding="utf-8", **kwargs,
        )
        self._refresh_symlink()

    def _refresh_symlink(self):
        link = self._base_path
        target = Path(self.baseFilename)
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(target.name)
        except OSError:
            pass

    def shouldRollover(self, record):
        if self._max_bytes and os.path.isfile(self.baseFilename):
            if os.path.getsize(self.baseFilename) >= self._max_bytes:
                return True
        return super().shouldRollover(record)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        new_name = (
            self._base_path.parent
            / f"{self._base_path.stem}.{ts}{self._base_path.suffix}"
        )
        if new_name.exists():
            new_name = (
                self._base_path.parent
                / f"{self._base_path.stem}.{ts}.{os.getpid()}{self._base_path.suffix}"
            )
        self.baseFilename = str(new_name)
        if not self.delay:
            self.stream = self._open()
        self._refresh_symlink()
        self.rolloverAt = self.computeRollover(int(time.time()))
        if self.backupCount > 0:
            self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        parent = self._base_path.parent
        stem = self._base_path.stem
        suffix = self._base_path.suffix
        current = Path(self.baseFilename).name
        rotated = sorted(
            (f for f in parent.iterdir()
             if f.name.startswith(stem + ".") and f.name.endswith(suffix)
             and f.is_file() and f.name != current and f.name != self._base_path.name),
            key=lambda p: p.stat().st_mtime,
        )
        while len(rotated) > self.backupCount:
            oldest = rotated.pop(0)
            try:
                oldest.unlink()
            except OSError:
                pass


def configure_logging(level=None):
    """Set up root logger with console + rotating-file handlers.
    Call once at startup."""
    level = level or LOG_LEVEL
    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()

    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    ctx_filter = _RequestContextFilter()
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FMT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(ctx_filter)
    root.addHandler(console)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = _SymlinkTimedRotatingFileHandler(
            str(_LOG_FILE),
            when=LOG_ROTATE_WHEN, interval=1,
            backupCount=LOG_BACKUP_COUNT,
            max_bytes=LOG_MAX_MB * 1024 * 1024,
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ctx_filter)
        root.addHandler(file_handler)
    except OSError:
        root.warning("Could not open log file %s; console only", _LOG_FILE)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
