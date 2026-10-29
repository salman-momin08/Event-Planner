from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import secrets
import sqlite3
from base64 import b64decode, b64encode
from datetime import timedelta

from ..context import Context
from ..db import is_unique_violation, transaction
from ..errors import ApiError, bad_request, conflict
from ..schemas import ChangePasswordIn, LoginIn, RegisterIn

SECURITY_EVENT_RETENTION_DAYS = 90

_N, _R, _P, _KEYLEN = 32768, 8, 1, 64
_MAXMEM = 128 * 1024 * 1024


def hash_password_sync(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=_MAXMEM, dklen=_KEYLEN)
    return f"scrypt${_N}${_R}${_P}${b64encode(salt).decode()}${b64encode(key).decode()}"


def verify_password_sync(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt, expected = b64decode(parts[4]), b64decode(parts[5])
        actual = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=_MAXMEM, dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(hash_password_sync, password)


async def verify_password(password: str, stored: str) -> bool:
    return await asyncio.to_thread(verify_password_sync, password, stored)


_dummy_hash: str | None = None


async def _burn_verification(password: str) -> None:
    """Equalises timing for unknown emails."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = await hash_password("dummy-password-for-timing")
    await verify_password(password, _dummy_hash)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _pseudonymize_ip(ctx: Context, ip: str) -> str:
    """Keyed HMAC so a DB leak cannot brute-force the small IPv4 space back to a real address."""
    return hmac.new(ctx.settings.security_log_key, ip.encode(), hashlib.sha256).hexdigest()[:16]


def purge_security_events(ctx: Context, retention_days: int = SECURITY_EVENT_RETENTION_DAYS) -> int:
    """Purges security_events older than retention_days (TD-004) and expired sessions."""
    cutoff = (ctx.clock() - timedelta(days=retention_days)).isoformat()
    now_ms = int(ctx.clock().timestamp() * 1000)
    ctx.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_ms,))
    cur = ctx.db.execute("DELETE FROM security_events WHERE at < ?", (cutoff,))
    return cur.rowcount


def record_security_event(ctx: Context, user_id: int | None, event_type: str, ip: str | None) -> None:
    cutoff = (ctx.clock() - timedelta(days=SECURITY_EVENT_RETENTION_DAYS)).isoformat()
    ctx.db.execute("DELETE FROM security_events WHERE at < ?", (cutoff,))
    ctx.db.execute(
        "INSERT INTO security_events (at, user_id, type, ip_hash) VALUES (?, ?, ?, ?)",
        (ctx.clock().isoformat(), user_id, event_type, _pseudonymize_ip(ctx, ip) if ip else None),
    )


def to_user(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "email": row["email"], "displayName": row["display_name"]}


def _create_session(ctx: Context, user_id: int) -> str:
    now_ms = int(ctx.clock().timestamp() * 1000)
    ctx.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_ms,))
    token = secrets.token_urlsafe(32)
    ctx.db.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (_sha256(token), user_id, now_ms + ctx.settings.session_ttl_seconds * 1000, now_ms),
    )
    return token


async def register(ctx: Context, body: RegisterIn, ip: str) -> tuple[dict, str]:
    password_hash = await hash_password(body.password)
    try:
        cur = ctx.db.execute(
            "INSERT INTO users (email, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (body.email, body.displayName, password_hash, ctx.clock().isoformat()),
        )
    except sqlite3.IntegrityError as err:
        if is_unique_violation(err):
            raise conflict("An account with this email already exists", "email_taken") from None
        raise
    user_id = int(cur.lastrowid)
    token = _create_session(ctx, user_id)
    record_security_event(ctx, user_id, "register", ip)
    return {"id": user_id, "email": body.email, "displayName": body.displayName}, token


async def login(ctx: Context, body: LoginIn, ip: str) -> tuple[dict, str]:
    row = ctx.db.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()
    if row is not None:
        ok = await verify_password(body.password, row["password_hash"])
    else:
        await _burn_verification(body.password)
        ok = False
    if not ok:
        record_security_event(ctx, row["id"] if row else None, "login_failed", ip)
        raise ApiError(401, "invalid_credentials", "Invalid email or password")
    token = _create_session(ctx, row["id"])
    record_security_event(ctx, row["id"], "login", ip)
    return to_user(row), token


def session_user(ctx: Context, token: str | None) -> dict | None:
    if not token:
        return None
    row = ctx.db.execute(
        """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token_hash = ? AND s.expires_at > ?""",
        (_sha256(token), int(ctx.clock().timestamp() * 1000)),
    ).fetchone()
    return to_user(row) if row else None


def logout(ctx: Context, token: str, user_id: int, ip: str) -> None:
    ctx.db.execute("DELETE FROM sessions WHERE token_hash = ?", (_sha256(token),))
    record_security_event(ctx, user_id, "logout", ip)


async def change_password(ctx: Context, user: dict, body: ChangePasswordIn, ip: str) -> str:
    row = ctx.db.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
    if row is None or not await verify_password(body.currentPassword, row["password_hash"]):
        record_security_event(ctx, user["id"], "password_change_failed", ip)
        raise ApiError(401, "invalid_credentials", "Invalid current password")
    if body.newPassword == body.currentPassword:
        raise bad_request({"newPassword": "New password must be different from your current password"})
    new_hash = await hash_password(body.newPassword)
    with transaction(ctx.db):
        ctx.db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
        ctx.db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        token = _create_session(ctx, user["id"])
        record_security_event(ctx, user["id"], "password_changed", ip)
    return token


async def delete_account(ctx: Context, user: dict, password: str, ip: str) -> None:
    row = ctx.db.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
    if row is None or not await verify_password(password, row["password_hash"]):
        raise ApiError(401, "invalid_credentials", "Invalid password")
    ctx.db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    record_security_event(ctx, user["id"], "account_deleted", ip)
