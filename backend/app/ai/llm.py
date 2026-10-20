"""Chat model factory: Hugging Face via the LangChain integration."""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import AiSettings


def disable_telemetry() -> None:
    """Prompts contain event data; never ship them to a tracing service (SEC-012, RA-008)."""
    for name in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGCHAIN_TRACING"):
        os.environ[name] = "false"


def build_chat_model(ai: AiSettings) -> BaseChatModel:
    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

    disable_telemetry()
    kwargs: dict = {
        "task": "text-generation",
        "max_new_tokens": ai.max_new_tokens,
        "temperature": 0.4,
        "timeout": ai.timeout_s,
        "huggingfacehub_api_token": ai.token or None,
    }
    if ai.endpoint_url:
        kwargs["endpoint_url"] = ai.endpoint_url
    else:
        kwargs["repo_id"] = ai.model_id
        kwargs["provider"] = ai.provider
    endpoint = HuggingFaceEndpoint(**kwargs)
    return ChatHuggingFace(llm=endpoint, model_id=ai.model_id or "tgi")
