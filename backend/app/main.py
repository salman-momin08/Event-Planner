from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi import HTTPException as FastApiHTTPException
from fastapi.exceptions import RequestValidationError
from langchain_core.language_models.chat_models import BaseChatModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .ai.runtime import AiRuntime
from .config import Settings, load_settings
from .context import Context
from .db import open_database
from .errors import ApiError, error_body
from .logger import Logger
from .routes import ai as ai_routes
from .routes import auth as auth_routes
from .routes import events as event_routes
from .routes import planning as planning_routes
from .services.auth import purge_security_events
from .security import (
    MAX_BODY_BYTES,
    RateLimiter,
    check_content_type,
    check_csrf,
    client_ip,
    enforce,
    security_headers,
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
API_PREFIX = "/api/v1"
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}


class PayloadTooLarge(FastApiHTTPException):
    """Subclasses FastAPI's HTTPException so body parsing re-raises it instead of mapping it to a 400."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request body too large")


class BodyLimitMiddleware:
    """Caps request bodies (declared or streamed) at 64 KiB (SEC-005)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        total = 0

        async def limited_receive() -> Message:
            nonlocal total
            if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
                raise PayloadTooLarge()
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > MAX_BODY_BYTES:
                    raise PayloadTooLarge()
            return message

        await self.app(scope, limited_receive, send)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Request ID, rate limit, CSRF, content-type, security headers, access log, generic 500."""

    async def dispatch(self, request: Request, call_next):
        ctx: Context = request.app.state.ctx
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            if request.url.path.startswith("/api/"):
                enforce(ctx.limiters["api"], client_ip(request, ctx.settings.trust_proxy))
                check_csrf(request)
                check_content_type(request)
            response = await call_next(request)
        except ApiError as err:
            response = _error_response(err, request_id)
        except Exception as err:  # unexpected: details go to the log only
            ctx.logger.error("unhandled", requestId=request_id, error=type(err).__name__, detail=str(err)[:500])
            response = _error_response(ApiError(500, "internal_error", "Something went wrong"), request_id)
        response.headers["X-Request-Id"] = request_id
        for name, value in ctx.extras["headers"].items():
            response.headers[name] = value
        route = request.scope.get("route")
        route_path = getattr(route, "path", None)
        if route_path is None:
            route_name = "static" if not request.url.path.startswith("/api/") else "-"
        elif route_path.startswith("/healthz") or route_path.startswith("/{"):
            route_name = route_path
        else:
            route_name = API_PREFIX + route_path
        ctx.logger.info(
            "request",
            requestId=request_id,
            method=request.method,
            route=route_name,
            status=response.status_code,
            durationMs=round((time.monotonic() - started) * 1000),
            **({"userId": request.state.user_id} if hasattr(request.state, "user_id") else {}),
        )
        return response


def _error_response(err: ApiError, request_id: str) -> JSONResponse:
    headers = {"Cache-Control": "no-store", **err.headers}
    if err.status == 413:
        headers["Connection"] = "close"
    return JSONResponse(error_body(err, request_id), status_code=err.status, headers=headers)


def _validation_details(exc: RequestValidationError) -> dict[str, str]:
    details: dict[str, str] = {}
    for item in exc.errors():
        loc = [str(p) for p in item["loc"] if p != "body"]
        loc = [p for p in loc if p not in {"query", "path"}]
        key = ".".join(p for p in loc if not p.isdigit()) if loc and item["type"] != "json_invalid" else "_"
        kind = item["type"]
        if kind == "missing":
            message = "Required"
        elif kind == "extra_forbidden":
            message = "Unknown field"
        elif kind == "json_invalid":
            message = "Invalid JSON"
        elif kind in {"model_attributes_type", "dict_type"}:
            message = "Body must be a JSON object"
            key = "_"
        else:
            message = str(item["msg"]).removeprefix("Value error, ")
        details.setdefault(key or "_", message)
    return details


def create_app(
    settings: Settings | None = None,
    *,
    db=None,
    chat_model: BaseChatModel | None = None,
    clock: Callable[[], datetime] | None = None,
    logger: Logger | None = None,
    limits: dict[str, int] | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    logger = logger or Logger()
    owns_db = db is None
    db = db or open_database(settings.database_path)

    if chat_model is not None:
        ai = AiRuntime.from_chat_model(chat_model, settings.ai, label=settings.ai.model_label or "custom")
    elif settings.ai.enabled:
        try:
            from .ai.llm import build_chat_model

            ai = AiRuntime.from_chat_model(build_chat_model(settings.ai), settings.ai)
        except Exception as err:  # misconfiguration must not stop core planning
            logger.error("ai_init_failed", error=type(err).__name__)
            ai = AiRuntime.disabled()
    else:
        ai = AiRuntime.disabled()

    lim = {"api": 300, "login_ip": 30, "login_account": 10, "register": 5, "ai_minute": 5, **(limits or {})}
    ctx = Context(
        settings=settings,
        db=db,
        clock=clock or (lambda: datetime.now(timezone.utc)),
        logger=logger,
        limiters={
            "api": RateLimiter(lim["api"], 60),
            "login_ip": RateLimiter(lim["login_ip"], 15 * 60),
            "login_account": RateLimiter(lim["login_account"], 15 * 60),
            "register": RateLimiter(lim["register"], 3600),
            "ai_minute": RateLimiter(lim["ai_minute"], 60),
            "ai_daily": RateLimiter(settings.ai.daily_limit, 24 * 3600),
        },
        ai=ai,
        extras={"headers": security_headers(settings.hsts)},
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        purge_security_events(ctx)
        for warning in settings.warnings:
            logger.warn("config", warning=warning)
        logger.info("starting", environment=settings.environment, aiEnabled=ai.available)
        yield
        if owns_db:
            db.close()

    app = FastAPI(title="Event Planning Assistant", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.ctx = ctx

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, err: ApiError):
        return _error_response(err, request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        err = ApiError(400, "validation_error", "Invalid input", _validation_details(exc))
        return _error_response(err, request.state.request_id)

    @app.exception_handler(PayloadTooLarge)
    async def too_large_handler(request: Request, exc: PayloadTooLarge):
        return _error_response(ApiError(413, "payload_too_large", "Request body too large"), request.state.request_id)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed"}
        err = ApiError(exc.status_code, codes.get(exc.status_code, "error"), "Not found" if exc.status_code == 404 else "Method not allowed")
        return _error_response(err, request.state.request_id)

    api_prefix = API_PREFIX
    for module in (auth_routes, event_routes, planning_routes, ai_routes):
        app.include_router(module.router, prefix=api_prefix)

    @app.get("/healthz")
    async def healthz():
        ctx.db.execute("SELECT 1").fetchone()
        return {"status": "ok"}

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def static_files(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path == "api":
            raise ApiError(404, "not_found", "Not found")
        return _serve_static(full_path, request.method, request.headers.get("if-none-match"))

    # Order matters: the body limit sits *inside* the BaseHTTPMiddleware so the exception reaches FastAPI's body parsing unwrapped.
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityMiddleware)
    return app


_STATIC_CACHE: dict[Path, tuple[int, int, str, bytes]] = {}


def _serve_static(path: str, method: str, if_none_match: str | None = None) -> Response:
    root = FRONTEND_DIR.resolve()
    if any(ch in path for ch in ("\0", ":", "\\")):  # NUL, NTFS alternate streams, Windows separators
        return PlainTextResponse("Not Found", status_code=404)
    try:
        target = (root / (path or "index.html")).resolve()
    except (OSError, ValueError):
        return PlainTextResponse("Not Found", status_code=404)
    media_type = MIME.get(target.suffix.lower())
    if not target.is_relative_to(root) or media_type is None or not target.is_file():
        return PlainTextResponse("Not Found", status_code=404)
    st = target.stat()
    cached = _STATIC_CACHE.get(target)
    if cached is not None and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
        etag, data = cached[2], cached[3]
    else:
        data = target.read_bytes()
        etag = f'W/"{st.st_mtime_ns:x}-{st.st_size:x}"'
        _STATIC_CACHE[target] = (st.st_mtime_ns, st.st_size, etag, data)
    headers = {"Cache-Control": "no-cache", "ETag": etag}
    if if_none_match == etag:
        return Response(b"", status_code=304, headers=headers)
    body = b"" if method == "HEAD" else data
    return Response(body, media_type=media_type, headers=headers)
