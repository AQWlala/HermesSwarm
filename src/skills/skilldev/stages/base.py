"""SkillDev阶段处理器基类

JiuwenSwarm基因: 每个阶段是纯函数 (state, context) -> StageResult
确定性: 相同输入永远产生相同输出（LLM调用除外，但有重试保证）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageResult


class StageHandler(ABC):
    """阶段处理器基类

    约定:
    - execute() 是幂等的：重复执行同一阶段不产生副作用
    - 失败时返回 StageResult(success=False)，不抛异常
    - 需要人工审批时返回 should_suspend=True
    """

    stage: SkillDevStage

    def __init__(self, llm_adapter: Any = None, skill_registry: Any = None):
        self.llm = llm_adapter
        self.skill_registry = skill_registry

    @abstractmethod
    async def execute(self, state: SkillDevState) -> StageResult:
        """执行阶段逻辑"""
        ...

    def can_skip(self, state: SkillDevState) -> bool:
        """是否可跳过此阶段（默认不可跳过）"""
        return False