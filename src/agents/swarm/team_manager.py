"""TeamManager - JiuwenSwarm基因的核心实现

提取自: jiuwenswarm/agents/harness/team/team_manager.py
核心心智模型:
- 管理团队实例 + 事件广播 + Skill演进Rails
- 事件队列上限64，慢速消费者背压 (TEAM_EVENT_QUEUE_MAXSIZE)
- 单一Skill库原则: authoring/review/reuse在同一物理库
- SwarmBuildContext: per-team字段，跨序列化边界通过seed重建
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.agents.swarm.context import AgentSpec, SwarmBuildContext, TeamAgentSpec


TEAM_EVENT_QUEUE_MAXSIZE = 64
_WAITER_PUT_RECHECK_TIMEOUT_SEC = 0.1


class TeamState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TeamEvent:
    """团队事件（JiuwenSwarm基因: 事件广播）"""
    type: str
    team_id: str
    member_name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TeamMember:
    """团队成员运行时实例"""
    name: str
    role: str
    spec: AgentSpec
    agent: Any = None
    status: str = "idle"
    last_activity: str = ""


@dataclass
class TeamInstance:
    """团队实例"""
    team_id: str
    team_name: str
    leader: TeamMember
    teammates: list[TeamMember] = field(default_factory=list)
    state: TeamState = TeamState.INITIALIZING
    context: SwarmBuildContext = field(default_factory=SwarmBuildContext)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    event_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=TEAM_EVENT_QUEUE_MAXSIZE))
    results: dict[str, Any] = field(default_factory=dict)


class TeamManager:
    """团队生命周期管理器（JiuwenSwarm基因: team_manager.py）

    职责:
    1. 创建/销毁团队实例
    2. 事件广播（背压: 队列满时await）
    3. Leader-Teammate装配
    4. 单一Skill库原则
    5. 分布式支持（通过seed重建）

    不变性:
    - 事件队列上限64，慢速消费者背压
    - Leader必须有AGENT.md
    - 成员从config源装配，不接收预构建DeepAgent
    """

    def __init__(self, skill_registry: Any = None, memory: Any = None):
        self.teams: dict[str, TeamInstance] = {}
        self.skill_registry = skill_registry
        self.memory = memory
        self._event_subscribers: dict[str, list[asyncio.Queue]] = {}

    async def create_team(
        self,
        spec: TeamAgentSpec,
        context: SwarmBuildContext,
    ) -> TeamInstance:
        """创建团队实例（JiuwenSwarm基因: assembly.py装配入口）

        1. enrich_team_spec_for_swarm: 装配Leader+Teammate
        2. 构建TeamInstance
        3. 初始化事件队列
        """
        from src.agents.swarm.context import enrich_team_spec_for_swarm
        spec = enrich_team_spec_for_swarm(spec, context)

        team_id = str(uuid.uuid4())[:8]
        leader = TeamMember(
            name=spec.leader.name,
            role="leader",
            spec=spec.leader,
        )
        teammates = [
            TeamMember(name=t.name, role="teammate", spec=t)
            for t in spec.teammates
        ]

        team = TeamInstance(
            team_id=team_id,
            team_name=spec.team_name,
            leader=leader,
            teammates=teammates,
            state=TeamState.RUNNING,
            context=context,
        )
        self.teams[team_id] = team

        await self._emit_event(team, "team.created", {
            "team_name": spec.team_name,
            "leader": leader.name,
            "teammates": [t.name for t in teammates],
        })
        return team

    async def execute_team(
        self,
        team_id: str,
        task: str,
        llm_adapter: Any = None,
    ) -> dict[str, Any]:
        """执行团队任务（Leader分解 → Teammate并行 → 汇总）"""
        team = self.teams.get(team_id)
        if not team:
            return {"error": f"team {team_id} not found"}
        if team.state != TeamState.RUNNING:
            return {"error": f"team {team_id} not running (state={team.state.value})"}

        await self._emit_event(team, "task.started", {"task": task[:200]})

        try:
            subtasks = await self._leader_plan(team, task, llm_adapter)
            await self._emit_event(team, "task.planned", {"subtasks": len(subtasks)})

            results = await self._teammates_execute(team, subtasks, llm_adapter)
            await self._emit_event(team, "teammates.completed", {
                "results": len(results),
            })

            summary = await self._leader_aggregate(team, task, results, llm_adapter)
            team.state = TeamState.COMPLETED
            team.results = {"summary": summary, "subtask_results": results}

            await self._emit_event(team, "task.completed", {
                "summary": summary[:200] if isinstance(summary, str) else str(summary)[:200],
            })

            if self.memory:
                from src.memory.unified import MemoryEntry
                self.memory.store(MemoryEntry(
                    id=f"team_{team_id}_{int(time.time())}",
                    content=f"Task: {task}\nSummary: {summary}",
                    type="episodic",
                    source="team",
                    metadata={"team_id": team_id, "team_name": team.team_name},
                ))

            return team.results

        except Exception as exc:
            team.state = TeamState.FAILED
            await self._emit_event(team, "task.failed", {"error": str(exc)})
            return {"error": str(exc), "team_id": team_id}

    async def _leader_plan(self, team: TeamInstance, task: str, llm: Any) -> list[dict[str, Any]]:
        """Leader分解任务"""
        if llm:
            prompt = (
                f"你是团队Leader '{team.leader.name}'。将任务分解为{len(team.teammates)}个子任务。\n"
                f"团队成员: {', '.join(t.name for t in team.teammates)}\n"
                f"任务: {task}\n\n"
                f"返回JSON数组，每个元素: {{\"assignee\": \"成员名\", \"description\": \"子任务描述\"}}"
            )
            try:

                resp_text = await llm.chat(prompt)
                import re
                json_match = re.search(r'\[[^\]]+\]', resp_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception:
                pass

        subtasks = []
        for i, member in enumerate(team.teammates):
            subtasks.append({
                "assignee": member.name,
                "description": f"{task} (部分{i+1})",
            })
        return subtasks

    async def _teammates_execute(
        self,
        team: TeamInstance,
        subtasks: list[dict[str, Any]],
        llm: Any,
    ) -> list[dict[str, Any]]:
        """Teammate并行执行（JiuwenSwarm基因: 并行协作）"""
        member_map = {m.name: m for m in team.teammates}

        async def execute_one(subtask: dict[str, Any]) -> dict[str, Any]:
            assignee = subtask.get("assignee", "")
            member = member_map.get(assignee)
            if not member:
                member = team.teammates[0] if team.teammates else None
                if not member:
                    return {"error": "no teammate available", "subtask": subtask}

            member.status = "running"
            member.last_activity = datetime.now().isoformat()
            await self._emit_event(team, "member.started", {
                "member": member.name,
                "subtask": subtask.get("description", "")[:100],
            })

            result = await self._member_execute(member, subtask, llm)

            member.status = "idle"
            member.last_activity = datetime.now().isoformat()
            await self._emit_event(team, "member.completed", {
                "member": member.name,
                "result_preview": str(result)[:100],
            })
            return {"member": member.name, "result": result}

        return await asyncio.gather(*[execute_one(st) for st in subtasks])

    async def _member_execute(self, member: TeamMember, subtask: dict[str, Any], llm: Any) -> Any:
        """单个成员执行子任务"""
        desc = subtask.get("description", "")
        skills_text = ""
        if self.skill_registry:
            skills = self.skill_registry.discover_skills_for_task(desc, limit=2, agent_name=member.name)
            for skill in skills:
                self.skill_registry.record_usage(skill.id, "use")
            if skills:
                skills_text = f"\n可用技能: {', '.join(s.name for s in skills)}"

        if llm:
            prompt = (
                f"你是团队成员 '{member.name}'，角色: {member.role}。\n"
                f"请完成以下子任务:\n{desc}{skills_text}\n\n"
                f"输出简洁专业的结果。"
            )
            try:
                return await llm.chat(prompt)
            except Exception as exc:
                return f"[执行错误: {exc}]"
        return f"[无LLM] 子任务: {desc}"

    async def _leader_aggregate(
        self,
        team: TeamInstance,
        original_task: str,
        results: list[dict[str, Any]],
        llm: Any,
    ) -> str:
        """Leader汇总结果"""
        results_text = "\n".join(
            f"- {r.get('member', '?')}: {str(r.get('result', ''))[:200]}"
            for r in results
        )
        if llm:
            prompt = (
                f"你是团队Leader '{team.leader.name}'。\n"
                f"原始任务: {original_task}\n\n"
                f"团队成员结果:\n{results_text}\n\n"
                f"请汇总为最终结果，简洁专业。"
            )
            try:
                return await llm.chat(prompt)
            except Exception:
                pass
        return f"任务完成。{len(results)}个成员参与。\n{results_text}"

    async def _emit_event(self, team: TeamInstance, event_type: str, data: dict[str, Any]) -> None:
        """发射事件（JiuwenSwarm基因: 背压队列上限64）

        队列满时短时超时重检（0.1s），检测孤儿队列避免永久阻塞。
        """
        event = TeamEvent(
            type=event_type,
            team_id=team.team_id,
            data=data,
        )
        try:
            team.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                await asyncio.wait_for(
                    team.event_queue.put(event),
                    timeout=_WAITER_PUT_RECHECK_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                pass

        for queue in self._event_subscribers.get(team.team_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    await asyncio.wait_for(
                        queue.put(event),
                        timeout=_WAITER_PUT_RECHECK_TIMEOUT_SEC,
                    )
                except asyncio.TimeoutError:
                    pass

    def subscribe_events(self, team_id: str) -> asyncio.Queue:
        """订阅团队事件"""
        queue: asyncio.Queue = asyncio.Queue(maxsize=TEAM_EVENT_QUEUE_MAXSIZE)
        if team_id not in self._event_subscribers:
            self._event_subscribers[team_id] = []
        self._event_subscribers[team_id].append(queue)
        return queue

    async def cancel_team(self, team_id: str) -> bool:
        """取消团队"""
        team = self.teams.get(team_id)
        if not team:
            return False
        team.state = TeamState.CANCELLED
        await self._emit_event(team, "team.cancelled", {})
        return True

    def get_team_status(self, team_id: str) -> dict[str, Any] | None:
        """获取团队状态"""
        team = self.teams.get(team_id)
        if not team:
            return None
        return {
            "team_id": team_id,
            "team_name": team.team_name,
            "state": team.state.value,
            "leader": team.leader.name,
            "teammates": [
                {"name": t.name, "status": t.status}
                for t in team.teammates
            ],
            "created_at": team.created_at,
        }

    def list_teams(self) -> list[dict[str, Any]]:
        """列出所有团队"""
        return [
            self.get_team_status(tid)
            for tid in self.teams
        ]

    def export_seed(self, team_id: str) -> dict[str, Any] | None:
        """导出seed（JiuwenSwarm基因: 跨序列化边界重建）"""
        team = self.teams.get(team_id)
        if not team:
            return None
        return {
            "team_id": team_id,
            "team_name": team.team_name,
            "context": team.context.to_seed(),
            "leader": {"name": team.leader.name, "role": team.leader.role},
            "teammates": [{"name": t.name, "role": t.role} for t in team.teammates],
        }