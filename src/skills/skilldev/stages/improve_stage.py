"""IMPROVE阶段 - LLM改进技能内容

JiuwenSwarm基因: 基于EVALUATE分数改进，有最大迭代次数限制
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.skills.skilldev.schema import SkillDevState, SkillDevStage, StageArtifact, StageResult
from src.skills.skilldev.stages.base import StageHandler


class ImproveStage(StageHandler):
    stage = SkillDevStage.IMPROVE

    async def execute(self, state: SkillDevState) -> StageResult:
        if state.improve_iterations >= state.max_improve_iterations:
            return StageResult(
                success=True,
                artifact=StageArtifact(
                    stage=self.stage,
                    timestamp=datetime.now().isoformat(),
                    content="Max improve iterations reached, proceeding to PACKAGE",
                    metadata={"skipped": True, "iterations": state.improve_iterations},
                ),
            )

        content = state.context.get("generated_content", "")
        scores = state.eval_scores
        weak_dims = [d for d, s in scores.items() if s < 0.7]

        if not weak_dims:
            return StageResult(
                success=True,
                artifact=StageArtifact(
                    stage=self.stage,
                    timestamp=datetime.now().isoformat(),
                    content="All dimensions pass threshold, no improvement needed",
                    metadata={"skipped": True, "weak_dims": []},
                ),
            )

        if not self.llm:
            improved = content + f"\n\n<!-- Improved for: {', '.join(weak_dims)} -->\n"
        else:
            try:
                prompt = self._build_prompt(state, content, weak_dims)
                response = await self.llm.complete(prompt)
                improved = response.strip()
                if improved.startswith("```markdown"):
                    improved = improved[len("```markdown"):]
                if improved.startswith("```"):
                    improved = improved[3:]
                if improved.endswith("```"):
                    improved = improved[:-3]
                improved = improved.strip()
                if not improved:
                    improved = content
            except Exception as e:
                return StageResult(success=False, error=f"LLM improve failed: {e}")

        state.context["generated_content"] = improved
        state.improve_iterations += 1

        skill_md_path = Path(state.context.get("skill_md_path", ""))
        if skill_md_path.parent.exists():
            skill_md_path.write_text(improved, encoding="utf-8")

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=improved,
            metadata={
                "weak_dims": weak_dims,
                "iteration": state.improve_iterations,
                "improved": True,
            },
            file_paths=[str(skill_md_path)] if skill_md_path.exists() else [],
        )
        return StageResult(success=True, artifact=artifact)

    def _build_prompt(self, state: SkillDevState, content: str, weak_dims: list[str]) -> str:
        return f"""Improve this SKILL.md content, focusing on these weak dimensions: {', '.join(weak_dims)}

Current content:
{content}

Evaluation scores: {state.eval_scores}

Improve the weak dimensions while keeping the good parts.
Output the improved SKILL.md content only."""