from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

SCHEMA_V1 = """
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('wedding','birthday','community')),
  title TEXT NOT NULL,
  event_date TEXT NOT NULL,
  attendance INTEGER NOT NULL CHECK (attendance >= 1),
  location TEXT NOT NULL DEFAULT '',
  budget_cents INTEGER NOT NULL DEFAULT 0 CHECK (budget_cents >= 0),
  currency TEXT NOT NULL DEFAULT 'USD',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_events_owner ON events(owner_id);
CREATE TABLE budget_categories (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL COLLATE NOCASE,
  planned_cents INTEGER NOT NULL DEFAULT 0 CHECK (planned_cents >= 0),
  UNIQUE (event_id, name)
);
CREATE TABLE vendors (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'researching'
    CHECK (status IN ('researching','contacted','quoted','booked','declined')),
  quote_cents INTEGER CHECK (quote_cents IS NULL OR quote_cents >= 0),
  contact TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_vendors_event ON vendors(event_id);
CREATE TABLE expenses (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES budget_categories(id) ON DELETE RESTRICT,
  vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
  description TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  spent_on TEXT NOT NULL
);
CREATE INDEX idx_expenses_event ON expenses(event_id);
CREATE INDEX idx_expenses_category ON expenses(category_id);
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  title TEXT NOT NULL COLLATE NOCASE,
  description TEXT NOT NULL DEFAULT '',
  due_date TEXT,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done')),
  category TEXT NOT NULL DEFAULT '',
  vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','template','ai')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (event_id, title)
);
CREATE INDEX idx_tasks_event_due ON tasks(event_id, due_date);
CREATE TABLE task_dependencies (
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  depends_on_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on_id),
  CHECK (task_id <> depends_on_id)
);
CREATE TABLE ai_plan_versions (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  parent_id INTEGER REFERENCES ai_plan_versions(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','applied','discarded')),
  instruction TEXT NOT NULL DEFAULT '',
  preferences TEXT NOT NULL DEFAULT '',
  plan_json TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_plans_event ON ai_plan_versions(event_id, created_at);
CREATE TABLE security_events (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  user_id INTEGER,
  type TEXT NOT NULL,
  ip_hash TEXT
);
CREATE INDEX idx_security_events_at ON security_events(at);
"""

MIGRATIONS = [SCHEMA_V1]


def open_database(path: str = ":memory:") -> sqlite3.Connection:
    """One connection, autocommit mode; transactions are explicit via `transaction()`.

    All database access happens on the event-loop thread, so the single connection is never
    used concurrently.
    """
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    if path != ":memory:":
        db.execute("PRAGMA journal_mode = WAL")
    _migrate(db)
    return db


def _migrate(db: sqlite3.Connection) -> None:
    current = db.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current, len(MIGRATIONS)):
        db.execute("BEGIN")
        try:
            for statement in MIGRATIONS[version].split(";\n"):
                if statement.strip():
                    db.execute(statement)
            db.execute(f"PRAGMA user_version = {version + 1}")
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise


@contextmanager
def transaction(db: sqlite3.Connection) -> Iterator[None]:
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def update_row(
    db: sqlite3.Connection,
    table: str,
    column_map: Mapping[str, str],
    data: Mapping[str, object],
    where_sql: str,
    where_params: tuple,
) -> None:
    """Table/column names come only from hard-coded maps; values are always bound."""
    keys = [k for k in data if k in column_map]
    if not keys:
        return
    sets = ", ".join(f"{column_map[k]} = ?" for k in keys)
    db.execute(f"UPDATE {table} SET {sets} WHERE {where_sql}", (*[data[k] for k in keys], *where_params))


def is_unique_violation(err: Exception) -> bool:
    return isinstance(err, sqlite3.IntegrityError) and "UNIQUE constraint failed" in str(err)
