"""EVALUATE阶段 - LLM评估技能质量

JiuwenSwarm基因: 多维度评分，挂起点等待人工确认分数
"""

from __future__ import annotations

import json
from datetime import datetime

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class EvaluateStage(StageHandler):
    stage = SkillDevStage.EVALUATE

    _DIMENSIONS = ["clarity", "completeness", "actionability", "correctness", "safety"]
    _PASS_THRESHOLD = 0.7

    async def execute(self, state: SkillDevState) -> StageResult:
        content = state.context.get("generated_content", "")

        if not self.llm:
            scores = {d: 0.75 for d in self._DIMENSIONS}
        else:
            try:
                prompt = self._build_prompt(state, content)
                response = await self.llm.complete(prompt)
                scores = self._parse_scores(response)
            except Exception as e:
                return StageResult(success=False, error=f"LLM evaluate failed: {e}")

        for d in self._DIMENSIONS:
            if d not in scores:
                scores[d] = 0.5
            scores[d] = max(0.0, min(1.0, float(scores[d])))

        state.eval_scores = scores
        overall = sum(scores.values()) / len(scores)
        state.context["eval_overall"] = overall
        passed = overall >= self._PASS_THRESHOLD

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=json.dumps(scores, indent=2),
            metadata={
                "scores": scores,
                "overall": overall,
                "threshold": self._PASS_THRESHOLD,
                "passed": passed,
            },
        )
        return StageResult(
            success=True,
            artifact=artifact,
            metrics={"overall_score": overall, "passed": 1.0 if passed else 0.0},
        )

    def _build_prompt(self, state: SkillDevState, content: str) -> str:
        return f"""Evaluate the quality of this SKILL.md content.

Skill: {state.skill_name}
Content:
{content[:2000]}

Score each dimension from 0.0 to 1.0:
- clarity: How clear are the instructions?
- completeness: Does it cover necessary aspects?
- actionability: Can an agent follow these instructions?
- correctness: Are the instructions technically correct?
- safety: Are there appropriate safety constraints?

Return JSON: {{"clarity": 0.x, "completeness": 0.x, "actionability": 0.x, "correctness": 0.x, "safety": 0.x}}
JSON only."""

    def _parse_scores(self, response: str) -> dict[str, float]:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            data = json.loads(text)
            return {k: float(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError, TypeError):
            return {d: 0.5 for d in self._DIMENSIONS}