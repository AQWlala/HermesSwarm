"""WorkflowRunState - JiuwenSwarm基因: 工作流状态机

提取自: jiuwenswarm/agents/harness/team/handlers/workflow_state.py
纯pydantic模型，无外部依赖，可直接复用
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowEventKind(str, Enum):
    """工作流事件类型"""
    WORKFLOW_STARTED = "workflow_started"
    PHASE = "phase"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    HUMAN_PROMPT = "human_prompt"
    HUMAN_REPLIED = "human_replied"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    LOG = "log"


class WorkflowProgress(BaseModel):
    """工作流进度事件"""
    kind: WorkflowEventKind
    run_id: str | None = None
    workflow_name: str | None = None
    phase: str | None = None
    label: str | None = None
    node_type: str | None = None  # agent/agent_session/human/human_session
    agent_id: str | None = None  # 确定性resume-stable node id
    correlation_id: str | None = None  # session turn id
    answer: str | None = None  # HUMAN_REPLIED的真人回复
    tokens: int | None = None
    budget: dict[str, Any] | None = None
    message: str | None = None  # LOG消息


class WorkflowAgentState(BaseModel):
    """工作流中单个Agent节点状态"""
    id: str
    name: str
    status: str = "running"  # running/completed/failed/waiting_for_human
    kind: str = "agent"  # "agent" | "human"
    node_type: str | None = None
    correlation_id: str | None = None
    human_prompt: str | None = None
    human_reply: str | None = None
    tokens: int = 0
    error: str | None = None


class WorkflowPhaseState(BaseModel):
    """工作流Phase状态"""
    id: str
    name: str
    status: str = "running"  # running/completed/failed/planned
    agents: list[WorkflowAgentState] = Field(default_factory=list)
    phase_type: str | None = None  # "child" 等
    parent_phase: str | None = None


class WorkflowRunState(BaseModel):
    """工作流运行状态（核心状态机）

    纯数据结构，通过apply()方法消费事件更新状态
    """

    id: str
    name: str
    status: str = "running"  # running/completed/failed/stopped
    phases: list[WorkflowPhaseState] = Field(default_factory=list)
    budget: dict[str, Any] | None = None
    current_phase: str | None = None

    def apply(self, progress: WorkflowProgress) -> dict[str, Any] | None:
        """应用进度事件，返回增量delta

        核心方法: 消费WorkflowProgress事件，更新内部状态
        """
        handler = self._KIND_HANDLERS.get(progress.kind)
        if not handler:
            return None

        method = getattr(self, handler)
        return method(progress)

    def _on_workflow_started(self, progress: WorkflowProgress) -> dict[str, Any]:
        self.status = "running"
        if progress.workflow_name:
            self.name = progress.workflow_name
        return {"action": "workflow_started", "name": self.name}

    def _on_phase(self, progress: WorkflowProgress) -> dict[str, Any]:
        phase_name = progress.phase or ""
        old_phase = self.current_phase

        # 密封前一phase
        if old_phase:
            for p in self.phases:
                if p.name == old_phase and p.status == "running":
                    p.status = "completed"

        # 创建新phase
        phase = WorkflowPhaseState(
            id=f"phase_{len(self.phases)}",
            name=phase_name,
            status="running",
        )
        self.phases.append(phase)
        self.current_phase = phase_name

        return {"action": "phase_started", "phase": phase_name, "old_phase": old_phase}

    def _on_agent_started(self, progress: WorkflowProgress) -> dict[str, Any]:
        phase = self._get_or_create_current_phase(progress.phase)
        agent = WorkflowAgentState(
            id=progress.agent_id or progress.label or f"agent_{len(phase.agents)}",
            name=progress.label or "agent",
            status="running",
            kind="agent",
            node_type=progress.node_type,
            correlation_id=progress.correlation_id,
        )
        phase.agents.append(agent)
        return {"action": "agent_started", "agent_id": agent.id, "phase": phase.name}

    def _on_agent_completed(self, progress: WorkflowProgress) -> dict[str, Any]:
        agent = self._resolve_agent(progress.phase, progress.label, progress.agent_id, progress.correlation_id)
        if agent:
            agent.status = "completed"
            if progress.tokens:
                agent.tokens = progress.tokens
        return {"action": "agent_completed", "agent_id": agent.id if agent else None}

    def _on_agent_failed(self, progress: WorkflowProgress) -> dict[str, Any]:
        agent = self._resolve_agent(progress.phase, progress.label, progress.agent_id, progress.correlation_id)
        if agent:
            agent.status = "failed"
            agent.error = progress.message
        return {"action": "agent_failed", "agent_id": agent.id if agent else None}

    def _on_human_prompt(self, progress: WorkflowProgress) -> dict[str, Any]:
        """HITL: 人工提问"""
        phase = self._get_or_create_current_phase(progress.phase)
        agent = WorkflowAgentState(
            id=progress.agent_id or progress.label or f"human_{len(phase.agents)}",
            name=progress.label or "human",
            status="waiting_for_human",
            kind="human",
            node_type=progress.node_type,
            correlation_id=progress.correlation_id,
            human_prompt=progress.message,
        )
        phase.agents.append(agent)
        return {"action": "human_prompt", "agent_id": agent.id, "prompt": progress.message}

    def _on_human_replied(self, progress: WorkflowProgress) -> dict[str, Any]:
        """HITL: 人工回复"""
        agent = self._resolve_agent(progress.phase, progress.label, progress.agent_id, progress.correlation_id)
        if agent:
            agent.status = "completed"
            agent.human_reply = progress.answer
        return {"action": "human_replied", "agent_id": agent.id if agent else None}

    def _on_workflow_completed(self, progress: WorkflowProgress) -> dict[str, Any]:
        self.status = "completed"
        for p in self.phases:
            if p.status == "running":
                p.status = "completed"
        return {"action": "workflow_completed"}

    def _on_workflow_failed(self, progress: WorkflowProgress) -> dict[str, Any]:
        self.status = "failed"
        for p in self.phases:
            if p.status == "running":
                p.status = "failed"
        return {"action": "workflow_failed", "message": progress.message}

    def _on_log(self, progress: WorkflowProgress) -> dict[str, Any]:
        return {"action": "log", "message": progress.message}

    def _get_or_create_current_phase(self, phase_name: str | None = None) -> WorkflowPhaseState:
        """获取或创建当前phase"""
        target = phase_name or self.current_phase or "default"
        for p in self.phases:
            if p.name == target:
                return p
        phase = WorkflowPhaseState(id=f"phase_{len(self.phases)}", name=target, status="running")
        self.phases.append(phase)
        self.current_phase = target
        return phase

    def _resolve_agent(
        self,
        phase_name: str | None,
        label: str | None,
        agent_id: str | None,
        correlation_id: str | None,
    ) -> WorkflowAgentState | None:
        """解析agent（优先级: agent_id → correlation_id → label fallback）"""
        target_phase = phase_name or self.current_phase
        for p in self.phases:
            if p.name == target_phase:
                if agent_id:
                    for a in p.agents:
                        if a.id == agent_id:
                            return a
                if correlation_id:
                    for a in p.agents:
                        if a.correlation_id == correlation_id:
                            return a
                if label:
                    for a in p.agents:
                        if a.name == label:
                            return a
        return None

    def finalize_if_running(self, terminal_status: str = "stopped") -> None:
        """强制非终态run转终态"""
        if self.status in ("running",):
            self.status = terminal_status
            for p in self.phases:
                if p.status == "running":
                    p.status = terminal_status
                for a in p.agents:
                    if a.status == "running":
                        a.status = terminal_status
                    elif a.status == "waiting_for_human":
                        a.status = "failed"
                        a.error = "workflow terminated while waiting for human"

    _KIND_HANDLERS: dict[WorkflowEventKind, str] = {
        WorkflowEventKind.WORKFLOW_STARTED: "_on_workflow_started",
        WorkflowEventKind.PHASE: "_on_phase",
        WorkflowEventKind.AGENT_STARTED: "_on_agent_started",
        WorkflowEventKind.AGENT_COMPLETED: "_on_agent_completed",
        WorkflowEventKind.AGENT_FAILED: "_on_agent_failed",
        WorkflowEventKind.HUMAN_PROMPT: "_on_human_prompt",
        WorkflowEventKind.HUMAN_REPLIED: "_on_human_replied",
        WorkflowEventKind.WORKFLOW_COMPLETED: "_on_workflow_completed",
        WorkflowEventKind.WORKFLOW_FAILED: "_on_workflow_failed",
        WorkflowEventKind.LOG: "_on_log",
    }
