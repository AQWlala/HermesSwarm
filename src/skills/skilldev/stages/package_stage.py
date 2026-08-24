"""PACKAGE阶段 - 打包技能到最终位置

JiuwenSwarm基因: 将dev技能移动到skills/目录，更新版本号
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class PackageStage(StageHandler):
    stage = SkillDevStage.PACKAGE

    async def execute(self, state: SkillDevState) -> StageResult:
        skill_dir = Path(state.context.get("skill_dir", ""))
        if not skill_dir.exists():
            return StageResult(success=False, error=f"Skill dir not found: {skill_dir}")

        target_base = Path.home() / ".hermesswarm" / "skills"
        target_base.mkdir(parents=True, exist_ok=True)
        target_dir = target_base / state.skill_name

        if target_dir.exists():
            backup = target_dir.with_suffix(".bak")
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(target_dir), str(backup))

        shutil.copytree(str(skill_dir), str(target_dir))

        skill_md = target_dir / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            content = content.replace("version: 0.1.0-dev", "version: 1.0.0")
            content = content.replace("category: generated", "category: agent-generated")
            skill_md.write_text(content, encoding="utf-8")

        if self.skill_registry:
            try:
                self.skill_registry.discover(str(target_base))
            except Exception:
                pass

        state.package_path = str(target_dir)

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=f"Packaged to {target_dir}",
            metadata={
                "package_path": str(target_dir),
                "skill_name": state.skill_name,
            },
            file_paths=[str(skill_md)],
        )
        return StageResult(success=True, artifact=artifact)