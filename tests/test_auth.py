from __future__ import annotations

from tests.conftest import FIXED_NOW, PASSWORD
from datetime import timedelta


def test_002_005_007_register_session_cookie_logout_login(make_app):
    app = make_app(env={"COOKIE_SECURE": "true"})
    c = app.client()
    assert c.get("/auth/me").status == 401  # TEST-005

    reg = c.post("/auth/register", {"email": "Asha@Example.com", "displayName": "Asha", "password": PASSWORD})
    assert reg.status == 201
    assert reg.json == {"id": reg.json["id"], "email": "asha@example.com", "displayName": "Asha"}
    set_cookie = reg.headers["set-cookie"]
    for flag in ("HttpOnly", "SameSite=strict", "Path=/", "Max-Age=604800", "Secure"):
        assert flag.lower() in set_cookie.lower(), flag

    token = set_cookie.split(";")[0].split("=", 1)[1]
    stored = app.db.execute("SELECT token_hash FROM sessions").fetchall()
    assert len(stored) == 1 and stored[0]["token_hash"] != token  # hashed at rest (SEC-002)
    assert PASSWORD not in app.db.execute("SELECT password_hash FROM users").fetchone()["password_hash"]

    assert c.get("/auth/me").json["displayName"] == "Asha"
    assert c.post("/auth/logout").status == 204
    assert c.get("/auth/me").status == 401
    assert app.db.execute("SELECT COUNT(*) n FROM sessions").fetchone()["n"] == 0

    bad = c.post("/auth/login", {"email": "asha@example.com", "password": "wrong wrong wrong"})
    unknown = c.post("/auth/login", {"email": "nobody@example.com", "password": "wrong wrong wrong"})
    assert bad.status == 401 and bad.json["error"]["message"] == unknown.json["error"]["message"]
    assert c.post("/auth/login", {"email": "asha@example.com", "password": PASSWORD}).status == 200

    types = [r["type"] for r in app.db.execute("SELECT type FROM security_events ORDER BY id")]
    assert types == ["register", "logout", "login_failed", "login_failed", "login"]


def test_registration_validation(make_app):
    app = make_app()
    c = app.client()
    base = {"email": "a@example.com", "displayName": "A", "password": PASSWORD}
    assert c.post("/auth/register", {**base, "password": "short"}).status == 400
    assert c.post("/auth/register", {**base, "email": "nope"}).status == 400
    r = c.post("/auth/register", {**base, "isAdmin": True})
    assert r.status == 400 and r.json["error"]["details"]["isAdmin"] == "Unknown field"
    assert c.post("/auth/register", base).status == 201
    dup = app.client().post("/auth/register", base)
    assert dup.status == 409 and dup.json["error"]["code"] == "email_taken"


def test_006_csrf(make_app):
    app = make_app()
    c = app.sign_up()
    no_header = c.post("/events", {"type": "birthday"}, csrf=False)
    assert no_header.status == 403 and no_header.json["error"]["code"] == "csrf"
    assert c.post("/events", {}, headers={"Origin": "https://evil.example"}).status == 403
    assert c.post("/events", {}, headers={"Origin": "http://testserver"}).status == 400  # passes CSRF, fails validation
    assert c.get("/events", csrf=False).status == 200


def test_008_login_rate_limit(make_app):
    app = make_app(limits={"login_account": 3})
    c = app.client()
    body = {"email": "x@example.com", "password": "wrong wrong wrong"}
    for _ in range(3):
        assert c.post("/auth/login", body).status == 401
    limited = c.post("/auth/login", body)
    assert limited.status == 429 and int(limited.headers["retry-after"]) >= 1
    assert c.post("/auth/login", {**body, "email": "y@example.com"}).status == 401  # per-account key


def test_register_rate_limit(make_app):
    app = make_app(limits={"register": 2})
    for _ in range(2):
        app.sign_up()
    r = app.client().post("/auth/register", {"email": "z@example.com", "displayName": "Z", "password": PASSWORD})
    assert r.status == 429


def test_expired_sessions_rejected(make_app):
    app = make_app()
    c = app.sign_up()
    assert c.get("/auth/me").status == 200
    app.clock_value = FIXED_NOW + timedelta(days=8)
    assert c.get("/auth/me").status == 401


def test_063_account_deletion_cascades(make_app):
    app = make_app()
    c = app.sign_up("del")
    ev = app.make_event(c)
    base = f"/events/{ev['id']}"
    c.post(f"{base}/budget-categories", {"name": "Food", "plannedCents": 100})
    c.post(f"{base}/tasks", {"title": "T"})
    c.post(f"{base}/vendors", {"name": "V"})

    assert c.delete("/auth/me", {"password": "not the password!"}).status == 401
    assert c.get("/auth/me").status == 200
    assert c.delete("/auth/me", {"password": PASSWORD}).status == 204
    for table in ("users", "sessions", "events", "budget_categories", "tasks", "vendors"):
        assert app.db.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"] == 0, table
    assert c.get("/auth/me").status == 401
