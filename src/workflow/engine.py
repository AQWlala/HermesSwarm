"""工作流引擎 - 融合 JiuwenSwarm SwarmFlow + 可视化画布

数据流: 画布JSON → 拓扑排序 → 分层并行执行 → 状态更新 → 事件广播
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.events import EventBus, EventType
from src.workflow.state import (
    WorkflowEventKind,
    WorkflowProgress,
    WorkflowRunState,
)


class NodeType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    HITL = "hitl"
    SUBFLOW = "subflow"


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    label: str
    position: dict[str, float]
    config: dict[str, Any] = field(default_factory=dict)
    hermes_config: dict[str, Any] = field(default_factory=dict)
    jiwen_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEdge:
    id: str
    source: str
    target: str
    source_handle: str = ""
    target_handle: str = ""
    condition: str | None = None


@dataclass
class Workflow:
    id: str
    name: str
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)


@dataclass
class TopoSortResult:
    """拓扑排序结果"""
    layers: list[list[str]]
    has_cycle: bool
    cycle_nodes: list[str]


class WorkflowEngine:
    """工作流引擎

    融合: JiuwenSwarm SwarmFlow算子 + Hermes执行循环 + 画布可视化
    特性: 拓扑排序 + 分层并行执行 + 环检测 + HITL
    """

    def __init__(
        self,
        event_bus: EventBus,
        skill_registry: Any = None,
        tool_registry: Any = None,
        memory: Any = None,
    ):
        self.event_bus = event_bus
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.memory = memory
        self.workflows: dict[str, Workflow] = {}
        self.run_states: dict[str, WorkflowRunState] = {}
        self._hitl_futures: dict[str, asyncio.Future] = {}
        self._llm: Any = None

    def create_from_canvas(self, canvas_data: dict[str, Any]) -> Workflow:
        """从画布数据创建工作流"""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=canvas_data.get("name", "Untitled"),
            nodes=[
                WorkflowNode(
                    id=n["id"],
                    type=NodeType(n.get("type", "default")),
                    label=n.get("label", ""),
                    position=n.get("position", {"x": 0, "y": 0}),
                    config=n.get("config", {}),
                    hermes_config=n.get("hermesConfig", {}),
                    jiwen_config=n.get("jiwenConfig", {}),
                )
                for n in canvas_data.get("nodes", [])
            ],
            edges=[
                WorkflowEdge(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    source_handle=e.get("sourceHandle", ""),
                    target_handle=e.get("targetHandle", ""),
                    condition=e.get("condition") or e.get("label"),
                )
                for e in canvas_data.get("edges", [])
            ],
        )
        self.workflows[workflow.id] = workflow
        return workflow

    def topological_sort(self, workflow: Workflow) -> TopoSortResult:
        """Kahn算法拓扑排序，返回分层结果

        Returns:
            layers: 按执行顺序排列的层级，每层包含可并行执行的节点ID
            has_cycle: 是否存在环
            cycle_nodes: 环中的节点ID
        """
        node_ids = {n.id for n in workflow.nodes}
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adj: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for edge in workflow.edges:
            if edge.source in node_ids and edge.target in node_ids:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        layers: list[list[str]] = []
        remaining = set(node_ids)

        while remaining:
            current_layer = [nid for nid in remaining if in_degree[nid] == 0]
            if not current_layer:
                cycle_nodes = sorted(remaining)
                return TopoSortResult(layers=layers, has_cycle=True, cycle_nodes=cycle_nodes)

            input_nodes = [
                n.id for n in workflow.nodes
                if n.id in current_layer and n.type == NodeType.INPUT
            ]
            if input_nodes:
                current_layer = input_nodes + [nid for nid in current_layer if nid not in input_nodes]

            layers.append(current_layer)
            for nid in current_layer:
                remaining.discard(nid)
                for target in adj[nid]:
                    in_degree[target] -= 1

        return TopoSortResult(layers=layers, has_cycle=False, cycle_nodes=[])

    async def execute(self, workflow_id: str, input_data: Any = None) -> dict[str, Any]:
        """执行工作流（拓扑排序 + 分层并行执行）"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        run_state = WorkflowRunState(id=str(uuid.uuid4()), name=workflow.name)
        self.run_states[run_state.id] = run_state

        await self._emit(WorkflowEventKind.WORKFLOW_STARTED, run_state, workflow_name=workflow.name)
        await self._emit(WorkflowEventKind.PHASE, run_state, phase="topological_sort")

        topo = self.topological_sort(workflow)
        if topo.has_cycle:
            await self._emit(
                WorkflowEventKind.WORKFLOW_FAILED, run_state,
                message=f"检测到环: {topo.cycle_nodes}",
            )
            return {
                "run_id": run_state.id,
                "outputs": {},
                "status": "failed",
                "error": f"Cycle detected: {topo.cycle_nodes}",
            }

        await self._emit(WorkflowEventKind.PHASE, run_state, phase="execution")

        outputs: dict[str, Any] = {}
        node_map = {n.id: n for n in workflow.nodes}

        for layer_idx, layer in enumerate(topo.layers):
            await self._emit(
                WorkflowEventKind.PHASE, run_state,
                phase=f"layer_{layer_idx}",
            )

            tasks = []
            for node_id in layer:
                node = node_map[node_id]
                parent_output = self._collect_parent_output(workflow, node_id, outputs)
                task = self._execute_node_safe(
                    node, parent_output if parent_output is not None else input_data,
                    run_state,
                )
                tasks.append((node_id, task))

            results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
            for (node_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    outputs[node_id] = {"error": str(result)}
                else:
                    outputs[node_id] = result

        await self._emit(WorkflowEventKind.WORKFLOW_COMPLETED, run_state)

        return {
            "run_id": run_state.id,
            "outputs": outputs,
            "status": run_state.status,
            "layers": topo.layers,
        }

    def _collect_parent_output(
        self, workflow: Workflow, node_id: str, outputs: dict[str, Any]
    ) -> Any:
        """收集父节点输出作为输入"""
        parents = [e.source for e in workflow.edges if e.target == node_id]
        if not parents:
            return None
        if len(parents) == 1:
            return outputs.get(parents[0])
        return {parent: outputs.get(parent) for parent in parents}

    async def _execute_node_safe(
        self, node: WorkflowNode, input_data: Any, run_state: WorkflowRunState
    ) -> Any:
        """安全执行单个节点（带事件发射）"""
        await self._emit(
            WorkflowEventKind.AGENT_STARTED,
            run_state,
            label=node.label,
            node_type=node.type.value,
            agent_id=node.id,
        )
        try:
            result = await self._execute_node(node, input_data, run_state)
            await self._emit(
                WorkflowEventKind.AGENT_COMPLETED, run_state,
                label=node.label, agent_id=node.id,
            )
            return result
        except Exception as e:
            await self._emit(
                WorkflowEventKind.AGENT_FAILED, run_state,
                label=node.label, agent_id=node.id, message=str(e),
            )
            raise

    async def _execute_node(
        self, node: WorkflowNode, input_data: Any, run_state: WorkflowRunState
    ) -> Any:
        """执行单个节点"""
        if node.type == NodeType.AGENT:
            return await self._execute_agent(node, input_data)
        elif node.type == NodeType.TOOL:
            return await self._execute_tool(node, input_data)
        elif node.type == NodeType.CONDITION:
            return await self._execute_condition(node, input_data)
        elif node.type == NodeType.HITL:
            return await self._execute_hitl(node, input_data, run_state)
        elif node.type == NodeType.INPUT:
            return input_data
        elif node.type == NodeType.OUTPUT:
            return input_data
        else:
            return input_data

    async def _execute_agent(self, node: WorkflowNode, input_data: Any) -> Any:
        """执行Agent节点"""
        agent_type = node.config.get("agent_type", "specialist")
        model = node.config.get("model", "gpt-4")

        if agent_type == "leader":
            from src.agents.base import AgentConfig, AgentMode, AgentRole
            from src.agents.leader import LeaderAgent
            agent = LeaderAgent(AgentConfig(
                name=node.label, role=AgentRole.LEADER, mode=AgentMode.TEAM,
                model=model, tools=node.config.get("tools", []),
            ))
        else:
            from src.agents.base import AgentConfig, AgentMode, AgentRole
            from src.agents.specialist import SpecialistAgent
            agent = SpecialistAgent(AgentConfig(
                name=node.label, role=AgentRole.SPECIALIST, mode=AgentMode.SINGLE,
                model=model, tools=node.config.get("tools", []),
            ))

        agent.llm = self._llm
        agent.memory = self.memory
        agent.skill_registry = self.skill_registry
        agent.tool_registry = self.tool_registry

        return await agent.execute(input_data)

    async def _execute_tool(self, node: WorkflowNode, input_data: Any) -> Any:
        """执行Tool节点"""
        tool_name = node.config.get("tool_name", "")
        if self.tool_registry and tool_name:
            return await self.tool_registry.execute(
                tool_name, input_data, node.config.get("parameters", {})
            )
        return {"tool": tool_name, "input": str(input_data)[:200]}

    async def _execute_condition(self, node: WorkflowNode, input_data: Any) -> Any:
        """执行条件节点"""
        expr = node.config.get("expression", "True")
        try:
            result = eval(expr, {"__builtins__": {}}, {"data": input_data, "input": input_data})
            return {"condition": expr, "result": bool(result)}
        except Exception:
            return {"condition": expr, "result": True}

    async def _execute_hitl(
        self, node: WorkflowNode, input_data: Any, run_state: WorkflowRunState
    ) -> Any:
        """执行HITL节点（JiuwenSwarm基因: 人机协同）"""
        prompt = node.config.get("prompt", f"请审批: {str(input_data)[:200]}")
        timeout = node.config.get("timeout", 300)

        await self._emit(
            WorkflowEventKind.HUMAN_PROMPT, run_state,
            message=prompt, node_type="human",
        )

        await self.event_bus.publish_simple(
            EventType.HITL_REQUEST,
            {
                "run_id": run_state.id,
                "node_id": node.id,
                "prompt": prompt,
                "input": str(input_data)[:500],
            },
        )

        reply = await self._wait_for_human_reply(run_state.id, node.id, timeout)
        approved = reply != "timeout" and reply != "rejected"
        return {"approved": approved, "reply": reply, "input": input_data}

    async def _wait_for_human_reply(
        self, run_id: str, node_id: str, timeout: int = 300
    ) -> str:
        """等待人工回复"""
        future_key = f"{run_id}:{node_id}"
        future = asyncio.get_running_loop().create_future()
        self._hitl_futures[future_key] = future

        async def handler(event):
            if event.data.get("run_id") == run_id and event.data.get("node_id") == node_id:
                if not future.done():
                    future.set_result(event.data.get("answer", ""))

        self.event_bus.subscribe(EventType.HITL_RESPONSE, handler)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return "timeout"
        finally:
            self.event_bus.unsubscribe(EventType.HITL_RESPONSE, handler)
            self._hitl_futures.pop(future_key, None)

    def submit_hitl_reply(self, run_id: str, node_id: str, answer: str) -> bool:
        """提交人工回复（供API调用）"""
        future_key = f"{run_id}:{node_id}"
        future = self._hitl_futures.get(future_key)
        if future and not future.done():
            future.set_result(answer)
            return True
        return False

    async def _emit(
        self, kind: WorkflowEventKind, run_state: WorkflowRunState, **kwargs
    ) -> None:
        """发射工作流事件"""
        progress = WorkflowProgress(kind=kind, run_id=run_state.id, **kwargs)
        run_state.apply(progress)
        await self.event_bus.publish_simple(
            EventType.NODE_COMPLETED if kind == WorkflowEventKind.AGENT_COMPLETED
            else EventType.NODE_STARTED,
            {"kind": kind.value, "run_id": run_state.id, **kwargs},
        )

    def get_run_state(self, run_id: str) -> WorkflowRunState | None:
        return self.run_states.get(run_id)
