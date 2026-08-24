"""Agent Warm Pool预热 - JiuwenSwarm基因

维护已初始化未认领的agent会话，消除冷启动延迟:
- 后台预热agent实例
- config_fingerprint处理配置变更
- 前台/后台并发隔离

基因来源: JiuwenSwarm server/runtime/agent_warm_pool.py
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WarmSlot:
    """预热槽"""
    agent: Any
    config_fingerprint: str
    created_at: float = field(default_factory=time.time)
    claimed: bool = False


class AgentWarmPool:
    """Agent预热池

    进程本地维护一组已初始化、未认领的agent会话。
    """

    def __init__(self, max_size: int = 3, prewarm_enabled: bool = False):
        self.max_size = max_size
        self.prewarm_enabled = prewarm_enabled
        self._slots: list[WarmSlot] = []
        self._foreground_sem = asyncio.Semaphore(1)
        self._background_sem = asyncio.Semaphore(1)
        self._boot_id = str(time.time())

    def _compute_fingerprint(self, config: Any) -> str:
        """计算配置指纹"""
        try:
            import json
            data = json.dumps(config.__dict__, default=str, sort_keys=True)
            return hashlib.sha256(data.encode()).hexdigest()[:16]
        except Exception:
            return "unknown"

    async def acquire(self, config: Any, factory: Any) -> Any:
        """获取agent实例

        优先从预热池获取，否则现场创建。
        """
        fingerprint = self._compute_fingerprint(config)

        async with self._foreground_sem:
            for slot in self._slots:
                if not slot.claimed and slot.config_fingerprint == fingerprint:
                    slot.claimed = True
                    return slot.agent

        agent = await factory(config)
        return agent

    async def release(self, agent: Any) -> None:
        """释放agent实例（可复用）"""
        for slot in self._slots:
            if slot.agent is agent:
                slot.claimed = False
                return

    async def prewarm(self, config: Any, factory: Any) -> None:
        """后台预热"""
        if not self.prewarm_enabled:
            return

        fingerprint = self._compute_fingerprint(config)
        available = [s for s in self._slots if not s.claimed and s.config_fingerprint == fingerprint]

        if len(available) >= self.max_size:
            return

        async with self._background_sem:
            try:
                agent = await factory(config)
                self._slots.append(WarmSlot(
                    agent=agent,
                    config_fingerprint=fingerprint,
                ))
            except Exception:
                pass

    def cleanup_stale(self, max_age_seconds: int = 3600) -> int:
        """清理过期槽"""
        now = time.time()
        before = len(self._slots)
        self._slots = [
            s for s in self._slots
            if not s.claimed and (now - s.created_at) < max_age_seconds
        ]
        return before - len(self._slots)

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.prewarm_enabled,
            "max_size": self.max_size,
            "total_slots": len(self._slots),
            "available": sum(1 for s in self._slots if not s.claimed),
            "claimed": sum(1 for s in self._slots if s.claimed),
            "boot_id": self._boot_id,
        }