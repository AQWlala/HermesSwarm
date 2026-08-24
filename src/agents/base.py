"""智能体基类 - 融合 Hermes AIAgent + JiuwenSwarm DeepAgent 基因

Hermes基因: 自进化、记忆、技能、提示缓存
JiuwenSwarm基因: Leader-Teammate、SwarmBuildContext、HITL
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentRole(Enum):
    """智能体角色（JiuwenSwarm基因）"""
    LEADER = "leader"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"


class AgentMode(Enum):
    """执行模式"""
    SINGLE = "single"        # 单智能体（Hermes基因）
    TEAM = "team"            # 团队协作（JiuwenSwarm基因）
    DISTRIBUTED = "distributed"  # 分布式（JiuwenSwarm基因）


@dataclass
class AgentConfig:
    """智能体配置（融合配置）

    Hermes基因: personality, skills, memory, evolution
    JiuwenSwarm基因: role, team, collaboration, hitl
    """
    name: str
    role: AgentRole = AgentRole.SPECIALIST
    mode: AgentMode = AgentMode.SINGLE

    # Hermes基因
    personality: str = "default"
    skills: list[str] = field(default_factory=list)
    memory_enabled: bool = True
    evolution_enabled: bool = True
    max_iterations: int = 500

    # JiuwenSwarm基因
    team_size: int = 1
    collaboration_mode: str = "hybrid"  # parallel | sequential | hybrid
    hitl_required: bool = False

    # 模型配置
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    api_base: str = ""
    api_key: str = ""

    # 工具
    tools: list[str] = field(default_factory=list)
    toolsets: list[str] = field(default_factory=list)


@dataclass
class AgentState:
    """智能体运行时状态"""
    # Hermes基因: 自进化状态
    evolution_state: dict[str, Any] = field(default_factory=lambda: {
        "learned_skills": [],
        "improvements": [],
        "feedback_history": [],
    })

    # JiuwenSwarm基因: 协作状态
    collaboration_state: dict[str, Any] = field(default_factory=lambda: {
        "team_members": [],
        "current_task": None,
        "handoff_queue": [],
    })

    # 共享状态
    iterations: int = 0
    total_tokens: int = 0
    last_activity: str = ""


class BaseAgent(ABC):
    """智能体基类（融合基类）

    融合点:
    - Hermes: chat()对话循环, evolve()自进化, recall()记忆回溯
    - JiuwenSwarm: delegate()任务委派, handoff()交接, plan()团队规划
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.id = f"{config.name}_{id(self)}"
        self.state = AgentState()

        # 子系统引用（由引擎注入）
        self.memory: Any = None
        self.skill_registry: Any = None
        self.tool_registry: Any = None
        self.event_bus: Any = None
        self.llm: Any = None

        # 提示缓存不变性（Hermes基因: per-conversation prompt caching is sacred）
        # system prompt在会话期间byte-stable，不随技能加载/工具变更而改变
        self._cached_system_prompt: str | None = None
        self._prompt_cache_version: int = 0

    @abstractmethod
    async def process(self, input: Any) -> Any:
        """处理输入（抽象方法，由子类实现）"""
        ...

    async def execute(self, input: Any, **kwargs) -> Any:
        """统一执行入口"""
        self.state.iterations += 1

        # 预处理：记忆回溯（Hermes基因）
        if self.config.memory_enabled and self.memory:
            await self._recall_context(input)

        # 执行
        result = await self.process(input)

        # 后处理：记忆存储（Hermes基因）
        if self.config.memory_enabled and self.memory:
            await self._store_memory(input, result)

        return result

    async def llm_chat(self, prompt: str, system: str = "") -> str:
        """调用LLM生成回复（统一入口）

        提示缓存不变性（Hermes基因）:
        - system prompt在会话期间byte-stable
        - 首次调用时构建并缓存，后续调用复用
        - 技能/工具变更不破坏已有缓存
        """
        if not self.llm:
            from src.llm.adapter import DemoAdapter
            self.llm = DemoAdapter()

        cached_system = self._get_or_build_system_prompt(system)
        messages = []
        if cached_system:
            messages.append({"role": "system", "content": cached_system})
        messages.append({"role": "user", "content": prompt})
        return await self.llm.chat(
            messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

    def _get_or_build_system_prompt(self, explicit: str = "") -> str:
        """获取或构建system prompt（提示缓存不变性）

        优先级: 显式参数 > 缓存 > 构建
        一旦构建，后续调用复用缓存，不重建
        """
        if explicit:
            return explicit
        if self._cached_system_prompt is not None:
            return self._cached_system_prompt

        parts = [f"你是{self.config.name}，一个专业AI智能体。"]
        if self.skill_registry:
            skill_section = self.skill_registry.build_system_prompt_section()
            if skill_section:
                parts.append(skill_section)
        self._cached_system_prompt = "\n\n".join(parts)
        self._prompt_cache_version += 1
        return self._cached_system_prompt

    def invalidate_prompt_cache(self) -> None:
        """显式失效提示缓存（仅在技能/工具集变更时调用）"""
        self._cached_system_prompt = None

    # === Hermes基因: 自进化方法 ===

    async def evolve(self, feedback: str) -> dict[str, Any]:
        """自进化（Hermes闭环学习）

        数据流:
        1. 记录反馈到feedback_history
        2. 分析反馈类型(positive/negative/suggestion)
        3. 生成改进方案
        4. 应用改进(需审批时请求HITL)
        5. 更新技能进化分数
        """
        self.state.evolution_state["feedback_history"].append({
            "feedback": feedback,
            "timestamp": self._now(),
        })

        feedback_type = self._classify_feedback(feedback)

        if feedback_type == "negative":
            improvements = await self._generate_improvements(feedback)
            applied = []
            for imp in improvements:
                if self.config.hitl_required:
                    approved = await self._request_approval(imp)
                    if approved:
                        applied.append(await self._apply_improvement(imp))
                else:
                    applied.append(await self._apply_improvement(imp))
            return {"evolved": True, "changes": applied}
        elif feedback_type == "positive":
            await self._learn_from_success(feedback)
            return {"evolved": False, "action": "pattern_recorded"}

        return {"evolved": False, "action": "recorded"}

    async def _recall_context(self, input: Any) -> dict[str, Any]:
        """记忆回溯（Hermes基因: FTS5搜索）"""
        if isinstance(input, str) and self.memory:
            results = self.memory.search(input, limit=5)
            return {"recalled": results}
        return {}

    async def _store_memory(self, input: Any, output: Any) -> None:
        """存储记忆"""
        if self.memory:
            self.memory.store_interaction(
                agent_id=self.id,
                input=str(input)[:1000],
                output=str(output)[:1000],
            )

    async def _learn_from_success(self, feedback: str) -> None:
        """从成功中学习（提取模式）"""
        self.state.evolution_state["improvements"].append({
            "type": "success_pattern",
            "feedback": feedback,
            "timestamp": self._now(),
        })

    async def _generate_improvements(self, feedback: str) -> list[dict[str, Any]]:
        """生成改进方案"""
        return [{
            "suggestion": "基于反馈优化",
            "feedback": feedback,
            "timestamp": self._now(),
        }]

    async def _apply_improvement(self, improvement: dict[str, Any]) -> dict[str, Any]:
        """应用改进"""
        self.state.evolution_state["improvements"].append(improvement)
        return {"applied": True, "improvement": improvement}

    async def _request_approval(self, improvement: dict[str, Any]) -> bool:
        """请求审批（JiuwenSwarm基因: HITL）"""
        if self.event_bus:
            from src.core.events import EventType
            await self.event_bus.publish_simple(
                EventType.HITL_REQUEST,
                {"agent_id": self.id, "improvement": improvement},
            )
        return True  # 默认通过

    def _classify_feedback(self, feedback: str) -> str:
        """分类反馈"""
        lower = feedback.lower()
        if any(w in lower for w in ["好", "棒", "good", "great", "perfect"]):
            return "positive"
        if any(w in lower for w in ["差", "错", "bad", "wrong", "slow"]):
            return "negative"
        return "neutral"

    # === JiuwenSwarm基因: 协作方法 ===

    async def plan(self, task: str) -> dict[str, Any]:
        """任务规划（JiuwenSwarm基因: Leader分解任务）"""
        return {
            "task": task,
            "subtasks": [],  # 由LeaderAgent实现
            "team_members": [],
        }

    async def delegate(self, task: dict[str, Any], member_id: str | None = None) -> Any:
        """委派任务（JiuwenSwarm基因: Leader→Teammate）"""
        self.state.collaboration_state["handoff_queue"].append(task)
        return {"delegated": True, "task": task}

    async def handoff(self, target_agent_id: str, data: Any) -> Any:
        """交接数据（JiuwenSwarm基因: Teammate→Leader）"""
        if self.event_bus:
            from src.core.events import EventType
            await self.event_bus.publish_simple(
                EventType.AGENT_HANDOFF,
                {"from": self.id, "to": target_agent_id, "data": str(data)[:500]},
            )
        return {"handed_off": True}

    async def report(self, result: Any) -> None:
        """汇报结果（JiuwenSwarm基因: Teammate→Leader）"""
        if self.event_bus:
            from src.core.events import EventType
            await self.event_bus.publish_simple(
                EventType.AGENT_MESSAGE,
                {"agent_id": self.id, "result": str(result)[:500]},
            )

    # === 工具方法 ===

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()

    def get_status(self) -> dict[str, Any]:
        """获取智能体状态"""
        return {
            "id": self.id,
            "name": self.config.name,
            "role": self.config.role.value,
            "mode": self.config.mode.value,
            "iterations": self.state.iterations,
            "evolution_count": len(self.state.evolution_state["improvements"]),
            "feedback_count": len(self.state.evolution_state["feedback_history"]),
        }
