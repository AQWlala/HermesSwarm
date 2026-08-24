"""SkillDev阶段处理器注册

JiuwenSwarm基因: 确定性阶段注册，pipeline按顺序调用
"""

from __future__ import annotations

from typing import Any

from src.skills.skilldev.schema import SkillDevStage
from src.skills.skilldev.stages.base import StageHandler
from src.skills.skilldev.stages.init_stage import InitStage
from src.skills.skilldev.stages.plan_stage import PlanStage
from src.skills.skilldev.stages.generate_stage import GenerateStage
from src.skills.skilldev.stages.validate_stage import ValidateStage
from src.skills.skilldev.stages.test_stage import TestStage
from src.skills.skilldev.stages.evaluate_stage import EvaluateStage
from src.skills.skilldev.stages.improve_stage import ImproveStage
from src.skills.skilldev.stages.package_stage import PackageStage


def create_all_stages(llm_adapter: Any = None, skill_registry: Any = None) -> dict[SkillDevStage, StageHandler]:
    """创建所有阶段处理器实例"""
    common = {"llm_adapter": llm_adapter, "skill_registry": skill_registry}
    return {
        SkillDevStage.INIT: InitStage(**common),
        SkillDevStage.PLAN: PlanStage(**common),
        SkillDevStage.GENERATE: GenerateStage(**common),
        SkillDevStage.VALIDATE: ValidateStage(**common),
        SkillDevStage.TEST: TestStage(**common),
        SkillDevStage.EVALUATE: EvaluateStage(**common),
        SkillDevStage.IMPROVE: ImproveStage(**common),
        SkillDevStage.PACKAGE: PackageStage(**common),
    }