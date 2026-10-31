"""Chat model factory: Google Gemini, OpenAI (or compatible free-tier/local endpoints), and Hugging Face."""
from __future__ import annotations

import os
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ..config import AiSettings


def disable_telemetry() -> None:
    """Prompts contain event data; never ship them to a tracing service (SEC-012, RA-008)."""
    for name in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGCHAIN_TRACING"):
        os.environ[name] = "false"


def _role_of(msg: BaseMessage) -> str:
    if msg.type == "system":
        return "system"
    if msg.type == "ai":
        return "assistant"
    return "user"


def _serialize_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if isinstance(m.content, list):
            out.append({"role": _role_of(m), "content": m.content})
        else:
            out.append({"role": _role_of(m), "content": str(m.content)})
    return out


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Empty chat completion choices")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(part if isinstance(part, str) else str(part.get("text", "")) for part in content)
    return str(content)


class OpenAICompatibleChatModel(BaseChatModel):
    """Lightweight LangChain BaseChatModel speaking the OpenAI Chat Completions REST API.

    Works natively with Google Gemini (`https://generativelanguage.googleapis.com/v1beta/openai`),
    OpenAI (`https://api.openai.com/v1`), Groq, OpenRouter, Ollama, and local TGI/vLLM servers.
    """

    model_id: str
    endpoint_url: str
    api_key: str = ""
    timeout_s: float = 30.0
    max_tokens: int = 2500
    temperature: float = 0.4

    @property
    def _llm_type(self) -> str:
        return "openai-compatible"

    def _url(self) -> str:
        base = self.endpoint_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1") or base.endswith("/openai"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(self, messages: list[BaseMessage]) -> dict[str, Any]:
        return {
            "model": self.model_id,
            "messages": _serialize_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(self._url(), headers=self._headers(), json=self._payload(messages))
            resp.raise_for_status()
            text = _extract_content(resp.json())
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _agenerate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(self._url(), headers=self._headers(), json=self._payload(messages))
            resp.raise_for_status()
            text = _extract_content(resp.json())
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def build_chat_model(ai: AiSettings) -> BaseChatModel:
    disable_telemetry()
    if ai.provider in {"gemini", "openai"}:
        return OpenAICompatibleChatModel(
            model_id=ai.model_id or "gpt-4o-mini",
            endpoint_url=ai.endpoint_url,
            api_key=ai.token,
            timeout_s=ai.timeout_s,
            max_tokens=ai.max_new_tokens,
        )

    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

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
