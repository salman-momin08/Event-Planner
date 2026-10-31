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


def _endpoint(raw: str, name: str = "AI_BASE_URL") -> str:
    if not raw:
        return ""
    url = urlparse(raw)
    local = (url.hostname or "") in LOCAL_HOSTS
    if url.scheme == "https" or (url.scheme == "http" and local):
        return raw.rstrip("/")
    raise ConfigError(f"{name} must use https (http is allowed only for localhost)")


DEFAULT_MODELS = {
    "gemini": "gemini-3-flash-preview",
    "openai": "gpt-4o-mini",
}
DEFAULT_ENDPOINTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openai": "https://api.openai.com/v1",
}


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

    raw_provider = (env.get("AI_PROVIDER") or "").strip().lower()
    gemini_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or ""
    openai_key = env.get("OPENAI_API_KEY") or ""
    hf_token = env.get("HF_TOKEN") or env.get("HUGGINGFACEHUB_API_TOKEN") or ""
    ai_key = env.get("AI_API_KEY") or ""

    raw_base_url = env.get("AI_BASE_URL") or env.get("OPENAI_BASE_URL") or ""
    raw_hf_url = env.get("HF_ENDPOINT_URL") or ""

    if raw_provider and raw_provider not in {"gemini", "openai", "huggingface", "hf", "auto"}:
        raise ConfigError("Invalid AI_PROVIDER: expected gemini, openai, huggingface, or auto")

    if raw_provider in {"huggingface", "hf"} or (
        not raw_provider
        and not gemini_key
        and not openai_key
        and not ai_key
        and not raw_base_url
        and (hf_token or raw_hf_url or env.get("HF_MODEL_ID"))
    ):
        provider = env.get("HF_PROVIDER", "auto") or "auto"
        token = ai_key or hf_token
        model_id = env.get("AI_MODEL") or env.get("HF_MODEL_ID") or ""
        endpoint_url = _endpoint(raw_hf_url or raw_base_url, "HF_ENDPOINT_URL")
        local_endpoint = bool(endpoint_url) and (urlparse(endpoint_url).hostname or "") in LOCAL_HOSTS
        enabled = bool(model_id or endpoint_url) and bool(token or local_endpoint)
    else:
        if raw_provider == "gemini" or (not raw_provider and gemini_key):
            provider = "gemini"
            token = ai_key or gemini_key
        elif raw_provider == "openai" or (not raw_provider and (openai_key or ai_key or raw_base_url)):
            provider = "openai"
            token = ai_key or openai_key or gemini_key
        else:
            provider = "gemini"
            token = ""

        endpoint_url = _endpoint(raw_base_url or DEFAULT_ENDPOINTS.get(provider, ""), "AI_BASE_URL") if (token or raw_base_url) else ""
        local_endpoint = bool(raw_base_url) and (urlparse(endpoint_url).hostname or "") in LOCAL_HOSTS
        model_id = (
            env.get("AI_MODEL")
            or env.get("GEMINI_MODEL")
            or env.get("OPENAI_MODEL")
            or (DEFAULT_MODELS.get(provider, "") if (token or local_endpoint) else "")
        )
        enabled = bool(model_id or endpoint_url) and bool(token or local_endpoint)

    ai = AiSettings(
        enabled=enabled,
        model_id=model_id,
        token=token,
        endpoint_url=endpoint_url,
        provider=provider,
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
