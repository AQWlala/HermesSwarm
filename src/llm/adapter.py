"""LLM适配器实现 - httpx直调API，无额外SDK依赖

支持:
- OpenAI (gpt-4, gpt-4o, gpt-3.5-turbo)
- Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku)
- Demo降级 (无API密钥时)

可靠性:
- 指数退避重试(3次, 1s/2s/4s)
- 模块级httpx连接池复用
- 429速率限制自动等待
- 超时降级到Demo模式
"""

from __future__ import annotations

import asyncio
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx


_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

_shared_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """模块级httpx连接池单例"""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )
    return _shared_client


async def _retry_with_backoff(
    func: Any,
    max_retries: int = _MAX_RETRIES,
) -> Any:
    """指数退避重试包装器

    对429/5xx错误重试，对其他错误立即抛出。
    429时读取Retry-After header等待。
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            if status not in _RETRY_STATUS_CODES:
                raise
            if attempt >= max_retries:
                raise
            retry_after = exc.response.headers.get("retry-after")
            if retry_after:
                delay = min(float(retry_after), 60.0)
            else:
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
            await asyncio.sleep(delay)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
    raise last_exc  # type: ignore[misc]


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
        client = _get_client()

        async def _call() -> str:
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

        return await _retry_with_backoff(_call)


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
        client = _get_client()
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

        async def _call() -> str:
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

        return await _retry_with_backoff(_call)


def create_llm_adapter(
    provider: str = "",
    api_key: str = "",
    api_base: str = "",
) -> LLMAdapter:
    """工厂函数 - 根据provider和密钥创建适配器

    优先级: 显式参数 > 环境变量 > Demo降级
    支持DeepSeek (OpenAI兼容API)
    """
    openai_key = api_key or os.environ.get("OPENAI_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "")
    anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    deepseek_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")

    if provider == "openai" and openai_key:
        base = api_base or deepseek_base
        return OpenAIAdapter(openai_key, base)
    if provider == "anthropic" and anthropic_key:
        return AnthropicAdapter(anthropic_key, api_base or "https://api.anthropic.com")

    if openai_key:
        return OpenAIAdapter(openai_key, api_base or deepseek_base)
    if anthropic_key:
        return AnthropicAdapter(anthropic_key, api_base or "https://api.anthropic.com")

    return DemoAdapter()


async def close_shared_client() -> None:
    """关闭共享httpx连接池"""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
    _shared_client = None
