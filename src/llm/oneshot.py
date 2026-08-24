"""Oneshot无状态LLM调用 - Hermes基因

非对话场景的纯文本LLM调用:
- 生成commit message、标题、摘要等小任务
- 从不触碰会话历史
- 不破坏提示缓存
- 返回纯文本

基因来源: Hermes agent/oneshot.py
"""

from __future__ import annotations

from typing import Any


_PROMPT_TEMPLATES: dict[str, str] = {
    "commit_message": "Based on the following changes, generate a concise commit message:\n\n{input}",
    "title": "Generate a short title (max 50 chars) for:\n\n{input}",
    "summary": "Summarize the following in 2-3 sentences:\n\n{input}",
    "classify": "Classify the following into one category. Respond with only the category name:\n\n{input}",
    "extract_keywords": "Extract 5 key terms from:\n\n{input}",
}


class OneshotCaller:
    """Oneshot无状态调用器

    与主agent对话循环完全隔离:
    - 不使用agent的system prompt缓存
    - 不记录到memory
    - 不触发技能发现
    - 纯文本输入→纯文本输出
    """

    def __init__(self, llm: Any = None):
        self.llm = llm

    async def call(
        self,
        prompt: str,
        system: str = "",
        model: str = "",
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        """无状态LLM调用"""
        if not self.llm:
            from src.llm.adapter import DemoAdapter
            self.llm = DemoAdapter()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.llm.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def call_template(
        self,
        template_name: str,
        input_text: str,
        **kwargs: Any,
    ) -> str:
        """使用预定义模板调用"""
        template = _PROMPT_TEMPLATES.get(template_name)
        if not template:
            return await self.call(input_text, **kwargs)
        prompt = template.format(input=input_text[:2000])
        return await self.call(prompt, **kwargs)

    async def commit_message(self, diff: str) -> str:
        """生成commit message"""
        return await self.call_template("commit_message", diff, system="You are a helpful assistant that writes concise git commit messages.")

    async def summarize(self, text: str) -> str:
        """生成摘要"""
        return await self.call_template("summary", text)

    async def title(self, text: str) -> str:
        """生成标题"""
        return await self.call_template("title", text)