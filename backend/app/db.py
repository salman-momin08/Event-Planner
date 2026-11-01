"""Database engine & migration manager: PostgreSQL (Production) + SQLite (Local Dev / Testing fallback).

When `DATABASE_URL` starts with `postgresql://` or `postgres://`, connects using `psycopg` (v3) with a
unified connection/cursor adapter that translates `?` parameter placeholders, `COLLATE NOCASE`,
`INSERT OR IGNORE`, and `cur.lastrowid` automatically so all application services run unmodified on both
PostgreSQL and SQLite.
"""
from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

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

SCHEMA_V2 = """
CREATE TABLE guests (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact TEXT NOT NULL DEFAULT '',
  rsvp_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (rsvp_status IN ('pending','attending','declined','maybe')),
  party_size INTEGER NOT NULL DEFAULT 1 CHECK (party_size >= 1 AND party_size <= 20),
  dietary TEXT NOT NULL DEFAULT 'none'
    CHECK (dietary IN ('none','vegetarian','vegan','halal','kosher','gluten_free','nut_allergy','other')),
  table_group TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX idx_guests_event ON guests(event_id);
CREATE TABLE schedule_items (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  start_time TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duration_minutes >= 5 AND duration_minutes <= 720),
  title TEXT NOT NULL,
  location_zone TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_schedule_event ON schedule_items(event_id, start_time);
CREATE TABLE decor_analyses (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  space_type TEXT NOT NULL
    CHECK (space_type IN ('open_garden','party_hall','house_room','rooftop','banquet_lawn','other')),
  custom_space_type TEXT NOT NULL DEFAULT '',
  lighting_mood TEXT NOT NULL DEFAULT 'warm_ambient',
  style_pref TEXT NOT NULL DEFAULT '',
  has_image INTEGER NOT NULL DEFAULT 0,
  analysis_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','applied')),
  model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_decor_event ON decor_analyses(event_id, created_at);
CREATE TABLE invitations (
  event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  headline TEXT NOT NULL DEFAULT '',
  subheadline TEXT NOT NULL DEFAULT '',
  host_line TEXT NOT NULL DEFAULT '',
  body_text TEXT NOT NULL DEFAULT '',
  dress_code TEXT NOT NULL DEFAULT '',
  theme_style TEXT NOT NULL DEFAULT 'royal_indigo',
  layout_style TEXT NOT NULL DEFAULT 'classic_crest',
  updated_at TEXT NOT NULL
);
"""

SCHEMA_V3 = ""

MIGRATIONS = [SCHEMA_V1, SCHEMA_V2, SCHEMA_V3]

# PostgreSQL DDL equivalent with BIGINT for millisecond epochs & monetary cents and CITEXT-like case-insensitive uniqueness
PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL,
  created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  owner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('wedding','birthday','community')),
  title TEXT NOT NULL,
  event_date TEXT NOT NULL,
  attendance INTEGER NOT NULL CHECK (attendance >= 1),
  location TEXT NOT NULL DEFAULT '',
  budget_cents BIGINT NOT NULL DEFAULT 0 CHECK (budget_cents >= 0),
  currency TEXT NOT NULL DEFAULT 'USD',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_owner ON events(owner_id);
CREATE TABLE IF NOT EXISTS budget_categories (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  planned_cents BIGINT NOT NULL DEFAULT 0 CHECK (planned_cents >= 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_categories_event_name_ci ON budget_categories(event_id, LOWER(name));
CREATE TABLE IF NOT EXISTS vendors (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'researching'
    CHECK (status IN ('researching','contacted','quoted','booked','declined')),
  quote_cents BIGINT CHECK (quote_cents IS NULL OR quote_cents >= 0),
  contact TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_vendors_event ON vendors(event_id);
CREATE TABLE IF NOT EXISTS expenses (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  category_id BIGINT NOT NULL REFERENCES budget_categories(id) ON DELETE RESTRICT,
  vendor_id BIGINT REFERENCES vendors(id) ON DELETE SET NULL,
  description TEXT NOT NULL,
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  spent_on TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_event ON expenses(event_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
CREATE TABLE IF NOT EXISTS tasks (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  due_date TEXT,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done')),
  category TEXT NOT NULL DEFAULT '',
  vendor_id BIGINT REFERENCES vendors(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual','template','ai')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_event_title_ci ON tasks(event_id, LOWER(title));
CREATE INDEX IF NOT EXISTS idx_tasks_event_due ON tasks(event_id, due_date);
CREATE TABLE IF NOT EXISTS task_dependencies (
  task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  depends_on_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on_id),
  CHECK (task_id <> depends_on_id)
);
CREATE TABLE IF NOT EXISTS ai_plan_versions (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  parent_id BIGINT REFERENCES ai_plan_versions(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','applied','discarded')),
  instruction TEXT NOT NULL DEFAULT '',
  preferences TEXT NOT NULL DEFAULT '',
  plan_json TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_plans_event ON ai_plan_versions(event_id, created_at);
CREATE TABLE IF NOT EXISTS security_events (
  id BIGSERIAL PRIMARY KEY,
  at TEXT NOT NULL,
  user_id BIGINT,
  type TEXT NOT NULL,
  ip_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_security_events_at ON security_events(at);
CREATE TABLE IF NOT EXISTS guests (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact TEXT NOT NULL DEFAULT '',
  rsvp_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (rsvp_status IN ('pending','attending','declined','maybe')),
  party_size INTEGER NOT NULL DEFAULT 1 CHECK (party_size >= 1 AND party_size <= 20),
  dietary TEXT NOT NULL DEFAULT 'none'
    CHECK (dietary IN ('none','vegetarian','vegan','halal','kosher','gluten_free','nut_allergy','other')),
  table_group TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_guests_event ON guests(event_id);
CREATE TABLE IF NOT EXISTS schedule_items (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  start_time TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK (duration_minutes >= 5 AND duration_minutes <= 720),
  title TEXT NOT NULL,
  location_zone TEXT NOT NULL DEFAULT '',
  owner TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_schedule_event ON schedule_items(event_id, start_time);
CREATE TABLE IF NOT EXISTS decor_analyses (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  space_type TEXT NOT NULL
    CHECK (space_type IN ('open_garden','party_hall','house_room','rooftop','banquet_lawn','other')),
  custom_space_type TEXT NOT NULL DEFAULT '',
  lighting_mood TEXT NOT NULL DEFAULT 'warm_ambient',
  style_pref TEXT NOT NULL DEFAULT '',
  has_image INTEGER NOT NULL DEFAULT 0,
  analysis_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','applied')),
  model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decor_event ON decor_analyses(event_id, created_at);
CREATE TABLE IF NOT EXISTS invitations (
  event_id BIGINT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  headline TEXT NOT NULL DEFAULT '',
  subheadline TEXT NOT NULL DEFAULT '',
  host_line TEXT NOT NULL DEFAULT '',
  body_text TEXT NOT NULL DEFAULT '',
  dress_code TEXT NOT NULL DEFAULT '',
  theme_style TEXT NOT NULL DEFAULT 'royal_indigo',
  layout_style TEXT NOT NULL DEFAULT 'classic_crest',
  updated_at TEXT NOT NULL
);
ALTER TABLE invitations DROP COLUMN IF EXISTS rsvp_contact;
ALTER TABLE invitations DROP COLUMN IF EXISTS rsvp_deadline;
"""

_SERIAL_ID_TABLES = {
    "users",
    "events",
    "budget_categories",
    "vendors",
    "expenses",
    "tasks",
    "ai_plan_versions",
    "security_events",
    "guests",
    "schedule_items",
    "decor_analyses",
}


class PgRow(dict):
    """Row object supporting both `row['col']` mapping access and `row[0]` positional indexing like `sqlite3.Row`."""

    def __init__(self, columns: Sequence[str], values: Sequence[Any]) -> None:
        super().__init__(zip(columns, values))
        self._values = tuple(values)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


def _translate_sql_for_postgres(sql: str) -> tuple[str, bool]:
    """Translates SQLite-dialect SQL into PostgreSQL-compatible SQL."""
    s = sql.strip()
    # Replace '?' placeholders outside string literals with '%s'
    out: list[str] = []
    in_quote = False
    for ch in s:
        if ch == "'":
            in_quote = not in_quote
            out.append(ch)
        elif ch == "?" and not in_quote:
            out.append("%s")
        else:
            out.append(ch)
    pg_sql = "".join(out)

    # Translate ORDER BY name COLLATE NOCASE -> ORDER BY LOWER(name)
    pg_sql = re.sub(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s+COLLATE\s+NOCASE\b", r"LOWER(\1)", pg_sql, flags=re.I)

    # Translate INSERT OR IGNORE INTO table ... -> INSERT INTO table ... ON CONFLICT DO NOTHING
    if re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b", pg_sql, flags=re.I):
        pg_sql = re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", pg_sql, count=1, flags=re.I)
        pg_sql = f"{pg_sql.rstrip(';')} ON CONFLICT DO NOTHING"

    # Append RETURNING id for single-row INSERTs into serial-id tables so cur.lastrowid works identically
    needs_returning = False
    m = re.match(r"^\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\b", pg_sql, flags=re.I)
    if m and m.group(1).lower() in _SERIAL_ID_TABLES and "RETURNING " not in pg_sql.upper() and "ON CONFLICT" not in pg_sql.upper():
        pg_sql = f"{pg_sql.rstrip(';')} RETURNING id"
        needs_returning = True

    return pg_sql, needs_returning


def _normalize_pg_dsn(dsn: str, *, decode_percent: bool = False) -> str:
    """Safely URL-encodes passwords containing raw '@', '%', '#', or spaces in a postgresql:// URI."""
    s = dsn.strip()
    if "://" not in s:
        return s
    if "@" in s:
        scheme, rest = s.split("://", 1)
        userinfo, hostpart = rest.rsplit("@", 1)
        if ":" in userinfo:
            user, raw_password = userinfo.split(":", 1)
            pw = unquote(raw_password) if decode_percent else raw_password
            userinfo = f"{quote(unquote(user), safe='')}:{quote(pw, safe='')}"
        s = f"{scheme}://{userinfo}@{hostpart}"
    parsed = urlsplit(s)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} and not any(key == "sslmode" for key, _ in query):
        query.append(("sslmode", "require"))
    return urlunsplit(parsed._replace(query=urlencode(query, quote_via=quote)))


def _supabase_pooler_dsn(dsn: str, region: str = "eu-west-1") -> str | None:
    """Converts a direct IPv6 db.<ref>.supabase.co DSN to its IPv4 Session Pooler DSN."""
    parsed = urlsplit(_normalize_pg_dsn(dsn))
    host = (parsed.hostname or "").lower()
    parts = host.split(".")
    if len(parts) != 4 or parts[0] != "db" or parts[2] != "supabase" or parts[3] != "co":
        return None
    project_ref = parts[1]
    user = unquote(parsed.username or "postgres")
    if "." not in user:
        user = f"{user}.{project_ref}"
    pw = quote(unquote(parsed.password or ""), safe="")
    user_enc = quote(user, safe=".")
    port = parsed.port or 5432
    pooler_prefix = region if region.startswith("aws-") else f"aws-0-{region}"
    return urlunsplit(parsed._replace(netloc=f"{user_enc}:{pw}@{pooler_prefix}.pooler.supabase.com:{port}"))


class PgCursorAdapter:
    def __init__(self, rows: list[PgRow], rowcount: int, lastrowid: int | None = None) -> None:
        self._rows = rows
        self._idx = 0
        self.rowcount = rowcount
        self.lastrowid = lastrowid

    def fetchone(self) -> PgRow | None:
        if self._idx >= len(self._rows):
            return None
        row = self._rows[self._idx]
        self._idx += 1
        return row

    def fetchall(self) -> list[PgRow]:
        rows = self._rows[self._idx :]
        self._idx = len(self._rows)
        return rows

    def __iter__(self) -> Iterator[PgRow]:
        while (row := self.fetchone()) is not None:
            yield row


class PostgresDatabase:
    """PostgreSQL connection wrapper matching the synchronous interface used across all services."""

    engine = "postgresql"

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg
        except ImportError as err:
            raise RuntimeError(
                "psycopg is required when DATABASE_URL points to PostgreSQL. Install with: pip install 'psycopg[binary]'"
            ) from err
        self._psycopg = psycopg
        self._dsn = dsn
        self._conn = self._connect()
        try:
            self._migrate()
        except BaseException:
            self._conn.close()
            raise

    def _connect(self):
        normalized_dsn = _normalize_pg_dsn(self._dsn)
        try:
            return self._psycopg.connect(normalized_dsn, autocommit=True, connect_timeout=10)
        except self._psycopg.OperationalError as first_err:
            fallback_dsn = _normalize_pg_dsn(self._dsn, decode_percent=True)
            if fallback_dsn != normalized_dsn:
                try:
                    conn = self._psycopg.connect(fallback_dsn, autocommit=True, connect_timeout=10)
                    self._dsn = fallback_dsn
                    return conn
                except self._psycopg.OperationalError:
                    pass
            msg = str(first_err).lower()
            if "cannot assign requested address" in msg or "network is unreachable" in msg or "no route to host" in msg:
                pooler_dsn = _supabase_pooler_dsn(self._dsn)
                if pooler_dsn:
                    conn = self._psycopg.connect(pooler_dsn, autocommit=True, connect_timeout=10)
                    self._dsn = pooler_dsn
                    return conn
            raise

    def _ensure_open(self) -> None:
        if getattr(self._conn, "closed", False) or getattr(self._conn, "broken", False):
            self._conn = self._connect()

    def _migrate(self) -> None:
        with self._conn.transaction(), self._conn.cursor() as cur:
            for stmt in PG_SCHEMA.split(";\n"):
                if stmt.strip():
                    cur.execute(stmt)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> PgCursorAdapter:
        stripped = sql.strip().upper()
        if stripped.startswith("PRAGMA "):
            return PgCursorAdapter([], 0)
        self._ensure_open()
        pg_sql, needs_returning = _translate_sql_for_postgres(sql)
        for attempt in range(2):
            try:
                with self._conn.cursor() as cur:
                    cur.execute(pg_sql, tuple(params))
                    lastrowid = None
                    rows: list[PgRow] = []
                    if cur.description is not None:
                        cols = [col.name for col in cur.description]
                        raw_rows = cur.fetchall()
                        rows = [PgRow(cols, r) for r in raw_rows]
                        if needs_returning and rows:
                            lastrowid = int(rows[0]["id"])
                            rows = []
                    return PgCursorAdapter(rows, cur.rowcount, lastrowid)
            except self._psycopg.OperationalError as err:
                if attempt == 0 and (
                    getattr(self._conn, "closed", False)
                    or getattr(self._conn, "broken", False)
                    or not getattr(self._conn.info, "transaction_status", 0)
                ):
                    self._conn = self._connect()
                    continue
                raise sqlite3.Error(str(err)) from err
            except self._psycopg.IntegrityError as err:
                # Map PostgreSQL unique violation (SQLSTATE 23505) to sqlite3.IntegrityError so services catch it uniformly
                if getattr(err, "sqlstate", "") == "23505":
                    raise sqlite3.IntegrityError(f"UNIQUE constraint failed: {err}") from err
                raise sqlite3.IntegrityError(str(err)) from err
            except self._psycopg.Error as err:
                raise sqlite3.Error(str(err)) from err
        return PgCursorAdapter([], 0)

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> None:
        self._ensure_open()
        pg_sql, _ = _translate_sql_for_postgres(sql)
        with self._conn.cursor() as cur:
            cur.executemany(pg_sql, [tuple(p) for p in seq_of_params])

    def close(self) -> None:
        self._conn.close()


def open_database(path: str = ":memory:", database_url: str = "") -> Any:
    """Opens PostgreSQL when `database_url` or `path` is a postgres:// URI, otherwise opens SQLite (WAL mode)."""
    url = (database_url or "").strip()
    raw_path = (path or "").strip()
    if not url and raw_path.startswith(("postgresql://", "postgres://", "sqlite://")):
        url = raw_path
    if url.startswith(("postgresql://", "postgres://")):
        return PostgresDatabase(url)
    if url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///")

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
def transaction(db: Any) -> Iterator[None]:
    if getattr(db, "engine", "sqlite") == "postgresql":
        db.execute("BEGIN")
    else:
        db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise


def update_row(
    db: Any,
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
    msg = str(err).lower()
    return isinstance(err, sqlite3.IntegrityError) and ("unique constraint failed" in msg or "duplicate key value" in msg)
