"""Pydantic schema for the model's plan. Validation here is the AI-output trust boundary (SEC-013)."""
from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, model_validator

from ..errors import ApiError
from ..validation import clean_text

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


class AiBadOutput(ApiError):
    def __init__(self, reason: str) -> None:
        super().__init__(502, "ai_bad_output", "The AI response could not be used. Nothing was changed.")
        self.reason = reason


def _scrub(text: str) -> str:
    return _PHONE.sub("[removed]", _URL.sub("[removed]", _EMAIL.sub("[removed]", text)))


def _ai_text(max_len: int, optional: bool = False):
    def convert(value: Any) -> str:
        if value is None and optional:
            return ""
        if not isinstance(value, str):
            raise ValueError("must be text")
        s = _scrub(clean_text(value))
        if not s and not optional:
            raise ValueError("must not be empty")
        return s[:max_len].rstrip()

    return Annotated[str, BeforeValidator(convert)]


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    return float(value)


def _whole(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) != int(value):
        raise ValueError("must be a whole number")
    return int(value)


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore")  # unknown keys from the model are dropped


class Theme(_Model):
    name: _ai_text(80)
    description: _ai_text(300, optional=True) = ""


class BudgetAllocation(_Model):
    category: _ai_text(80)
    percent: Annotated[float, BeforeValidator(_number), Field(gt=0, le=100)]


class PlanTask(_Model):
    title: _ai_text(120)
    description: _ai_text(300, optional=True) = ""
    category: _ai_text(80, optional=True) = ""
    daysBeforeEvent: Annotated[int, BeforeValidator(_whole), Field(ge=0, le=730)]
    dependsOn: Annotated[list[_ai_text(120)], Field(max_length=10)] = []


class VendorSuggestion(_Model):
    category: _ai_text(80)
    guidance: _ai_text(300)


class Plan(_Model):
    summary: _ai_text(600)
    assumptions: Annotated[list[_ai_text(200)], Field(max_length=10)] = []
    themes: Annotated[list[Theme], Field(min_length=1, max_length=5)]
    budgetAllocations: Annotated[list[BudgetAllocation], Field(min_length=1, max_length=12)]
    tasks: Annotated[list[PlanTask], Field(min_length=1, max_length=40)]
    vendorSuggestions: Annotated[list[VendorSuggestion], Field(max_length=10)] = []

    @model_validator(mode="after")
    def _business_rules(self) -> "Plan":
        if sum(round(b.percent, 2) for b in self.budgetAllocations) > 100.01:
            raise ValueError("budget percentages exceed 100")
        for label, values in (
            ("budget categories", [b.category for b in self.budgetAllocations]),
            ("task titles", [t.title for t in self.tasks]),
        ):
            lowered = [v.lower() for v in values]
            if len(set(lowered)) != len(lowered):
                raise ValueError(f"{label} contain duplicates")
        by_title = {t.title.lower(): t for t in self.tasks}
        graph: dict[str, list[str]] = {}
        for t in self.tasks:
            key = t.title.lower()
            deps: list[str] = []
            for dep in t.dependsOn:
                dep_key = dep.lower()
                if dep_key == key:
                    raise ValueError(f"task '{t.title}' cannot depend on itself")
                if dep_key not in by_title:
                    raise ValueError(f"task dependency '{dep}' does not match any task title in the plan")
                if dep_key not in deps:
                    deps.append(dep_key)
            graph[key] = deps
        for start in graph:
            seen: set[str] = set()
            stack = list(graph[start])
            while stack:
                cur = stack.pop()
                if cur == start:
                    raise ValueError("task dependencies must not form a cycle")
                if cur in seen:
                    continue
                seen.add(cur)
                stack.extend(graph.get(cur, []))
        return self


def validate_plan(raw: Any) -> dict:
    """Returns a normalised plan dict or raises AiBadOutput."""
    if not isinstance(raw, dict):
        raise AiBadOutput("plan must be an object")
    try:
        plan = Plan.model_validate(raw)
    except ValidationError as err:
        first = err.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "plan"
        raise AiBadOutput(f"{where}: {first['msg']}") from None
    dumped = plan.model_dump()
    for b in dumped["budgetAllocations"]:
        b["percent"] = round(b["percent"], 2)
    for t in dumped["tasks"]:
        if not t.get("dependsOn"):
            t.pop("dependsOn", None)
    return dumped
