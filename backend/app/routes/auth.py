from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from ..context import Context
from ..deps import current_user, get_ctx, require_user
from ..schemas import ChangePasswordIn, DeleteAccountIn, LoginIn, RegisterIn
from ..security import client_ip, enforce
from ..services import auth

router = APIRouter(prefix="/auth")


def _set_session_cookie(response: Response, ctx: Context, token: str, max_age: int) -> None:
    response.set_cookie(
        "sid", token, max_age=max_age, httponly=True, samesite="strict", secure=ctx.settings.cookie_secure, path="/"
    )


@router.post("/register", status_code=201)
async def register(body: RegisterIn, request: Request, response: Response, ctx: Context = Depends(get_ctx)):
    ip = client_ip(request, ctx.settings.trust_proxy)
    enforce(ctx.limiters["register"], ip, "Too many registrations. Try again later.")
    user, token = await auth.register(ctx, body, ip)
    _set_session_cookie(response, ctx, token, ctx.settings.session_ttl_seconds)
    return user


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, ctx: Context = Depends(get_ctx)):
    ip = client_ip(request, ctx.settings.trust_proxy)
    message = "Too many sign-in attempts. Try again later."
    enforce(ctx.limiters["login_ip"], ip, message)
    enforce(ctx.limiters["login_account"], f"{ip}|{body.email}", message)
    user, token = await auth.login(ctx, body, ip)
    _set_session_cookie(response, ctx, token, ctx.settings.session_ttl_seconds)
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request, ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)):
    auth.logout(ctx, request.cookies.get("sid", ""), user["id"], client_ip(request, ctx.settings.trust_proxy))
    response = Response(status_code=204)
    _set_session_cookie(response, ctx, "", 0)
    return response


@router.get("/me")
async def me(user: dict = Depends(require_user)):
    return user


@router.post("/password", status_code=204)
async def change_password(
    body: ChangePasswordIn, request: Request, ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)
):
    ip = client_ip(request, ctx.settings.trust_proxy)
    enforce(ctx.limiters["login_account"], f"pw|{user['id']}", "Too many password attempts. Try again later.")
    token = await auth.change_password(ctx, user, body, ip)
    response = Response(status_code=204)
    _set_session_cookie(response, ctx, token, ctx.settings.session_ttl_seconds)
    return response


@router.delete("/me", status_code=204)
async def delete_me(body: DeleteAccountIn, request: Request, ctx: Context = Depends(get_ctx), user: dict = Depends(require_user)):
    await auth.delete_account(ctx, user, body.password, client_ip(request, ctx.settings.trust_proxy))
    response = Response(status_code=204)
    _set_session_cookie(response, ctx, "", 0)
    return response


__all__ = ["router", "current_user"]
