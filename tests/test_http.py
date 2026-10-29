from __future__ import annotations

import json

from app.config import load_settings
from app.db import open_database
from app.logger import Logger
from app.main import create_app
from starlette.testclient import TestClient
from tests.conftest import Client


def test_060_security_headers(make_app):
    app = make_app()
    c = app.client()
    for path in ("/", "/api/v1/auth/me", "/healthz", "/api/v1/nope", "/missing.js"):
        r = c.request("GET", path)
        csp = r.headers["content-security-policy"]
        for part in ("default-src 'self'", "script-src 'self'", "frame-ancestors 'none'", "object-src 'none'"):
            assert part in csp, (path, part)
        assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["x-request-id"]
        assert "strict-transport-security" not in r.headers
    assert c.get("/auth/me").headers["cache-control"] == "no-store"
    prod = make_app(env={"APP_ENV": "production"}).client()
    assert "strict-transport-security" in prod.request("GET", "/healthz").headers


def test_healthz_and_unknown_routes(make_app):
    app = make_app()
    c = app.sign_up()
    assert c.request("GET", "/healthz").json == {"status": "ok"}
    r = c.get("/nope")
    assert r.status == 404 and r.json["error"]["code"] == "not_found"
    assert c.delete("/events").status == 405
    assert c.get("/events/abc").status == 404


def test_061_unexpected_errors_are_generic(make_app):
    app = make_app()
    c = app.sign_up()
    ev = app.make_event(c)
    app.db.execute("DROP TABLE vendors")  # force a SQL failure
    r = c.get(f"/events/{ev['id']}/vendors")
    assert r.status == 500
    assert r.json["error"]["code"] == "internal_error" and r.json["error"]["message"] == "Something went wrong"
    assert r.json["error"]["requestId"] == r.headers["x-request-id"]
    low = r.text.lower()
    assert "vendors" not in low and "sql" not in low and "traceback" not in low and ".py" not in low


def test_061b_logs_never_contain_secrets_or_bodies():
    lines: list[str] = []
    db = open_database(":memory:")
    app = create_app(load_settings({}), db=db, logger=Logger(write=lines.append))
    with TestClient(app) as http:
        c = Client(app)
        r = c.post("/auth/register", {"email": "log@example.com", "displayName": "Log", "password": "super secret passphrase"})
        assert r.status == 201
        sid = r.headers["set-cookie"].split(";")[0].split("=", 1)[1]
        c.get("/auth/me")
    joined = "\n".join(lines)
    assert '"route": "/api/v1/auth/register"' in joined
    for secret in ("super secret passphrase", "log@example.com", sid):
        assert secret not in joined
    assert all(json.loads(line) for line in lines)


def test_062_static_files_and_traversal(make_app):
    c = make_app().client()
    for path in (
        "/..%2f..%2fpyproject.toml", "/%2e%2e/%2e%2e/requirements.txt", "/..\\requirements.txt", "/%00",
        "/..%5c..%5capp%5cmain.py", "/index.html::$DATA", "/%zz", "/app/main.py", "/../app/main.py",
    ):
        r = c.request("GET", path)
        assert r.status in (400, 404), (path, r.status)
        assert "create_app" not in r.text and "fastapi" not in r.text.lower(), path
    assert c.request("POST", "/", {}).status == 405
    idx = c.request("GET", "/")
    assert idx.status == 200 and idx.headers["content-type"].startswith("text/html")
    etag = idx.headers["etag"]
    assert etag.startswith('W/"')
    not_mod = c.request("GET", "/", headers={"If-None-Match": etag})
    assert not_mod.status == 304 and not_mod.text == ""
    assert c.request("GET", "/app.js").headers["content-type"].startswith("text/javascript")
    assert c.request("GET", "/views/ai.js").status == 200
    head = c.request("HEAD", "/")
    assert head.status == 200 and head.text == ""


def test_064_body_limits_and_content_type(make_app):
    app = make_app()
    c = app.sign_up()
    big = json.dumps({"type": "wedding", "notes": "x" * (70 * 1024)})
    r = c.post("/events", raw_body=big)
    assert r.status == 413 and r.json["error"]["code"] == "payload_too_large"
    wrong = c.post("/events", raw_body='{"a":1}', headers={"Content-Type": "text/plain"})
    assert wrong.status == 415
    assert c.post("/events", raw_body="{not json").status == 400
    assert c.post("/events", raw_body="[]").status == 400
    assert c.post("/events", raw_body="null").status == 400
    assert c.get("/events").status == 200  # still healthy


def test_chunked_body_over_limit_is_rejected(make_app):
    app = make_app()
    c = app.sign_up()

    def chunks():
        for _ in range(100):
            yield b"x" * 1024

    r = c.http.post("/api/v1/events", content=chunks(), headers={"X-Requested-With": "planner", "Content-Type": "application/json"})
    assert r.status_code == 413
