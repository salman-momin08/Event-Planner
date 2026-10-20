from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .config import Settings
from .logger import Logger
from .security import RateLimiter

if TYPE_CHECKING:
    from .ai.runtime import AiRuntime


@dataclass
class Context:
    """Everything a request handler needs, injected so tests are deterministic."""

    settings: Settings
    db: sqlite3.Connection
    clock: Callable[[], datetime]
    logger: Logger
    limiters: dict[str, RateLimiter]
    ai: "AiRuntime"
    extras: dict = field(default_factory=dict)
