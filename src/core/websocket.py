"""WebSocket流式事件推送 - Codex/JiuwenSwarm基因

实时推送工作流执行进度到前端:
- 节点开始/完成/失败事件
- HITL请求事件
- 进化事件

基因来源: Codex app-server-transport/websocket.rs + JiuwenSwarm agent_ws_server.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class WebSocketManager:
    """WebSocket连接管理器

    维护活跃的WS连接，广播事件到所有连接的前端。
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._event_history: list[dict[str, Any]] = []
        self._max_history = 200

    async def connect(self, ws: WebSocket) -> None:
        """接受新连接"""
        await ws.accept()
        self._connections.append(ws)
        for event in self._event_history[-20:]:
            try:
                await ws.send_json(event)
            except Exception:
                pass

    def disconnect(self, ws: WebSocket) -> None:
        """断开连接"""
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """广播事件到所有连接"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_simple(self, event_type: str, **kwargs: Any) -> None:
        """简化广播方法"""
        await self.broadcast(event_type, kwargs)

    def get_status(self) -> dict[str, Any]:
        return {
            "connections": len(self._connections),
            "history_size": len(self._event_history),
        }

    async def close(self) -> None:
        """关闭所有连接"""
        for ws in self._connections:
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()


ws_manager = WebSocketManager()


async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket端点处理"""
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)