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
        """处理: LLM分解任务 → 协调执行 → LLM汇总"""
        plan = await self.plan(str(input))
        results = []
        for subtask in plan["subtasks"]:
            result = await self._execute_subtask(subtask)
            results.append(result)
        return await self._aggregate(str(input), results)

    async def plan(self, task: str) -> dict[str, Any]:
        """任务规划（LLM分解）"""
        plan_text = await self.llm_chat(
            f"请将以下任务分解为2-3个子任务，用JSON数组格式返回，每个子任务包含description字段:\n{task}",
            system="你是团队Leader，负责任务分解。只返回JSON数组，不要其他文字。",
        )
        import json
        subtasks: list[dict[str, Any]] = []
        try:
            parsed = json.loads(plan_text)
            for i, item in enumerate(parsed):
                subtasks.append({
                    "id": i + 1,
                    "description": item.get("description", str(item)),
                    "agent": "specialist",
                })
        except Exception:
            subtasks = [
                {"id": 1, "description": f"分析: {task}", "agent": "specialist"},
                {"id": 2, "description": f"执行: {task}", "agent": "specialist"},
            ]

        return {"task": task, "subtasks": subtasks, "team_members": ["specialist_1", "specialist_2"]}

    async def _execute_subtask(self, subtask: dict[str, Any]) -> Any:
        """执行子任务"""
        from src.agents.specialist import SpecialistAgent
        agent = SpecialistAgent(AgentConfig(name=subtask.get("agent", "specialist")))
        agent.llm = self.llm
        agent.memory = self.memory
        agent.skill_registry = self.skill_registry
        agent.tool_registry = self.tool_registry
        return await agent.execute(subtask["description"])

    async def _aggregate(self, original_task: str, results: list[Any]) -> Any:
        """LLM汇总结果"""
        results_text = "\n".join(str(r) for r in results)
        summary = await self.llm_chat(
            f"原始任务: {original_task}\n子任务结果:\n{results_text}\n请汇总为最终结果。",
            system="你是团队Leader，负责结果汇总。简洁专业地总结。",
        )
        return {"summary": summary, "subtask_count": len(results), "results": results}
