"""INIT阶段 - 初始化技能开发请求

JiuwenSwarm基因: 流水线入口，验证输入，创建技能骨架
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class InitStage(StageHandler):
    stage = SkillDevStage.INIT

    async def execute(self, state: SkillDevState) -> StageResult:
        if not state.skill_name or not state.skill_description:
            return StageResult(
                success=False,
                error="skill_name and skill_description are required",
            )

        skill_dir = Path.home() / ".hermesswarm" / "skills-dev" / state.skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skeleton = f"""---
name: {state.skill_name}
description: {state.skill_description}
version: 0.1.0-dev
author: hermesswarm-skilldev
license: Apache-2.0
tags: []
category: generated
related_skills: []
---

# {state.skill_name}

> {state.skill_description}

## Instructions

(To be generated in GENERATE stage)
"""
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(skeleton, encoding="utf-8")

        state.context["skill_dir"] = str(skill_dir)
        state.context["skill_md_path"] = str(skill_md)

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=skeleton,
            metadata={"skill_dir": str(skill_dir)},
            file_paths=[str(skill_md)],
        )
        return StageResult(success=True, artifact=artifact)