from __future__ import annotations

import pytest


@pytest.fixture
def setup(make_app):
    def build(**event_overrides):
        app = make_app()
        c = app.sign_up()
        ev = app.make_event(c, **event_overrides)
        return app, c, ev, f"/events/{ev['id']}"

    return build


def test_event_validation_and_update(setup):
    app, c, ev, base = setup()
    bad = c.post("/events", {"type": "party", "title": "", "eventDate": "2027-02-30", "attendance": 0, "budgetCents": -1, "currency": "XXX"})
    assert bad.status == 400
    assert sorted(bad.json["error"]["details"]) == ["attendance", "budgetCents", "currency", "eventDate", "title", "type"]
    assert bad.json["error"]["requestId"]
    upd = c.patch(base, {"title": "Renamed", "attendance": 120})
    assert upd.json["title"] == "Renamed" and upd.json["attendance"] == 120 and upd.json["eventDate"] == ev["eventDate"]
    assert c.patch(base, {"budgetCents": 1.5}).status == 400
    assert c.patch(base, {"title": None}).status == 400
    assert c.delete(base).status == 204
    assert c.get(base).status == 404


def test_011_budget_summary_after_edits(setup):
    app, c, ev, base = setup(budgetCents=100_000)
    food = c.post(f"{base}/budget-categories", {"name": "Food", "plannedCents": 40_000}).json
    decor = c.post(f"{base}/budget-categories", {"name": "Decor", "plannedCents": 20_000}).json
    b = c.get(f"{base}/summary").json["budget"]
    assert [b["totalCents"], b["allocatedCents"], b["unallocatedCents"], b["spentCents"], b["remainingCents"]] == [100_000, 60_000, 40_000, 0, 100_000]

    e1 = c.post(f"{base}/expenses", {"categoryId": food["id"], "description": "Deposit", "amountCents": 36_000, "spentOn": "2026-11-01"}).json
    e2 = c.post(f"{base}/expenses", {"categoryId": decor["id"], "description": "Flowers", "amountCents": 25_000, "spentOn": "2026-11-02"}).json
    b = c.get(f"{base}/summary").json["budget"]
    assert b["spentCents"] == 61_000 and b["remainingCents"] == 39_000
    by = {x["name"]: x for x in b["categories"]}
    assert by["Food"]["status"] == "near_limit" and by["Decor"]["status"] == "over" and by["Decor"]["varianceCents"] == -5_000

    c.patch(f"{base}/expenses/{e2['id']}", {"amountCents": 5_000})
    b = c.get(f"{base}/summary").json["budget"]
    assert b["spentCents"] == 41_000
    assert next(x for x in b["categories"] if x["name"] == "Decor")["status"] == "on_track"

    c.patch(f"{base}/expenses/{e1['id']}", {"categoryId": decor["id"]})
    b = c.get(f"{base}/summary").json["budget"]
    assert next(x for x in b["categories"] if x["name"] == "Food")["spentCents"] == 0
    assert next(x for x in b["categories"] if x["name"] == "Decor")["spentCents"] == 41_000

    c.delete(f"{base}/expenses/{e1['id']}")
    c.delete(f"{base}/expenses/{e2['id']}")
    b = c.get(f"{base}/summary").json["budget"]
    assert [b["spentCents"], b["remainingCents"], b["overBudget"]] == [0, 100_000, False]

    c.patch(base, {"budgetCents": 50_000})
    b = c.get(f"{base}/summary").json["budget"]
    assert [b["overAllocated"], b["unallocatedCents"]] == [True, -10_000]
    c.post(f"{base}/expenses", {"categoryId": food["id"], "description": "Big", "amountCents": 60_000, "spentOn": "2026-11-03"})
    assert c.get(f"{base}/summary").json["budget"]["overBudget"] is True


def test_012_category_in_use_and_duplicates(setup):
    app, c, ev, base = setup()
    cat = c.post(f"{base}/budget-categories", {"name": "Food", "plannedCents": 100}).json
    assert c.post(f"{base}/budget-categories", {"name": "FOOD"}).status == 409
    x = c.post(f"{base}/expenses", {"categoryId": cat["id"], "description": "a", "amountCents": 5, "spentOn": "2026-11-01"}).json
    blocked = c.delete(f"{base}/budget-categories/{cat['id']}")
    assert blocked.status == 409 and blocked.json["error"]["code"] == "category_in_use"
    c.delete(f"{base}/expenses/{x['id']}")
    assert c.delete(f"{base}/budget-categories/{cat['id']}").status == 204


def test_013_032_expense_refs_same_event_and_vendor_delete_unlinks(setup):
    app, c, ev, base = setup()
    other = app.make_event(c, title="Other")
    other_cat = c.post(f"/events/{other['id']}/budget-categories", {"name": "Food"}).json
    other_vendor = c.post(f"/events/{other['id']}/vendors", {"name": "Elsewhere"}).json
    cat = c.post(f"{base}/budget-categories", {"name": "Food"}).json
    vendor = c.post(f"{base}/vendors", {"name": "Mine"}).json
    body = {"description": "x", "amountCents": 10, "spentOn": "2026-11-01"}

    r1 = c.post(f"{base}/expenses", {**body, "categoryId": other_cat["id"]})
    assert r1.status == 400 and "categoryId" in r1.json["error"]["details"]
    r2 = c.post(f"{base}/expenses", {**body, "categoryId": cat["id"], "vendorId": other_vendor["id"]})
    assert r2.status == 400 and "vendorId" in r2.json["error"]["details"]
    assert c.post(f"{base}/expenses", {**body, "categoryId": cat["id"], "amountCents": 0}).status == 400
    assert c.post(f"{base}/expenses", {**body, "categoryId": cat["id"], "amountCents": 1.5}).status == 400

    ok = c.post(f"{base}/expenses", {**body, "categoryId": cat["id"], "vendorId": vendor["id"]}).json
    task = c.post(f"{base}/tasks", {"title": "Call", "vendorId": vendor["id"]}).json
    assert c.delete(f"{base}/vendors/{vendor['id']}").status == 204
    assert next(e for e in c.get(f"{base}/expenses").json if e["id"] == ok["id"])["vendorId"] is None
    assert next(t for t in c.get(f"{base}/tasks").json if t["id"] == task["id"])["vendorId"] is None


def test_020_to_023_tasks_dependencies(setup):
    app, c, ev, base = setup()
    a = c.post(f"{base}/tasks", {"title": "Book venue", "dueDate": "2027-01-01"}).json
    assert a["status"] == "todo"
    assert c.post(f"{base}/tasks", {"title": "book VENUE"}).status == 409
    assert c.post(f"{base}/tasks", {"title": "x", "dueDate": "2027-13-01"}).status == 400
    assert c.post(f"{base}/tasks", {"title": "x", "status": "finished"}).status == 400

    b = c.post(f"{base}/tasks", {"title": "Send invites", "dependsOn": [a["id"]]}).json
    assert b["blocked"] is True
    ctask = c.post(f"{base}/tasks", {"title": "Collect RSVPs", "dependsOn": [b["id"]]}).json

    cyc = c.patch(f"{base}/tasks/{a['id']}", {"dependsOn": [ctask["id"]]})
    assert cyc.status == 400 and "dependsOn" in cyc.json["error"]["details"]
    assert c.patch(f"{base}/tasks/{a['id']}", {"dependsOn": [a["id"]]}).status == 400

    other = app.make_event(c, title="Other")
    foreign = c.post(f"/events/{other['id']}/tasks", {"title": "Foreign"}).json
    assert c.patch(f"{base}/tasks/{b['id']}", {"dependsOn": [foreign["id"]]}).status == 400
    assert c.patch(f"{base}/tasks/{b['id']}", {"dependsOn": [999999]}).status == 400
    assert next(t for t in c.get(f"{base}/tasks").json if t["id"] == b["id"])["dependsOn"] == [a["id"]]

    c.patch(f"{base}/tasks/{a['id']}", {"status": "done"})
    tasks = c.get(f"{base}/tasks").json
    assert next(t for t in tasks if t["id"] == b["id"])["blocked"] is False
    assert next(t for t in tasks if t["id"] == ctask["id"])["blocked"] is True

    c.patch(f"{base}/tasks/{ctask['id']}", {"dependsOn": []})
    assert next(t for t in c.get(f"{base}/tasks").json if t["id"] == ctask["id"])["blocked"] is False
    c.patch(f"{base}/tasks/{ctask['id']}", {"dependsOn": [b["id"]]})
    assert c.delete(f"{base}/tasks/{b['id']}").status == 204
    assert next(t for t in c.get(f"{base}/tasks").json if t["id"] == ctask["id"])["dependsOn"] == []


def test_024_timeline_order_and_overdue(setup):
    app, c, ev, base = setup()
    for body in (
        {"title": "Later", "dueDate": "2027-01-01"},
        {"title": "Past", "dueDate": "2026-10-01"},
        {"title": "Past but done", "dueDate": "2026-09-01", "status": "done"},
        {"title": "Today", "dueDate": "2026-10-20"},
        {"title": "No date"},
    ):
        c.post(f"{base}/tasks", body)
    tl = c.get(f"{base}/timeline").json
    assert tl["today"] == "2026-10-20"
    assert [t["title"] for t in tl["dated"]] == ["Past but done", "Past", "Today", "Later"]
    assert [t["overdue"] for t in tl["dated"]] == [False, True, False, False]
    assert [t["title"] for t in tl["undated"]] == ["No date"]
    assert c.get(f"{base}/summary").json["tasks"] == {"total": 5, "done": 1, "overdue": 1, "blocked": 0}


def test_025_026_template_timeline(setup):
    app, c, ev, base = setup(type="birthday", eventDate="2026-12-01")
    first = c.post(f"{base}/timeline/generate-template")
    assert first.status == 200 and first.json["created"] > 5 and first.json["skipped"] == 0
    tasks = c.get(f"{base}/tasks").json
    assert len(tasks) == first.json["created"]
    by = {t["title"]: t for t in tasks}
    assert by["Send invitations"]["dueDate"] == "2026-11-10"
    assert by["Set up venue"]["dueDate"] == "2026-12-01"
    assert all(t["source"] == "template" for t in tasks)

    second = c.post(f"{base}/timeline/generate-template")
    assert second.json == {"created": 0, "skipped": first.json["created"]}
    assert len(c.get(f"{base}/tasks").json) == len(tasks)

    w = c.post("/events", {"type": "wedding", "title": "W", "eventDate": "2027-06-12", "attendance": 50}).json
    c.post(f"/events/{w['id']}/tasks", {"title": "book venue"})
    gen = c.post(f"/events/{w['id']}/timeline/generate-template")
    assert gen.json["skipped"] == 1
    assert next(t for t in c.get(f"/events/{w['id']}/tasks").json if t["title"] == "Book caterer")["dueDate"] == "2026-09-15"


def test_030_031_vendors(setup):
    app, c, ev, base = setup()
    v = c.post(f"{base}/vendors", {"name": "Bloom & Co", "category": "Florist", "quoteCents": 120_000, "contact": "<img src=x onerror=alert(1)>"}).json
    assert v["status"] == "researching" and v["contact"] == "<img src=x onerror=alert(1)>"
    assert c.patch(f"{base}/vendors/{v['id']}", {"status": "booked", "quoteCents": None}).json["quoteCents"] is None
    assert c.post(f"{base}/vendors", {"name": "x", "status": "hired"}).status == 400
    assert c.post(f"{base}/vendors", {"name": "x", "quoteCents": -1}).status == 400
    assert c.post(f"{base}/vendors", {"name": ""}).status == 400
    assert c.get(f"{base}/summary").json["vendors"]["booked"] == 1
    assert c.delete(f"{base}/vendors/{v['id']}").status == 204
    assert c.get(f"{base}/vendors").json == []


def test_050_051_exports(setup):
    app, c, ev, base = setup()
    cat = c.post(f"{base}/budget-categories", {"name": "Food", "plannedCents": 100}).json
    c.post(f"{base}/expenses", {"categoryId": cat["id"], "description": "=cmd|' /C calc'!A0", "amountCents": 12_345, "spentOn": "2026-11-01"})
    c.post(f"{base}/tasks", {"title": "@SUM(1+1)", "description": "a,b"})
    c.post(f"{base}/vendors", {"name": "V", "quoteCents": 500})

    j = c.get(f"{base}/export?format=json")
    assert j.headers["content-disposition"].startswith('attachment; filename="event-')
    data = j.json
    assert data["event"]["title"] == "Our wedding"
    assert [len(data[k]) for k in ("expenses", "tasks", "vendors", "budgetCategories")] == [1, 1, 1, 1]

    csv = c.get(f"{base}/export?format=csv&section=expenses")
    assert csv.headers["content-type"].startswith("text/csv")
    assert '"\'=cmd' in csv.text and '"123.45"' in csv.text
    tasks_csv = c.get(f"{base}/export?format=csv&section=tasks")
    assert "\"'@SUM(1+1)\"" in tasks_csv.text and '"a,b"' in tasks_csv.text
    assert c.get(f"{base}/export?format=xml").status == 400
    assert c.get(f"{base}/export?format=csv&section=users").status == 400


def test_per_event_limits(setup):
    app, c, ev, base = setup()
    for i in range(200):
        assert c.post(f"{base}/vendors", {"name": f"v{i}"}).status == 201
    r = c.post(f"{base}/vendors", {"name": "one too many"})
    assert r.status == 409 and r.json["error"]["code"] == "limit_reached"
