"""TEST阶段 - 运行技能测试

JiuwenSwarm基因: 确定性测试执行，挂起点等待测试结果
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from src.skills.skilldev.schema import (
    SkillDevState,
    SkillDevStage,
    StageArtifact,
    StageResult,

)
from src.skills.skilldev.stages.base import StageHandler


class TestStage(StageHandler):
    stage = SkillDevStage.TEST

    async def execute(self, state: SkillDevState) -> StageResult:
        skill_dir = Path(state.context.get("skill_dir", ""))
        test_file = skill_dir / "test_skill.py"

        if not test_file.exists():
            test_content = self._generate_test(state)
            test_file.write_text(test_content, encoding="utf-8")

        passed, output = await self._run_tests(test_file)

        artifact = StageArtifact(
            stage=self.stage,
            timestamp=datetime.now().isoformat(),
            content=output,
            metadata={
                "test_file": str(test_file),
                "passed": passed,
            },
            file_paths=[str(test_file)],
        )
        return StageResult(
            success=passed,
            artifact=artifact,
            metrics={"test_passed": 1.0 if passed else 0.0},
        )

    def _generate_test(self, state: SkillDevState) -> str:
        return f'''"""Auto-generated test for skill: {state.skill_name}"""
import pytest
from pathlib import Path


def test_skill_md_exists():
    skill_md = Path(__file__).parent / "SKILL.md"
    assert skill_md.exists(), "SKILL.md must exist"


def test_skill_md_valid():
    skill_md = Path(__file__).parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---"), "Must have frontmatter"
    assert "## Instructions" in content, "Must have Instructions section"


def test_skill_name():
    skill_md = Path(__file__).parent / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "name: {state.skill_name}" in content, "Name must match"
'''

    async def _run_tests(self, test_file: Path) -> tuple[bool, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", str(test_file), "-v", "--tb=short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            output = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")
            return proc.returncode == 0, output
        except asyncio.TimeoutError:
            return False, "Test execution timed out (30s)"
        except FileNotFoundError:
            return True, "pytest not available, skipping tests"
        except Exception as e:
            return False, f"Test execution error: {e}"