from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import AiSettings
from .graph import build_plan_graph


@dataclass
class AiRuntime:
    """Holds the compiled LangGraph workflow, or nothing when AI is not configured."""

    available: bool
    model_label: str
    graph: object | None = None

    @classmethod
    def disabled(cls) -> "AiRuntime":
        return cls(available=False, model_label="")

    @classmethod
    def from_chat_model(cls, model: BaseChatModel, ai: AiSettings, label: str | None = None) -> "AiRuntime":
        graph = build_plan_graph(model, timeout_s=ai.timeout_s, max_repairs=ai.max_repairs)
        return cls(available=True, model_label=label or ai.model_label or "custom", graph=graph)
