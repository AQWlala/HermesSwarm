"""斜杠命令处理 - REPL内置命令

类似claude-code的斜杠命令系统
"""

from __future__ import annotations

from typing import Any

from src.cli.display import (
    console,
    print_error,
    print_info,
    print_memory_results,
    print_skills,
    print_status,
    print_success,
    print_warning,
)


HELP_TEXT = """[bold]HermesSwarm CLI 命令[/bold]

[bold blue]对话[/bold blue]
  直接输入文本与agent对话

[bold blue]斜杠命令[/bold blue]
  /help              显示此帮助
  /status            引擎状态
  /skills            列出已加载技能
  /skills:discover   为当前任务发现技能
  /memory <query>    搜索记忆
  /memory:store      存储记忆 (后续输入内容)
  /curator           运行Curator自进化周期
  /curator:status    Curator状态
  /skilldev <name>   启动SkillDev流水线开发新技能
  /skilldev:list     列出SkillDev流水线
  /mcp:status        MCP客户端状态
  /mcp:tools         MCP工具列表
  /symphony          Symphony图演进统计
  /project           显示项目规范
  /exit              退出"""


class CommandHandler:
    """斜杠命令处理器"""

    def __init__(self, engine: Any):
        self.engine = engine

    async def handle(self, line: str) -> bool:
        """处理斜杠命令，返回True表示已处理（不需对话）"""
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        handler = {
            "/help": self._help,
            "/status": self._status,
            "/skills": self._skills,
            "/skills:discover": self._skills_discover,
            "/memory": self._memory_search,
            "/memory:store": self._memory_store,
            "/curator": self._curator_run,
            "/curator:status": self._curator_status,
            "/skilldev": self._skilldev_start,
            "/skilldev:list": self._skilldev_list,
            "/mcp:status": self._mcp_status,
            "/mcp:tools": self._mcp_tools,
            "/symphony": self._symphony,
            "/project": self._project,
            "/exit": self._exit,
            "/quit": self._exit,
        }.get(cmd)

        if handler is None:
            print_error(f"未知命令: {cmd}，输入 /help 查看可用命令")
            return True

        return await handler(arg)

    async def _help(self, _: str) -> bool:
        console.print(HELP_TEXT)
        return True

    async def _status(self, _: str) -> bool:
        print_status(self.engine.get_status())
        return True

    async def _skills(self, _: str) -> bool:
        if self.engine._skill_registry:
            skills = [
                {
                    "name": s.name,
                    "description": s.description,
                    "state": s.usage.state.value,
                    "use_count": s.usage.use_count,
                }
                for s in self.engine._skill_registry.skills.values()
            ]
            print_skills(skills)
        else:
            print_warning("技能系统未初始化")
        return True

    async def _skills_discover(self, task: str) -> bool:
        if not task:
            print_error("用法: /skills:discover <任务描述>")
            return True
        if self.engine._skill_registry:
            skills = self.engine._skill_registry.discover_skills_for_task(task, limit=5)
            print_skills([
                {"name": s.name, "description": s.description, "state": s.usage.state.value, "use_count": s.usage.use_count}
                for s in skills
            ])
        return True

    async def _memory_search(self, query: str) -> bool:
        if not query:
            print_error("用法: /memory <搜索词>")
            return True
        if self.engine._memory:
            results = self.engine._memory.search(query, limit=10)
            print_memory_results([
                {"id": r.id, "content": r.content, "score": r.score}
                for r in results
            ])
        return True

    async def _memory_store(self, content: str) -> bool:
        if not content:
            print_error("用法: /memory:store <内容>")
            return True
        if self.engine._memory:
            from src.memory.unified import MemoryEntry
            import time
            entry = MemoryEntry(id=f"mem_{int(time.time()*1000)}", content=content, type="long")
            self.engine._memory.store(entry)
            print_success(f"已存储记忆: {entry.id}")
        return True

    async def _curator_run(self, _: str) -> bool:
        if self.engine._evolution:
            print_info("运行Curator周期...")
            result = await self.engine._evolution.run_curator_cycle(llm_adapter=self.engine._llm)
            console.print(result)
        else:
            print_warning("Curator未初始化")
        return True

    async def _curator_status(self, _: str) -> bool:
        if self.engine._evolution and self.engine._evolution.curator:
            console.print(self.engine._evolution.curator.get_status())
        else:
            print_warning("Curator未初始化")
        return True

    async def _skilldev_start(self, name: str) -> bool:
        if not name:
            print_error("用法: /skilldev <技能名称>")
            return True
        if self.engine._skilldev:
            desc = input(f"输入 {name} 的描述: ").strip()
            if not desc:
                print_error("描述不能为空")
                return True
            print_info(f"启动SkillDev流水线: {name}")
            state = await self.engine._skilldev.start(name, desc)
            print_success(f"流水线完成: stage={state.stage.value}, suspended={state.suspended}")
            if state.package_path:
                print_info(f"已打包到: {state.package_path}")
            if state.error_message:
                print_error(state.error_message)
        return True

    async def _skilldev_list(self, _: str) -> bool:
        if self.engine._skilldev:
            pipelines = self.engine._skilldev.list_pipelines()
            if not pipelines:
                console.print("[dim]暂无流水线[/dim]")
            for p in pipelines:
                console.print(
                    f"  [bold]{p['skill_name']}[/bold] "
                    f"[dim]{p['stage']}[/dim] "
                    f"{'[yellow]suspended[/yellow]' if p.get('suspended') else ''}"
                )
        return True

    async def _mcp_status(self, _: str) -> bool:
        if self.engine._mcp_client:
            console.print(self.engine._mcp_client.get_status())
        return True

    async def _mcp_tools(self, _: str) -> bool:
        if self.engine._mcp_client:
            tools = self.engine._mcp_client.get_tools()
            if not tools:
                console.print("[dim]无MCP工具[/dim]")
            for t in tools:
                console.print(f"  [bold]{t['name']}[/bold] [dim]({t['server']})[/dim] - {t['description'][:60]}")
        return True

    async def _symphony(self, _: str) -> bool:
        if self.engine._symphony:
            console.print(self.engine._symphony.get_graph_stats())
        return True

    async def _project(self, _: str) -> bool:
        if self.engine._project_context:
            spec = self.engine._project_context.discover_spec()
            if spec:
                console.print(f"[bold]规范文件:[/bold] {spec[1]}")
                console.print(f"[dim]{spec[0][:500]}[/dim]")
            else:
                print_warning("未发现项目规范文件")
        return True

    async def _exit(self, _: str) -> bool:
        raise SystemExit(0)