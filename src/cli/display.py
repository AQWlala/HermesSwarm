"""终端显示工具 - Rich美化输出

JiuwenSwarm基因: 终端流式输出 + 工具调用展示
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


console = Console()
err_console = Console(stderr=True)


def print_banner() -> None:
    """打印启动横幅"""
    banner = Text("☤ HermesSwarm", style="bold cyan")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))
    console.print("[dim]Hermes + JiuwenSwarm 融合智能体 · CLI模式[/dim]")
    console.print("[dim]输入 /help 查看命令，Ctrl+C 退出[/dim]")
    console.print()


def print_user(msg: str) -> None:
    """打印用户消息"""
    console.print(Panel(msg, title="[bold blue]You[/bold blue]", border_style="blue", padding=(0, 1)))


def print_assistant(msg: str) -> None:
    """打印agent回复（Markdown渲染）"""
    try:
        md = Markdown(msg)
        console.print(Panel(md, title="[bold green]Assistant[/bold green]", border_style="green", padding=(0, 1)))
    except Exception:
        console.print(Panel(msg, title="[bold green]Assistant[/bold green]", border_style="green", padding=(0, 1)))


def print_tool_call(tool_name: str, args: dict[str, Any]) -> None:
    """打印工具调用"""
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"  [bold yellow]⚙ {tool_name}[/bold yellow]({args_str})")


def print_tool_result(tool_name: str, result: Any, success: bool = True) -> None:
    """打印工具结果"""
    status = "[green]✓[/green]" if success else "[red]✗[/red]"
    text = str(result)
    if len(text) > 500:
        text = text[:500] + f"\n... ({len(text)} chars total)"
    console.print(f"  {status} [dim]{text}[/dim]")


def print_error(msg: str) -> None:
    """打印错误"""
    console.print(f"[bold red]✗ {msg}[/bold red]")


def print_info(msg: str) -> None:
    """打印信息"""
    console.print(f"[cyan]ℹ {msg}[/cyan]")


def print_success(msg: str) -> None:
    """打印成功"""
    console.print(f"[green]✓ {msg}[/green]")


def print_warning(msg: str) -> None:
    """打印警告"""
    console.print(f"[yellow]⚠ {msg}[/yellow]")


def print_skills(skills: list[dict[str, Any]]) -> None:
    """打印技能列表"""
    if not skills:
        console.print("[dim]暂无技能[/dim]")
        return
    for s in skills:
        state_color = {"active": "green", "stale": "yellow", "archived": "dim", "pinned": "cyan"}.get(
            s.get("state", ""), "white"
        )
        console.print(
            f"  [{state_color}]●[/{state_color}] [bold]{s['name']}[/bold] "
            f"[dim](used {s.get('use_count', 0)}x)[/dim] - {s.get('description', '')[:60]}"
        )


def print_memory_results(results: list[dict[str, Any]]) -> None:
    """打印记忆搜索结果"""
    if not results:
        console.print("[dim]无匹配记忆[/dim]")
        return
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        console.print(f"  [bold]{i}.[/bold] [dim](score={score:.2f})[/dim] {r['content'][:100]}")


def print_status(status: dict[str, Any]) -> None:
    """打印引擎状态"""
    console.print(Panel(
        f"[bold]技能:[/bold] {status.get('skills_count', 0)}  "
        f"[bold]工具:[/bold] {status.get('tools_count', 0)}  "
        f"[bold]进化:[/bold] {'✓' if status.get('evolution_enabled') else '✗'}  "
        f"[bold]WarmPool:[/bold] {status.get('warm_pool_size', 0)}  "
        f"[bold]MCP:[/bold] {status.get('mcp_connected', 0)}",
        title="[bold]引擎状态[/bold]",
        border_style="dim",
    ))


def stream_text(text: str, delay: float = 0.01) -> None:
    """模拟流式输出"""
    import time
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()