"""LLM适配器实现 - httpx直调API，无额外SDK依赖

支持:
- OpenAI (gpt-4, gpt-4o, gpt-3.5-turbo)
- Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
- Demo降级 (无API密钥时)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx


class LLMAdapter(ABC):
    """LLM适配器基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        ...

    async def chat_simple(self, prompt: str, **kwargs: Any) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)


class DemoAdapter(LLMAdapter):
    """Demo适配器 - 无API密钥时降级"""

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[Demo模式] 已接收请求({len(user_msg)}字符)。配置API密钥后可启用真实LLM。"


class OpenAIAdapter(LLMAdapter):
    """OpenAI适配器 - httpx直调 /v1/chat/completions"""

    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class AnthropicAdapter(LLMAdapter):
    """Anthropic适配器 - httpx直调 /v1/messages"""

    def __init__(self, api_key: str, api_base: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

        async with httpx.AsyncClient(timeout=120) as client:
            payload: dict[str, Any] = {
                "model": model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system:
                payload["system"] = system
            resp = await client.post(
                f"{self.api_base}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]


def create_llm_adapter(
    provider: str = "",
    api_key: str = "",
    api_base: str = "",
) -> LLMAdapter:
    """工厂函数 - 根据provider和密钥创建适配器

    优先级: 显式参数 > 环境变量 > Demo降级
    """
    openai_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    if provider == "openai" and openai_key:
        return OpenAIAdapter(openai_key, api_base or "https://api.openai.com/v1")
    if provider == "anthropic" and anthropic_key:
        return AnthropicAdapter(anthropic_key, api_base or "https://api.anthropic.com")

    if openai_key:
        return OpenAIAdapter(openai_key, api_base or "https://api.openai.com/v1")
    if anthropic_key:
        return AnthropicAdapter(anthropic_key, api_base or "https://api.anthropic.com")

    return DemoAdapter()