"""HermesSwarm CLI REPL主循环

设计蓝本: claude-code/codex终端交互
核心: 单agent对话循环，用户输入→agent思考→工具调用→流式回复

Hermes基因: 提示缓存不变性 + SKILL.md技能加载
JiuwenSwarm基因: WarmPool预热 + 工具调用展示
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from src.cli.commands import CommandHandler
from src.cli.display import (
    console,
    print_assistant,
    print_banner,
    print_error,
    print_info,
    print_tool_call,
    print_tool_result,
    print_user,
    print_warning,
)


async def _build_system_prompt(engine: Any) -> str:
    """构建system prompt（Hermes基因: 提示缓存不变性）

    system prompt在会话期间byte-stable:
    - 项目规范前缀
    - 技能指令（按需加载，但加载后不变）
    - 工具schema
    """
    parts: list[str] = []

    parts.append("你是HermesSwarm，一个融合Hermes和JiuwenSwarm基因的AI智能体。")
    parts.append("你可以通过工具调用来读写文件、执行命令、搜索代码。")

    if engine._project_context:
        spec = engine._project_context.discover_spec()
        if spec:
            parts.append(f"\n# 项目规范\n{spec[0][:3000]}")

    if engine._skill_registry:
        skill_lines = []
        for skill in engine._skill_registry.skills.values():
            if skill.usage.state.value in ("active", "pinned"):
                skill_lines.append(f"- {skill.name}: {skill.description}")
        if skill_lines:
            parts.append("\n# 可用技能\n" + "\n".join(skill_lines))

    if engine._tool_registry:
        tool_lines = []
        for name, tool in engine._tool_registry.tools.items():
            tool_lines.append(f"- {name}: {tool.schema.description}")
        if tool_lines:
            parts.append("\n# 可用工具\n" + "\n".join(tool_lines))

    return "\n\n".join(parts)


def _parse_tool_calls(response: str) -> list[dict[str, Any]]:
    """从LLM响应中解析工具调用（简单JSON格式）

    约定LLM输出格式:
    ```tool
    {"name": "read_file", "args": {"path": "src/main.py"}}
    ```
    """
    tool_calls = []
    parts = response.split("```tool")
    for part in parts[1:]:
        end = part.find("```")
        if end == -1:
            continue
        json_str = part[:end].strip()
        try:
            call = json.loads(json_str)
            if "name" in call:
                tool_calls.append(call)
        except json.JSONDecodeError:
            continue
    return tool_calls


def _strip_tool_blocks(response: str) -> str:
    """移除工具调用块，返回纯文本回复"""
    result = response
    while "```tool" in result:
        start = result.find("```tool")
        end = result.find("```", start + 7)
        if end == -1:
            break
        result = result[:start] + result[end + 3:]
    return result.strip()


async def _execute_tool(engine: Any, tool_name: str, args: dict[str, Any]) -> tuple[Any, bool]:
    """执行工具调用，返回(result, success)"""
    if not engine._tool_registry:
        return "工具注册表未初始化", False

    tool = engine._tool_registry.tools.get(tool_name)
    if not tool:
        return f"工具 {tool_name} 不存在", False

    if tool.severity in ("HIGH", "CRITICAL") and engine._tool_registry.approval_required:
        console.print(f"  [yellow]⚠ 工具 {tool_name} 需要审批 (severity={tool.severity})[/yellow]")
        approval = input("  批准执行? (y/N): ").strip().lower()
        if approval != "y":
            return "用户拒绝执行", False

    try:
        result = await engine._tool_registry.execute(tool_name, args, args)
        return result, True
    except Exception as e:
        return str(e), False


async def _chat_loop(engine: Any) -> None:
    """REPL主循环"""
    cmd_handler = CommandHandler(engine)
    system_prompt = await _build_system_prompt(engine)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    print_info(f"已加载 {len(engine._skill_registry.skills) if engine._skill_registry else 0} 个技能，"
               f"{len(engine._tool_registry.tools) if engine._tool_registry else 0} 个工具")

    while True:
        try:
            console.print()
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            try:
                await cmd_handler.handle(user_input)
            except SystemExit:
                break
            continue

        print_user(user_input)
        messages.append({"role": "user", "content": user_input})

        if not engine._llm:
            print_error("LLM未初始化，请配置API密钥")
            continue

        console.print()
        try:
            response = await engine._llm.chat(messages, max_tokens=4096)
        except Exception as e:
            print_error(f"LLM调用失败: {e}")
            continue

        tool_calls = _parse_tool_calls(response)
        text_reply = _strip_tool_blocks(response)

        for call in tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            print_tool_call(tool_name, tool_args)
            result, success = await _execute_tool(engine, tool_name, tool_args)
            print_tool_result(tool_name, result, success)

            tool_result_str = json.dumps(result, ensure_ascii=False, default=str) if not isinstance(result, str) else result
            messages.append({"role": "assistant", "content": f"```tool\n{json.dumps(call)}\n```"})
            messages.append({"role": "user", "content": f"工具 {tool_name} 结果: {tool_result_str[:2000]}"})

            if success:
                try:
                    followup = await engine._llm.chat(messages, max_tokens=4096)
                    followup_text = _strip_tool_blocks(followup)
                    if followup_text:
                        text_reply = followup_text
                except Exception:
                    pass

        if text_reply:
            print_assistant(text_reply)
            messages.append({"role": "assistant", "content": text_reply})

        if len(messages) > 50:
            messages = [messages[0]] + messages[-40:]


async def _init_engine() -> Any:
    """初始化融合引擎"""
    from src.core.config import FusionConfig
    from src.core.engine import FusionEngine

    config = FusionConfig()
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        config.model.provider = "openai"
        config.model.api_key = api_key
        config.model.api_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
        config.model.model_name = os.environ.get("LLM_MODEL", "deepseek-chat")

    engine = FusionEngine(config=config)
    await engine.initialize()
    return engine


def main() -> None:
    """CLI入口点"""
    print_banner()

    try:
        engine = asyncio.run(_init_engine())
    except Exception as e:
        print_error(f"引擎初始化失败: {e}")
        print_info("提示: 设置 DEEPSEEK_API_KEY 环境变量以启用LLM")
        sys.exit(1)

    try:
        asyncio.run(_chat_loop(engine))
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(engine.shutdown())
        console.print("[dim]再见！[/dim]")


if __name__ == "__main__":
    main()