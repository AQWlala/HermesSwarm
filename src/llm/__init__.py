"""LLM适配器 - 统一接口支持 OpenAI / Anthropic / Demo降级"""

from __future__ import annotations

from src.llm.adapter import (
    DemoAdapter,
    LLMAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    create_llm_adapter,
)

__all__ = [
    "LLMAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "DemoAdapter",
    "create_llm_adapter",
]