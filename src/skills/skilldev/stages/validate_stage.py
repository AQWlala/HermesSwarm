"""VALIDATE阶段 - 验证SKILL.md格式和结构

JiuwenSwarm基因: 确定性验证，不依赖LLM
"""

from __future__ import annotations

from datetime import datetime

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class ValidateStage(StageHandler):
    stage = SkillDevStage.VALIDATE

    _REQUIRED_FIELDS = ["name", "description", "version"]
    _REQUIRED_SECTIONS = ["## Instructions"]

    async def execute(self, state: SkillDevState) -> StageResult:
        content = state.context.get("generated_content", "")
        errors: list[str] = []
        warnings: list[str] = []

        if not content:
            return StageResult(success=False, error="No generated content to validate")

        if not content.startswith("---"):
            errors.append("Missing YAML frontmatter (must start with ---)")

        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Invalid frontmatter structure")
        else:
            yaml_block = parts[1].strip()
            for field in self._REQUIRED_FIELDS:
                if f"{field}:" not in yaml_block:
                    errors.append(f"Missing required field: {field}")

            body = parts[2].strip()
            for section in self._REQUIRED_SECTIONS:
                if section not in body:
                    warnings.append(f"Missing recommended section: {section}")

            if not body.strip():
                errors.append("Empty body after frontmatter")

        import yaml
        try:
            yaml.safe_load(parts[1]) if len(parts) >= 3 else None
        except yaml.YAMLError as e:
            errors.append(f"YAML parse error: {e}")

        success = len(errors) == 0
        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content="\n".join(errors + warnings) if (errors or warnings) else "valid",
            metadata={
                "errors": errors,
                "warnings": warnings,
                "is_valid": success,
            },
        )
        return StageResult(
            success=success,
            artifact=artifact,
            error="; ".join(errors) if errors else "",
            metrics={"error_count": len(errors), "warning_count": len(warnings)},
        )