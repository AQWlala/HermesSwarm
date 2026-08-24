"""GENERATE阶段 - LLM生成SKILL.md内容

JiuwenSwarm基因: 基于PLAN生成完整技能文档
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class GenerateStage(StageHandler):
    stage = SkillDevStage.GENERATE

    async def execute(self, state: SkillDevState) -> StageResult:
        plan = state.context.get("plan", {})
        skill_md_path = Path(state.context.get("skill_md_path", ""))

        if not self.llm:
            content = self._fallback_generate(state, plan)
        else:
            try:
                prompt = self._build_prompt(state, plan)
                response = await self.llm.complete(prompt)
                content = response.strip()
                if content.startswith("```markdown"):
                    content = content[len("```markdown"):]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            except Exception as e:
                return StageResult(success=False, error=f"LLM generate failed: {e}")

        if skill_md_path.parent.exists():
            skill_md_path.write_text(content, encoding="utf-8")

        state.context["generated_content"] = content

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=content,
            metadata={"content_length": len(content)},
            file_paths=[str(skill_md_path)] if skill_md_path.exists() else [],
        )
        return StageResult(success=True, artifact=artifact)

    def _build_prompt(self, state: SkillDevState, plan: dict) -> str:
        plan_str = str(plan)
        return f"""Generate a complete SKILL.md file for the following skill.

Skill Name: {state.skill_name}
Description: {state.skill_description}
Plan: {plan_str}

Requirements:
- YAML frontmatter with name, description, version, author, license, tags, category
- Markdown body with clear instructions
- Include ## Instructions section
- Include ## Examples section
- Be specific and actionable

Output the SKILL.md content only, no explanation."""

    def _fallback_generate(self, state: SkillDevState, plan: dict) -> str:
        sections = plan.get("structure", ["Instructions", "Examples"])
        body = f"# {state.skill_name}\n\n> {state.skill_description}\n\n"
        for section in sections:
            body += f"## {section}\n\n(Generated content)\n\n"
        return f"""---
name: {state.skill_name}
description: {state.skill_description}
version: 0.1.0-dev
author: hermesswarm-skilldev
license: Apache-2.0
tags: []
category: generated
related_skills: []
---

{body}"""