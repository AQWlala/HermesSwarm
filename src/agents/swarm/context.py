"""SwarmBuildContext - JiuwenSwarm基因: 声明式Spec装配上下文

提取自: jiuwenswarm/agents/swarm/context.py
核心心智模型: param vs context 边界
- param: config.yaml设定，换请求不变，config_specs烘焙
- context: 随请求/会话/成员动态变化，运行时注入
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SwarmBuildContext:
    """Swarm构建上下文（JiuwenSwarm基因）

    跨序列化边界通过seed重建: spawn/分布式/冷恢复
    """

    # 会话标识
    session_id: str = ""
    request_id: str | None = None
    channel_id: str | None = None
    channel: str = "default"

    # 执行模式
    mode: str = "team"  # team / code.team / team.plan / single

    # 工作区
    project_dir: str | None = None
    trusted_dirs: list[str] | None = None

    # 团队标识
    team_id: str = ""
    team_ws_root: str | None = None

    # 技能可见性
    team_skill_visibility_path: str | None = None
    global_skills_dir: str | None = None

    # 配置
    config: dict[str, Any] | None = None

    # 轨迹处理
    trajectory_span_processor: Any = None

    def to_seed(self) -> dict[str, Any]:
        """序列化为seed（跨进程/分布式重建）"""
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "channel_id": self.channel_id,
            "channel": self.channel,
            "mode": self.mode,
            "project_dir": self.project_dir,
            "team_id": self.team_id,
            "team_ws_root": self.team_ws_root,
            "team_skill_visibility_path": self.team_skill_visibility_path,
            "global_skills_dir": self.global_skills_dir,
        }

    @classmethod
    def from_seed(
        cls,
        seed: dict[str, Any],
        *,
        config: dict[str, Any] | None = None,
        trajectory_span_processor: Any = None,
    ) -> SwarmBuildContext:
        """从seed重建上下文（跨序列化边界）"""
        return cls(
            session_id=seed.get("session_id", ""),
            request_id=seed.get("request_id"),
            channel_id=seed.get("channel_id"),
            channel=seed.get("channel", "default"),
            mode=seed.get("mode", "team"),
            project_dir=seed.get("project_dir"),
            team_id=seed.get("team_id", ""),
            team_ws_root=seed.get("team_ws_root"),
            team_skill_visibility_path=seed.get("team_skill_visibility_path"),
            global_skills_dir=seed.get("global_skills_dir"),
            config=config,
            trajectory_span_processor=trajectory_span_processor,
        )


@dataclass
class AgentSpec:
    """智能体规格声明（JiuwenSwarm基因: 声明式装配）"""

    name: str
    role: str = "specialist"  # leader / teammate
    model: str = "gpt-4"
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    rails: list[str] = field(default_factory=list)
    subagents: list[str] = field(default_factory=list)

    # 参数（config_specs烘焙）
    params: dict[str, Any] = field(default_factory=dict)

    def build(self, context: SwarmBuildContext) -> Any:
        """构建运行时对象（由provider工厂实现）"""
        raise NotImplementedError


@dataclass
class TeamAgentSpec:
    """团队智能体规格（JiuwenSwarm基因: Leader + Teammates）"""

    team_name: str
    leader: AgentSpec = field(default_factory=lambda: AgentSpec(name="leader", role="leader"))
    teammates: list[AgentSpec] = field(default_factory=list)
    team_mode: str = "hybrid"  # hybrid / strict

    def build(self, context: SwarmBuildContext) -> dict[str, Any]:
        """构建团队"""
        return {
            "team_name": self.team_name,
            "leader": self.leader.build(context),
            "teammates": [t.build(context) for t in self.teammates],
            "team_mode": self.team_mode,
        }


def enrich_team_spec_for_swarm(
    spec: TeamAgentSpec,
    context: SwarmBuildContext,
) -> TeamAgentSpec:
    """装配入口（JiuwenSwarm基因: assembly.py的核心函数）

    1. 注册swarm providers
    2. 构建SwarmBuildContext
    3. 改写成员spec
    4. 挂build_context + seed
    """
    # 确保leader有正确的tools
    if not spec.leader.tools:
        spec.leader.tools = ["core.task_planning", "core.sys_operation"]

    # 确保teammates有基本tools
    for teammate in spec.teammates:
        if not teammate.tools:
            teammate.tools = ["core.web_search", "core.vision"]

    return spec
