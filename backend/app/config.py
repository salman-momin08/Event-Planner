"""Configuration read once from environment variables and validated at startup."""
from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AiSettings:
    enabled: bool
    model_id: str
    token: str
    endpoint_url: str
    provider: str
    timeout_s: int
    max_new_tokens: int
    daily_limit: int
    max_repairs: int

    @property
    def model_label(self) -> str:
        return self.model_id or self.endpoint_url


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    database_path: str
    cookie_secure: bool
    hsts: bool
    trust_proxy: bool
    session_ttl_seconds: int
    security_log_key: bytes
    ai: AiSettings
    warnings: tuple[str, ...] = ()

    @property
    def production(self) -> bool:
        return self.environment == "production"


def _int(env: Mapping[str, str], name: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(name, "")
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"Invalid {name}: expected integer {lo}..{hi}") from None
    if not lo <= value <= hi:
        raise ConfigError(f"Invalid {name}: expected integer {lo}..{hi}")
    return value


def _bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, "").strip().lower()
    if raw == "":
        return default
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    raise ConfigError(f"Invalid {name}: expected true/false")


def _endpoint(raw: str) -> str:
    if not raw:
        return ""
    url = urlparse(raw)
    local = (url.hostname or "") in LOCAL_HOSTS
    if url.scheme == "https" or (url.scheme == "http" and local):
        return raw.rstrip("/")
    raise ConfigError("HF_ENDPOINT_URL must use https (http is allowed only for localhost)")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    environment = env.get("APP_ENV", "development")
    production = environment == "production"
    warnings: list[str] = []

    cookie_secure = _bool(env, "COOKIE_SECURE", production)
    if production and not cookie_secure:
        warnings.append("COOKIE_SECURE is false in production")

    # Keys the HMAC that pseudonymises client IPs in the audit log; kept out of the database so a
    # DB leak cannot reverse the small IPv4 space. A random per-process key is used when unset.
    raw_log_key = env.get("SECURITY_LOG_KEY", "")
    security_log_key = raw_log_key.encode()
    if not security_log_key:
        if production:
            warnings.append("SECURITY_LOG_KEY is not set; audit-log IP pseudonyms will not persist across restarts")
        security_log_key = secrets.token_bytes(32)

    token = env.get("HF_TOKEN") or env.get("HUGGINGFACEHUB_API_TOKEN") or ""
    model_id = env.get("HF_MODEL_ID", "")
    endpoint_url = _endpoint(env.get("HF_ENDPOINT_URL", ""))
    local_endpoint = bool(endpoint_url) and (urlparse(endpoint_url).hostname or "") in LOCAL_HOSTS
    enabled = bool(model_id or endpoint_url) and bool(token or local_endpoint)

    ai = AiSettings(
        enabled=enabled,
        model_id=model_id,
        token=token,
        endpoint_url=endpoint_url,
        provider=env.get("HF_PROVIDER", "auto") or "auto",
        timeout_s=_int(env, "AI_TIMEOUT_SECONDS", 30, 1, 120),
        max_new_tokens=_int(env, "AI_MAX_OUTPUT_TOKENS", 2500, 100, 8000),
        daily_limit=_int(env, "AI_DAILY_LIMIT", 20, 1, 1000),
        max_repairs=_int(env, "AI_MAX_REPAIRS", 2, 0, 3),
    )
    return Settings(
        environment=environment,
        host=env.get("HOST", "127.0.0.1"),
        port=_int(env, "PORT", 3000, 0, 65535),
        database_path=env.get("DATABASE_PATH", "./data/planner.db"),
        cookie_secure=cookie_secure,
        hsts=production,
        trust_proxy=_bool(env, "TRUST_PROXY", False),
        session_ttl_seconds=_int(env, "SESSION_TTL_HOURS", 168, 1, 24 * 90) * 3600,
        security_log_key=security_log_key,
        ai=ai,
        warnings=tuple(warnings),
    )
