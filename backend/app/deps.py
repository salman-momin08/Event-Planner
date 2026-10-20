from __future__ import annotations

import sqlite3

from fastapi import Depends, Request

from .context import Context
from .errors import ApiError
from .services import auth as auth_service
from .services.events import require_event


async def get_ctx(request: Request) -> Context:
    return request.app.state.ctx


async def current_user(request: Request, ctx: Context = Depends(get_ctx)) -> dict | None:
    return auth_service.session_user(ctx, request.cookies.get("sid"))


async def require_user(request: Request, user: dict | None = Depends(current_user)) -> dict:
    if user is None:
        raise ApiError(401, "unauthenticated", "Sign in required")
    request.state.user_id = user["id"]
    return user


async def owned_event(event_id: int, ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)) -> sqlite3.Row:
    """Every event-scoped route depends on this (SEC-004)."""
    return require_event(ctx, user["id"], event_id)
