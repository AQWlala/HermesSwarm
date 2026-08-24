"""PLAN阶段 - LLM生成技能开发计划

JiuwenSwarm基因: LLM规划技能结构、依赖、测试策略
"""

from __future__ import annotations

import json
from datetime import datetime

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class PlanStage(StageHandler):
    stage = SkillDevStage.PLAN

    async def execute(self, state: SkillDevState) -> StageResult:
        if not self.llm:
            plan = self._fallback_plan(state)
        else:
            try:
                prompt = self._build_prompt(state)
                response = await self.llm.complete(prompt)
                plan = self._parse_plan(response, state)
            except Exception as e:
                return StageResult(success=False, error=f"LLM plan failed: {e}")

        state.context["plan"] = plan

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=json.dumps(plan, ensure_ascii=False, indent=2),
            metadata={"plan_keys": list(plan.keys())},
        )
        return StageResult(success=True, artifact=artifact)

    def _build_prompt(self, state: SkillDevState) -> str:
        return f"""You are a skill development planner. Create a development plan for a new skill.

Skill Name: {state.skill_name}
Description: {state.skill_description}

Return a JSON object with:
- "structure": list of sections for SKILL.md
- "dependencies": list of required tools/capabilities
- "test_strategy": how to validate this skill
- "success_criteria": list of measurable criteria
- "estimated_complexity": "low" | "medium" | "high"

JSON only, no markdown."""

    def _parse_plan(self, response: str, state: SkillDevState) -> dict:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_plan(state)

    def _fallback_plan(self, state: SkillDevState) -> dict:
        return {
            "structure": ["Description", "Instructions", "Examples", "Constraints"],
            "dependencies": [],
            "test_strategy": "unit_test + integration_test",
            "success_criteria": ["all_tests_pass", "eval_score >= 0.7"],
            "estimated_complexity": "medium",
        }