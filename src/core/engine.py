"""HermesSwarm 融合引擎 - 基因级融合 Hermes + JiuwenSwarm

这是融合项目的核心入口，协调工作流引擎、智能体系统、自进化引擎。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.config import FusionConfig
from src.core.events import EventBus, EventType


@dataclass
class FusionEngine:
    """融合引擎 - HermesSwarm 核心协调器

    融合点:
    - Hermes基因: AIAgent对话循环 + Curator自进化 + SessionDB
    - JiuwenSwarm基因: TeamManager + SwarmFlow + SwarmBuildContext
    - Codex基因: 协议/传输分离 + 模块<500LoC
    """

    config: FusionConfig
    event_bus: EventBus = field(default_factory=EventBus)

    # 子系统引用（延迟初始化）
    _workflow_engine: Any = None  # WorkflowEngine
    _skill_registry: Any = None   # SkillRegistry
    _memory: Any = None           # UnifiedMemory
    _evolution: Any = None        # EvolutionEngine
    _tool_registry: Any = None    # ToolRegistry
    _llm: Any = None              # LLMAdapter

    async def initialize(self) -> None:
        """初始化所有子系统"""
        await self.event_bus.publish_simple(
            EventType.WORKFLOW_STARTED,
            {"action": "engine_init"},
            source="fusion_engine",
        )

        # 初始化LLM适配器
        from src.llm.adapter import create_llm_adapter
        self._llm = create_llm_adapter(
            provider=self.config.model.provider,
            api_key=self.config.model.api_key,
            api_base=self.config.model.api_base,
        )

        # 初始化记忆系统（融合Hermes MemoryProvider + JiuwenSwarm MemoryIndexManager）
        from src.memory.unified import UnifiedMemory
        self._memory = UnifiedMemory(self.config.memory_db_path)

        # 初始化工具注册表（Hermes基因: AST自动发现）
        from src.tools.registry import ToolRegistry
        self._tool_registry = ToolRegistry(
            event_bus=self.event_bus,
            approval_required=self.config.tool_approval_required,
        )
        self._tool_registry.discover_builtin_tools()

        # 初始化技能注册中心（融合Hermes SKILL.md + JiuwenSwarm 单库+可见性）
        from src.skills.registry import SkillRegistry
        self._skill_registry = SkillRegistry(self.config)
        import os
        skills_dir = os.environ.get("HERMESSWARM_SKILLS_DIR", "")
        if skills_dir and os.path.isdir(skills_dir):
            self._skill_registry.discover(skills_dir)
        else:
            from pathlib import Path
            default_skills = Path(__file__).parent.parent.parent / "skills"
            if default_skills.exists():
                self._skill_registry.discover(default_skills)

        # 初始化工作流引擎（JiuwenSwarm基因: SwarmFlow + WorkflowRunState）
        from src.workflow.engine import WorkflowEngine
        self._workflow_engine = WorkflowEngine(
            event_bus=self.event_bus,
            skill_registry=self._skill_registry,
            tool_registry=self._tool_registry,
            memory=self._memory,
        )
        self._workflow_engine._llm = self._llm

        # 初始化自进化引擎（融合Hermes Curator + JiuwenSwarm Skill自演进）
        if self.config.hermes.self_evolution or self.config.jiwen.swarmflow:
            from src.agents.evolution import EvolutionEngine
            self._evolution = EvolutionEngine(
                config=self.config,
                skill_registry=self._skill_registry,
                memory=self._memory,
                event_bus=self.event_bus,
            )

    async def execute_workflow(self, workflow_data: dict[str, Any], input_data: Any = None) -> dict[str, Any]:
        """执行工作流（统一入口）

        数据流:
        1. 画布JSON → WorkflowEngine.create_from_canvas()
        2. 拓扑排序 → 节点执行队列
        3. 并行/串行执行 → 每个节点调用对应Agent/Tool
        4. HITL节点 → 发布事件等待前端回复
        5. 完成 → 触发自进化
        """
        if not self._workflow_engine:
            await self.initialize()

        # 创建工作流
        workflow = self._workflow_engine.create_from_canvas(workflow_data)

        # 执行
        result = await self._workflow_engine.execute(workflow.id, input_data)

        # 触发自进化（Hermes基因: 闭环学习）
        if self._evolution and self.config.hermes.self_evolution:
            await self._evolution.learn_from_execution(workflow, result)

        return result

    async def chat(self, message: str, session_id: str | None = None) -> str:
        """单智能体对话（Hermes基因: AIAgent.chat）

        当不需要工作流编排时，直接调用单智能体。
        """
        if not self._workflow_engine:
            await self.initialize()

        # 创建简单工作流: 输入 → Agent → 输出
        simple_workflow = {
            "name": "chat",
            "nodes": [
                {"id": "input", "type": "input", "label": "输入", "position": {"x": 100, "y": 100}},
                {"id": "agent", "type": "agent", "label": "智能体", "position": {"x": 300, "y": 100},
                 "config": {"agent_type": "specialist", "model": self.config.model.model_name}},
                {"id": "output", "type": "output", "label": "输出", "position": {"x": 500, "y": 100}},
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "agent"},
                {"id": "e2", "source": "agent", "target": "output"},
            ],
        }

        result = await self.execute_workflow(simple_workflow, message)
        return result.get("outputs", {}).get("agent", message)

    async def shutdown(self) -> None:
        """关闭所有子系统"""
        if self._memory:
            self._memory.close()
        await self.event_bus.publish_simple(
            EventType.WORKFLOW_COMPLETED,
            {"action": "engine_shutdown"},
            source="fusion_engine",
        )

    def get_status(self) -> dict[str, Any]:
        """获取引擎状态"""
        return {
            "initialized": self._workflow_engine is not None,
            "skills_count": len(self._skill_registry.skills) if self._skill_registry else 0,
            "tools_count": len(self._tool_registry.tools) if self._tool_registry else 0,
            "evolution_enabled": self._evolution is not None,
            "hermes_genes": self.config.hermes.__dict__,
            "jiuwen_genes": self.config.jiwen.__dict__,
        }

    def submit_hitl_reply(self, run_id: str, node_id: str, answer: str) -> bool:
        """提交HITL人工回复"""
        if self._workflow_engine:
            return self._workflow_engine.submit_hitl_reply(run_id, node_id, answer)
        return False

    def get_tools(self) -> list[dict[str, Any]]:
        """获取所有工具Schema"""
        if self._tool_registry:
            return self._tool_registry.get_schemas()
        return []


async def create_engine(config_path: str | None = None) -> FusionEngine:
    """创建并初始化融合引擎"""
    if config_path:
        config = FusionConfig.from_yaml(config_path)
    else:
        config = FusionConfig()
        config_path = config.get_default_config_path()
        config = FusionConfig.from_yaml(config_path)

    engine = FusionEngine(config=config)
    await engine.initialize()
    return engine
