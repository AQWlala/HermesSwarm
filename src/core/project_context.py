"""项目规范加载器 - 自动发现AGENTS.md/CLAUDE.md/.cursorrules

基因来源:
- Codex: AGENTS.md(22KB核心开发规范)
- Claude: CLAUDE.md项目级记忆
- Cursor: .cursorrules项目级指令

发现顺序(优先级从高到低):
1. AGENTS.md (Codex/HermesSwarm标准)
2. CLAUDE.md (Claude Code标准)
3. .cursorrules (Cursor标准)
4. .windsurfrules (Windsurf标准)

注入方式: 作为system prompt的前缀，不破坏提示缓存
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_SPEC_FILES = ["AGENTS.md", "CLAUDE.md", ".cursorrules", ".windsurfrules"]
_MAX_SPEC_SIZE = 50000


class ProjectContext:
    """项目规范上下文

    自动发现工作目录中的规范文件，构建项目级system prompt。
    规范内容被缓存，不随每次调用重新读取。
    """

    def __init__(self, project_dir: str | Path | None = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self._cached_spec: str | None = None
        self._cached_path: str | None = None

    def discover_spec(self) -> tuple[str, Path] | None:
        """发现项目规范文件

        Returns:
            (spec_content, spec_path) 或 None
        """
        if self._cached_spec is not None and self._cached_path is not None:
            return (self._cached_spec, Path(self._cached_path))

        for filename in _SPEC_FILES:
            spec_path = self.project_dir / filename
            if spec_path.exists():
                try:
                    content = spec_path.read_text(encoding="utf-8")
                    if len(content) > _MAX_SPEC_SIZE:
                        content = content[:_MAX_SPEC_SIZE] + "\n\n...(规范文件过大，已截断)"
                    self._cached_spec = content
                    self._cached_path = str(spec_path)
                    return (content, spec_path)
                except Exception:
                    continue
        return None

    def build_system_prefix(self) -> str:
        """构建system prompt前缀

        规范内容作为前缀注入，不破坏提示缓存不变性。
        """
        spec = self.discover_spec()
        if not spec:
            return ""
        content, path = spec
        return f"# Project Specification ({path.name})\n\n{content}\n\n---\n\n"

    def invalidate_cache(self) -> None:
        """失效缓存（规范文件变更时调用）"""
        self._cached_spec = None
        self._cached_path = None

    def get_status(self) -> dict[str, Any]:
        """获取状态"""
        spec = self.discover_spec()
        return {
            "project_dir": str(self.project_dir),
            "spec_file": self._cached_path,
            "spec_loaded": spec is not None,
            "spec_size": len(self._cached_spec) if self._cached_spec else 0,
        }