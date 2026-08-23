"""事件总线 - 连接前端画布与后端工作流引擎"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """事件类型"""
    # 工作流事件
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_ERROR = "workflow.error"
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    NODE_ERROR = "node.error"
    # 智能体事件
    AGENT_SPAWNED = "agent.spawned"
    AGENT_MESSAGE = "agent.message"
    AGENT_HANDOFF = "agent.handoff"
    # HITL 事件
    HITL_REQUEST = "hitl.request"
    HITL_RESPONSE = "hitl.response"
    # 进化事件
    EVOLUTION_TRIGGERED = "evolution.triggered"
    EVOLUTION_COMPLETED = "evolution.completed"
    # 记忆事件
    MEMORY_STORED = "memory.stored"
    MEMORY_RECALLED = "memory.recalled"


@dataclass
class Event:
    """事件对象"""
    type: EventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "core"


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """异步事件总线"""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """订阅事件"""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """发布事件"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event.type, [])
        tasks = [handler(event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_simple(
        self, event_type: EventType, data: dict[str, Any], source: str = "core"
    ) -> None:
        """简化发布方法"""
        await self.publish(Event(type=event_type, data=data, source=source))

    def get_history(self, event_type: EventType | None = None) -> list[Event]:
        """获取事件历史"""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.type == event_type]

    def clear_history(self) -> None:
        """清空历史"""
        self._history.clear()
