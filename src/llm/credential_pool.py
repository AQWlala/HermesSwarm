"""凭证池故障转移 - Hermes基因

同provider多凭证持久化故障转移池:
- 轮换使用多个API key
- 401/403时自动切换到下一个
- 全部失效时降级到Demo模式

基因来源: Hermes agent/credential_pool.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Credential:
    """凭证"""
    api_key: str
    api_base: str = ""
    label: str = ""
    failed_count: int = 0
    last_used: str = ""

    @property
    def is_valid(self) -> bool:
        return self.failed_count < 3 and bool(self.api_key)


class CredentialPool:
    """凭证池

    管理同provider的多个API凭证，自动故障转移。
    """

    def __init__(self) -> None:
        self._credentials: list[Credential] = []
        self._current_idx: int = 0

    def add(self, api_key: str, api_base: str = "", label: str = "") -> None:
        """添加凭证"""
        if api_key and not any(c.api_key == api_key for c in self._credentials):
            self._credentials.append(Credential(
                api_key=api_key,
                api_base=api_base,
                label=label or f"credential_{len(self._credentials)}",
            ))

    def load_from_env(self) -> None:
        """从环境变量加载凭证

        支持多key格式: KEY1,KEY2,KEY3
        """
        keys = []
        for env_var in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
            val = os.environ.get(env_var, "")
            if val:
                keys.extend(k.strip() for k in val.split(",") if k.strip())

        api_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
        for i, key in enumerate(keys):
            self.add(key, api_base, f"env_{i}")

    def get_current(self) -> Credential | None:
        """获取当前有效凭证"""
        valid = [c for c in self._credentials if c.is_valid]
        if not valid:
            return None
        if self._current_idx >= len(valid):
            self._current_idx = 0
        return valid[self._current_idx]

    def mark_failed(self, api_key: str) -> None:
        """标记凭证失败"""
        for c in self._credentials:
            if c.api_key == api_key:
                c.failed_count += 1
                break
        self._current_idx = (self._current_idx + 1) % max(len(self._credentials), 1)

    def mark_success(self, api_key: str) -> None:
        """标记凭证成功（重置失败计数）"""
        for c in self._credentials:
            if c.api_key == api_key:
                c.failed_count = 0
                break

    def get_status(self) -> dict[str, Any]:
        return {
            "total": len(self._credentials),
            "valid": sum(1 for c in self._credentials if c.is_valid),
            "current_idx": self._current_idx,
            "credentials": [
                {"label": c.label, "valid": c.is_valid, "failed": c.failed_count}
                for c in self._credentials
            ],
        }