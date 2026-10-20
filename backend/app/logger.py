from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone


class Logger:
    """JSON-lines logger. Callers must never pass bodies, cookies, prompts or secrets."""

    def __init__(self, write: Callable[[str], None] | None = None, silent: bool = False) -> None:
        self._write = write or (lambda line: sys.stdout.write(line + "\n"))
        self._silent = silent

    def _log(self, level: str, msg: str, fields: dict) -> None:
        if self._silent:
            return
        record = {"ts": datetime.now(timezone.utc).isoformat(), "level": level, "msg": msg, **fields}
        self._write(json.dumps(record, default=str))

    def info(self, msg: str, **fields) -> None:
        self._log("info", msg, fields)

    def warn(self, msg: str, **fields) -> None:
        self._log("warn", msg, fields)

    def error(self, msg: str, **fields) -> None:
        self._log("error", msg, fields)
