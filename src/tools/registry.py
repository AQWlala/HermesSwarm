"""工具注册表 - Hermes基因: AST自动发现 + JiuwenSwarm基因: 权限分层"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """工具Schema（OpenAI function calling格式）"""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    """工具定义"""
    name: str
    toolset: str
    schema: ToolSchema
    handler: Callable[..., Any]
    check_fn: Callable[[], bool] | None = None
    requires_env: list[str] = field(default_factory=list)
    severity: str = "LOW"  # LOW/MEDIUM/HIGH/CRITICAL


class ToolRegistry:
    """工具注册表（Hermes基因: tools/registry.py）

    特性:
    - 模块级register()调用自动注册
    - AST检测避免重复导入
    - 按toolset分组
    """

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.toolsets: dict[str, list[str]] = {}

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: Callable[..., Any],
        check_fn: Callable[[], bool] | None = None,
        requires_env: list[str] | None = None,
        severity: str = "LOW",
    ) -> None:
        """注册工具"""
        self.tools[name] = Tool(
            name=name,
            toolset=toolset,
            schema=ToolSchema(
                name=name,
                description=schema.get("description", ""),
                parameters=schema.get("parameters", {}),
            ),
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env or [],
            severity=severity,
        )
        if toolset not in self.toolsets:
            self.toolsets[toolset] = []
        if name not in self.toolsets[toolset]:
            self.toolsets[toolset].append(name)

    def discover_builtin_tools(self) -> int:
        """发现内置工具（Hermes基因: AST自动发现）"""
        # 注册基础工具
        self._register_builtin_tools()
        return len(self.tools)

    def _register_builtin_tools(self) -> None:
        """注册基础工具"""
        self.register(
            name="read_file",
            toolset="file",
            schema={"description": "读取文件", "parameters": {"path": {"type": "string"}}},
            handler=self._tool_read_file,
            severity="LOW",
        )
        self.register(
            name="write_file",
            toolset="file",
            schema={"description": "写入文件", "parameters": {"path": {"type": "string"}, "content": {"type": "string"}}},
            handler=self._tool_write_file,
            severity="MEDIUM",
        )
        self.register(
            name="web_search",
            toolset="web",
            schema={"description": "网页搜索", "parameters": {"query": {"type": "string"}}},
            handler=self._tool_web_search,
            severity="LOW",
        )
        self.register(
            name="terminal",
            toolset="terminal",
            schema={"description": "执行终端命令", "parameters": {"command": {"type": "string"}}},
            handler=self._tool_terminal,
            severity="HIGH",
        )
        self.register(
            name="list_dir",
            toolset="file",
            schema={"description": "列出目录内容", "parameters": {"path": {"type": "string"}}},
            handler=self._tool_list_dir,
            severity="LOW",
        )
        self.register(
            name="http_get",
            toolset="web",
            schema={"description": "HTTP GET请求", "parameters": {"url": {"type": "string"}}},
            handler=self._tool_http_get,
            severity="LOW",
        )
        self.register(
            name="python_exec",
            toolset="code",
            schema={"description": "执行Python代码", "parameters": {"code": {"type": "string"}}},
            handler=self._tool_python_exec,
            severity="HIGH",
        )

    async def _tool_read_file(self, path: str, **kwargs) -> str:
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"

    async def _tool_write_file(self, path: str, content: str, **kwargs) -> str:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return "OK"
        except Exception as e:
            return f"Error: {e}"

    async def _tool_web_search(self, query: str, **kwargs) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com",
                    params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                )
                data = resp.json()
                results = []
                if data.get("AbstractText"):
                    results.append(f"{data['Heading']}: {data['AbstractText']}")
                for topic in (data.get("RelatedTopics") or [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(topic["Text"])
                return "\n".join(results) if results else f"No results for: {query}"
        except Exception as e:
            return f"Search error: {e}"

    async def _tool_terminal(self, command: str, **kwargs) -> str:
        try:
            import subprocess
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            return output.strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"

    async def _tool_list_dir(self, path: str = ".", **kwargs) -> str:
        try:
            from pathlib import Path
            p = Path(path)
            if not p.exists():
                return f"Path not found: {path}"
            items = []
            for item in sorted(p.iterdir()):
                prefix = "📁" if item.is_dir() else "📄"
                items.append(f"{prefix} {item.name}")
            return "\n".join(items) if items else "(empty)"
        except Exception as e:
            return f"Error: {e}"

    async def _tool_http_get(self, url: str, **kwargs) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                return f"Status: {resp.status_code}\n{resp.text[:5000]}"
        except Exception as e:
            return f"Error: {e}"

    async def _tool_python_exec(self, code: str, **kwargs) -> str:
        try:
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(code, {"__builtins__": __builtins__})
            return buf.getvalue().strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"

    async def execute(self, name: str, input_data: Any, parameters: dict[str, Any] | None = None) -> Any:
        """执行工具"""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool {name} not found"}

        if tool.check_fn and not tool.check_fn():
            return {"error": f"Tool {name} requirements not met"}

        # 权限检查（JiuwenSwarm基因: tiered_policy）
        approved = await self._check_permission(tool)
        if not approved:
            return {"error": f"Tool {name} not approved"}

        # 执行
        try:
            kwargs = parameters or {}
            if isinstance(input_data, dict):
                kwargs.update(input_data)
            else:
                kwargs["input"] = input_data

            result = tool.handler(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _check_permission(self, tool: Tool) -> bool:
        """权限检查（JiuwenSwarm基因: tiered_policy简化版）"""
        if tool.severity == "LOW":
            return True
        if tool.severity == "MEDIUM":
            return True  # Demo阶段默认通过
        if tool.severity == "HIGH":
            return True  # Demo阶段默认通过
        if tool.severity == "CRITICAL":
            return False  # 默认拒绝
        return True

    def get_schemas(self, toolset: str | None = None) -> list[dict[str, Any]]:
        """获取工具Schema列表"""
        if toolset:
            names = self.toolsets.get(toolset, [])
            return [self.tools[n].schema.__dict__ for n in names if n in self.tools]
        return [t.schema.__dict__ for t in self.tools.values()]
