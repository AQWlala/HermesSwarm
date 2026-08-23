"""Leader智能体 - JiuwenSwarm基因: 任务分解 + 团队组建 + 结果汇总"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentConfig, AgentMode, AgentRole, BaseAgent


class LeaderAgent(BaseAgent):
    """Leader智能体（JiuwenSwarm基因）

    职责: 分析需求 → 组建团队 → 拆解任务 → 汇总结果
    """

    def __init__(self, config: AgentConfig):
        config.role = AgentRole.LEADER
        config.mode = AgentMode.TEAM
        super().__init__(config)

    async def process(self, input: Any) -> Any:
        """处理: 分解任务并协调执行"""
        plan = await self.plan(str(input))
        results = []
        for subtask in plan["subtasks"]:
            result = await self._execute_subtask(subtask)
            results.append(result)
        return await self._aggregate(results)

    async def plan(self, task: str) -> dict[str, Any]:
        """任务规划（JiuwenSwarm基因: Leader分解）"""
        return {
            "task": task,
            "subtasks": [
                {"id": 1, "description": f"分析: {task}", "agent": "specialist"},
                {"id": 2, "description": f"执行: {task}", "agent": "specialist"},
                {"id": 3, "description": f"验证: {task}", "agent": "specialist"},
            ],
            "team_members": ["specialist_1", "specialist_2"],
        }

    async def _execute_subtask(self, subtask: dict[str, Any]) -> Any:
        """执行子任务"""
        from src.agents.specialist import SpecialistAgent
        agent = SpecialistAgent(AgentConfig(name=subtask.get("agent", "specialist")))
        return await agent.execute(subtask["description"])

    async def _aggregate(self, results: list[Any]) -> Any:
        """汇总结果"""
        return {"summary": f"完成{len(results)}个子任务", "results": results}
