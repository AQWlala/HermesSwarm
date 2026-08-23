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
        """处理: 发现技能 → 执行 → 记录"""
        # 发现相关技能（Hermes基因: skill_utils）
        skills = []
        if self.skill_registry:
            skills = self.skill_registry.discover_skills_for_task(str(input), limit=3)
            for skill in skills:
                self.skill_registry.record_usage(skill.id, "use")

        # 执行（Demo: 直接返回结构化结果）
        result = {
            "agent": self.config.name,
            "input": str(input)[:500],
            "skills_used": [s.name for s in skills],
            "output": f"已处理: {input}",
        }

        # 记录活动
        self.state.last_activity = self._now()

        return result
