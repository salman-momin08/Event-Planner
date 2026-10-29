"""LangGraph workflow: prepare → generate → validate → (repair → generate)* → finish.

The model only drafts. The graph validates every reply against the Pydantic schema and business
rules, and gives the model a bounded number of chances to correct itself. Nothing here touches the
database or applies a plan.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from langgraph.graph import END, START, StateGraph

from ..errors import ApiError
from .prompts import PLAN_PROMPT
from .schemas import AiBadOutput, validate_plan


class PlanState(TypedDict, total=False):
    context_json: str
    messages: list[BaseMessage]
    raw: str
    plan: dict | None
    error: str | None
    attempts: int


def ai_unavailable() -> ApiError:
    return ApiError(503, "ai_unavailable", "The AI assistant is currently unavailable. Your plan is unchanged.")


def ai_timeout() -> ApiError:
    return ApiError(504, "ai_timeout", "The AI assistant took too long to respond. Your plan is unchanged.")


def _text_of(message: BaseMessage) -> str:
    content: Any = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part if isinstance(part, str) else str(part.get("text", "")) for part in content)
    return ""


def _parse_json(parser: JsonOutputParser, raw: str) -> Any:
    try:
        return parser.parse(raw)
    except (OutputParserException, ValueError):
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            return json.loads(raw[start : end + 1])
        raise


def build_plan_graph(model: BaseChatModel, *, timeout_s: float, max_repairs: int):
    parser = JsonOutputParser()

    async def prepare(state: PlanState) -> PlanState:
        return {"messages": PLAN_PROMPT.format_messages(context_json=state["context_json"]), "attempts": 0, "error": None}

    async def generate(state: PlanState) -> PlanState:
        try:
            reply = await asyncio.wait_for(model.ainvoke(state["messages"]), timeout=timeout_s)
        except asyncio.TimeoutError:
            raise ai_timeout() from None
        except ApiError:
            raise
        except Exception:  # provider/network failure: details stay out of responses
            raise ai_unavailable() from None
        return {"raw": _text_of(reply)[:60000], "attempts": state.get("attempts", 0) + 1}

    async def validate(state: PlanState) -> PlanState:
        try:
            parsed = _parse_json(parser, state["raw"])
        except (OutputParserException, ValueError):
            return {"plan": None, "error": "The reply was not a valid JSON object."}
        try:
            return {"plan": validate_plan(parsed), "error": None}
        except AiBadOutput as err:
            return {"plan": None, "error": err.reason}

    async def repair(state: PlanState) -> PlanState:
        feedback = (
            f"Your previous reply was rejected: {state['error']} "
            "Reply again with only the corrected JSON object, following every rule in the system message."
        )
        return {"messages": [*state["messages"], AIMessage(content=state["raw"]), HumanMessage(content=feedback)]}

    def route(state: PlanState) -> str:
        if state.get("plan") is not None:
            return "done"
        return "repair" if state.get("attempts", 0) <= max_repairs else "give_up"

    graph = StateGraph(PlanState)
    graph.add_node("prepare", prepare)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_node("repair", repair)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", route, {"done": END, "give_up": END, "repair": "repair"})
    graph.add_edge("repair", "generate")
    return graph.compile()


async def run_plan_graph(graph, context_json: str) -> dict:
    """Runs the graph and returns a validated plan, or raises a typed ApiError."""
    state = await graph.ainvoke({"context_json": context_json})
    if state.get("plan") is None:
        raise AiBadOutput(state.get("error") or "no plan produced")
    return state["plan"]
