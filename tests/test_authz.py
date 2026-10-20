from __future__ import annotations

import pytest

from tests.conftest import scripted


@pytest.fixture
def world(make_app):
    app = make_app(chat_model=scripted())
    alice, bob = app.sign_up("alice"), app.sign_up("bob")
    ev = app.make_event(alice)
    base = f"/events/{ev['id']}"
    cat = alice.post(f"{base}/budget-categories", {"name": "Food", "plannedCents": 1000}).json
    vendor = alice.post(f"{base}/vendors", {"name": "Caterer"}).json
    task = alice.post(f"{base}/tasks", {"title": "Book venue"}).json
    expense = alice.post(
        f"{base}/expenses", {"categoryId": cat["id"], "description": "Deposit", "amountCents": 500, "spentOn": "2026-10-01"}
    ).json
    plan = alice.post(f"{base}/ai/plans", {}).json
    assert plan["status"] == "draft"
    return dict(app=app, alice=alice, bob=bob, ev=ev, base=base, cat=cat, vendor=vendor, task=task, expense=expense, plan=plan)


def test_003_other_user_cannot_read_modify_delete_event(world):
    alice, bob, ev = world["alice"], world["bob"], world["ev"]
    path = f"/events/{ev['id']}"
    for r in (bob.get(path), bob.patch(path, {"title": "hacked"}), bob.delete(path)):
        assert r.status == 404 and r.json["error"]["code"] == "not_found"
    assert bob.get("/events/999999").status == 404  # indistinguishable from nonexistent
    assert bob.get("/events").json == []
    assert alice.get(path).json["title"] == "Our wedding"
    assert len(alice.get("/events").json) == 1


def test_004_052_other_user_cannot_reach_any_child_resource(world):
    bob, base = world["bob"], world["base"]
    cat, vendor, task, expense, plan = (world[k] for k in ("cat", "vendor", "task", "expense", "plan"))
    probes = [
        ("get", f"{base}/summary", None),
        ("get", f"{base}/budget-categories", None),
        ("post", f"{base}/budget-categories", {"name": "X"}),
        ("patch", f"{base}/budget-categories/{cat['id']}", {"name": "X"}),
        ("delete", f"{base}/budget-categories/{cat['id']}", None),
        ("get", f"{base}/expenses", None),
        ("post", f"{base}/expenses", {"categoryId": cat["id"], "description": "x", "amountCents": 1, "spentOn": "2026-10-01"}),
        ("patch", f"{base}/expenses/{expense['id']}", {"amountCents": 1}),
        ("delete", f"{base}/expenses/{expense['id']}", None),
        ("get", f"{base}/tasks", None),
        ("post", f"{base}/tasks", {"title": "X"}),
        ("patch", f"{base}/tasks/{task['id']}", {"status": "done"}),
        ("delete", f"{base}/tasks/{task['id']}", None),
        ("get", f"{base}/timeline", None),
        ("post", f"{base}/timeline/generate-template", None),
        ("get", f"{base}/vendors", None),
        ("post", f"{base}/vendors", {"name": "X"}),
        ("patch", f"{base}/vendors/{vendor['id']}", {"name": "X"}),
        ("delete", f"{base}/vendors/{vendor['id']}", None),
        ("get", f"{base}/ai/plans", None),
        ("get", f"{base}/ai/plans/{plan['id']}", None),
        ("post", f"{base}/ai/plans", {}),
        ("post", f"{base}/ai/plans/{plan['id']}/apply", None),
        ("post", f"{base}/ai/plans/{plan['id']}/discard", None),
        ("get", f"{base}/export?format=json", None),
        ("get", f"{base}/export?format=csv&section=tasks", None),
    ]
    assert len(probes) == 26
    for method, path, body in probes:
        r = getattr(bob, method)(path, body) if method in {"post", "patch", "delete"} else getattr(bob, method)(path)
        assert r.status == 404, f"{method} {path} -> {r.status}"
    assert len(world["alice"].get(f"{base}/tasks").json) == 1
    assert world["alice"].get(f"{base}/vendors").json[0]["name"] == "Caterer"
    assert world["alice"].get(f"{base}/ai/plans/{plan['id']}").json["status"] == "draft"


def test_child_ids_do_not_cross_events_of_same_owner(world):
    app, alice = world["app"], world["alice"]
    other = app.make_event(alice, title="Other")
    p = f"/events/{other['id']}"
    assert alice.patch(f"{p}/tasks/{world['task']['id']}", {"status": "done"}).status == 404
    assert alice.delete(f"{p}/budget-categories/{world['cat']['id']}").status == 404
    assert alice.patch(f"{p}/vendors/{world['vendor']['id']}", {"name": "x"}).status == 404


def test_005_protected_routes_require_session(make_app):
    anon = make_app().client()
    for method, path in [
        ("get", "/events"), ("post", "/events"), ("get", "/events/1"), ("get", "/events/1/tasks"),
        ("get", "/ai/status"), ("get", "/auth/me"), ("post", "/auth/logout"), ("delete", "/auth/me"),
    ]:
        r = anon.get(path) if method == "get" else getattr(anon, method)(path, {})
        assert r.status == 401, f"{method} {path}"


def test_009_malicious_input_cannot_bypass_authz_or_inject_sql(world):
    alice, bob, app, ev = world["alice"], world["bob"], world["app"], world["ev"]
    evil = "x'); DROP TABLE events;--"
    body = {"type": "birthday", "title": evil, "eventDate": "2027-01-01", "attendance": 5}
    assert bob.post("/events", {**body, "ownerId": 1}).status == 400  # mass assignment rejected
    ok = bob.post("/events", body)
    assert ok.status == 201 and ok.json["title"] == evil  # stored inertly
    assert app.db.execute("SELECT COUNT(*) n FROM events").fetchone()["n"] == 2
    assert app.db.execute("SELECT owner_id FROM events WHERE id = ?", (ok.json["id"],)).fetchone()["owner_id"] == bob.user["id"]
    for p in (f"/events/{ev['id']}%20OR%201=1", "/events/1;2", "/events/-1", "/events/0x1", "/events/99999999999999999999999"):
        assert bob.get(p).status in (400, 404), p
    assert alice.get(f"/events/{ev['id']}").status == 200
