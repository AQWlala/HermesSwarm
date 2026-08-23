"""Specialist智能体 - Hermes基因: 自进化 + 技能调用 + 闭环学习"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentConfig, AgentMode, AgentRole, BaseAgent


class SpecialistAgent(BaseAgent):
    """Specialist智能体（Hermes基因）

    职责: 独立执行任务 + 调用技能 + 自进化
    """

    def __init__(self, config: AgentConfig):
        config.role = AgentRole.SPECIALIST
        config.mode = AgentMode.SINGLE
        super().__init__(config)

    async def process(self, input: Any) -> Any:
        """处理: 发现技能 → LLM生成 → 记录"""
        skills = []
        if self.skill_registry:
            skills = self.skill_registry.discover_skills_for_task(str(input), limit=3)
            for skill in skills:
                self.skill_registry.record_usage(skill.id, "use")

        system_prompt = (
            f"你是{self.config.name}，一个专业AI智能体。"
            "请根据输入完成任务，输出简洁专业的结果。"
        )
        if skills:
            skill_names = "、".join(s.name for s in skills)
            system_prompt += f"\n可用技能: {skill_names}"

        input_text = str(input)
        if len(input_text) > 2000:
            input_text = input_text[:2000] + "...(截断)"

        llm_output = await self.llm_chat(input_text, system=system_prompt)

        result = {
            "agent": self.config.name,
            "input": str(input)[:500],
            "skills_used": [s.name for s in skills],
            "output": llm_output,
        }

        self.state.last_activity = self._now()
        return result
