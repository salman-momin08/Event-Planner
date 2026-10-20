from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from datetime import datetime, timezone
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from starlette.testclient import TestClient

from app.config import load_settings
from app.db import open_database
from app.logger import Logger
from app.main import create_app

FIXED_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
PASSWORD = "correct horse battery"


def valid_plan() -> dict:
    return {
        "summary": "A relaxed outdoor celebration.",
        "assumptions": ["Guests are mostly local"],
        "themes": [{"name": "Rustic garden", "description": "Wood, greenery, warm lights"}],
        "budgetAllocations": [
            {"category": "Venue", "percent": 40},
            {"category": "Catering", "percent": 33.33},
        ],
        "tasks": [
            {"title": "Book venue", "description": "Visit three venues", "category": "Venue", "daysBeforeEvent": 120},
            {"title": "Send invitations", "description": "", "category": "Guests", "daysBeforeEvent": 45},
        ],
        "vendorSuggestions": [{"category": "Catering", "guidance": "Ask about dietary options."}],
    }


class ScriptedChatModel(BaseChatModel):
    """Deterministic LangChain chat model. `respond(messages, call_number)` returns text, or raises."""

    respond: Any = None
    calls: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls.append(messages)
        text = self.respond(messages, len(self.calls))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.calls.append(messages)
        text = self.respond(messages, len(self.calls))
        if asyncio.iscoroutine(text):
            text = await text
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def scripted(respond=None) -> ScriptedChatModel:
    return ScriptedChatModel(respond=respond or (lambda _m, _n: json.dumps(valid_plan())))


class Resp:
    def __init__(self, r) -> None:
        self.response = r
        self.status = r.status_code
        self.text = r.text
        self.headers = r.headers
        try:
            self.json = r.json() if r.text else None
        except ValueError:
            self.json = None


class Client:
    """Cookie-keeping client; adds the CSRF header like the browser UI does."""

    def __init__(self, app, base_url: str = "http://testserver") -> None:
        self.http = TestClient(app, base_url=base_url, raise_server_exceptions=False)

    def request(self, method: str, path: str, body=None, *, csrf=True, headers=None, raw_body=None) -> Resp:
        h = dict(headers or {})
        if csrf:
            h["X-Requested-With"] = "planner"
        kwargs: dict = {}
        if raw_body is not None:
            kwargs["content"] = raw_body
            h.setdefault("Content-Type", "application/json")
        elif body is not None:
            kwargs["json"] = body
        return Resp(self.http.request(method, path, headers=h, **kwargs))

    def get(self, path, **kw):
        return self.request("GET", "/api/v1" + path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", "/api/v1" + path, body, **kw)

    def patch(self, path, body=None, **kw):
        return self.request("PATCH", "/api/v1" + path, body, **kw)

    def delete(self, path, body=None, **kw):
        return self.request("DELETE", "/api/v1" + path, body, **kw)


class Harness:
    def __init__(self, stack: ExitStack, env: dict, chat_model, clock, limits) -> None:
        self.settings = load_settings({"DATABASE_PATH": ":memory:", **env})
        self.db = open_database(":memory:")
        self.clock_value = clock
        self.app = create_app(
            self.settings,
            db=self.db,
            chat_model=chat_model,
            clock=lambda: self.clock_value,
            logger=Logger(silent=True),
            limits={"api": 100000, "login_ip": 100000, "login_account": 100000, "register": 100000, "ai_minute": 100000, **limits},
        )
        self.base_url = "https://testserver" if self.settings.cookie_secure else "http://testserver"
        stack.enter_context(TestClient(self.app, base_url=self.base_url))  # runs lifespan
        self._counter = 0

    def client(self) -> Client:
        return Client(self.app, self.base_url)

    def sign_up(self, name: str | None = None) -> Client:
        self._counter += 1
        name = name or f"user{self._counter}"
        c = self.client()
        r = c.post("/auth/register", {"email": f"{name}@example.com", "displayName": name, "password": PASSWORD})
        assert r.status == 201, r.text
        c.user = r.json
        return c

    def make_event(self, c: Client, **overrides) -> dict:
        body = {
            "type": "wedding", "title": "Our wedding", "eventDate": "2027-06-12", "attendance": 100,
            "location": "Pune", "budgetCents": 1_000_000, "currency": "USD", **overrides,
        }
        r = c.post("/events", body)
        assert r.status == 201, r.text
        return r.json


@pytest.fixture
def make_app():
    stack = ExitStack()

    def factory(*, env=None, chat_model=None, clock=FIXED_NOW, limits=None) -> Harness:
        return Harness(stack, env or {}, chat_model, clock, limits or {})

    yield factory
    stack.close()
