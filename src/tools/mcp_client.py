"""MCP客户端集成 - Hermes/Codex基因

Model Context Protocol客户端:
- 连接外部MCP服务器
- 发现MCP工具并注册到工具注册表
- 支持stdio和HTTP传输

基因来源: Hermes tools/mcp_tool.py + Codex mcp/
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # stdio / http
    url: str = ""


@dataclass
class MCPTool:
    """MCP工具"""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


class MCPClient:
    """MCP客户端

    连接MCP服务器，发现工具，代理工具调用。
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPTool] = {}
        self._processes: dict[str, subprocess.Popen] = {}

    def register_server(self, config: MCPServerConfig) -> None:
        """注册MCP服务器"""
        self._servers[config.name] = config

    async def connect(self, server_name: str) -> bool:
        """连接MCP服务器"""
        config = self._servers.get(server_name)
        if not config:
            return False

        if config.transport == "stdio":
            return await self._connect_stdio(config)
        return False

    async def _connect_stdio(self, config: MCPServerConfig) -> bool:
        """stdio传输连接"""
        try:
            proc = subprocess.Popen(
                [config.command] + config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**__import__("os").environ, **config.env},
            )
            self._processes[config.name] = proc

            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"capabilities": {}},
            }
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()

            response = proc.stdout.readline()
            if response:
                await self._discover_tools(config.name)
                return True
        except Exception:
            pass
        return False

    async def _discover_tools(self, server_name: str) -> int:
        """发现MCP工具"""
        proc = self._processes.get(server_name)
        if not proc:
            return 0

        try:
            msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()

            response = proc.stdout.readline()
            data = json.loads(response)
            tools = data.get("result", {}).get("tools", [])

            for tool in tools:
                mcp_tool = MCPTool(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                    server_name=server_name,
                )
                self._tools[mcp_tool.name] = mcp_tool
            return len(tools)
        except Exception:
            return 0

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用MCP工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"MCP tool {tool_name} not found"}

        proc = self._processes.get(tool.server_name)
        if not proc:
            return {"error": f"Server {tool.server_name} not connected"}

        try:
            msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()

            response = proc.stdout.readline()
            data = json.loads(response)
            return data.get("result", {})
        except Exception as e:
            return {"error": str(e)}

    def get_tools(self) -> list[dict[str, Any]]:
        """获取所有MCP工具"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "server": t.server_name,
                "schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def disconnect(self, server_name: str) -> None:
        """断开服务器连接"""
        proc = self._processes.pop(server_name, None)
        if proc:
            proc.terminate()

    def disconnect_all(self) -> None:
        """断开所有连接"""
        for name in list(self._processes.keys()):
            self.disconnect(name)

    def get_status(self) -> dict[str, Any]:
        return {
            "servers": list(self._servers.keys()),
            "connected": list(self._processes.keys()),
            "tools": len(self._tools),
        }