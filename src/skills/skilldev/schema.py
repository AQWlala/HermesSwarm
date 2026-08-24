"""SkillDev状态定义 - 确定性流水线的状态机schema

JiuwenSwarm基因: 确定性状态机，每个阶段有明确的前置/后置条件
挂起点（suspend_point）允许人工审批或异步恢复
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SkillDevStage(str, Enum):
    """SkillDev流水线阶段（确定性顺序）"""
    INIT = "init"
    PLAN = "plan"
    GENERATE = "generate"
    VALIDATE = "validate"
    TEST = "test"
    EVALUATE = "evaluate"
    IMPROVE = "improve"
    PACKAGE = "package"
    DONE = "done"
    FAILED = "failed"
    SUSPENDED = "suspended"


_STAGE_ORDER = [
    SkillDevStage.INIT,
    SkillDevStage.PLAN,
    SkillDevStage.GENERATE,
    SkillDevStage.VALIDATE,
    SkillDevStage.TEST,
    SkillDevStage.EVALUATE,
    SkillDevStage.IMPROVE,
    SkillDevStage.PACKAGE,
    SkillDevStage.DONE,
]


def next_stage(current: SkillDevStage) -> SkillDevStage | None:
    """获取下一个阶段（确定性顺序）"""
    try:
        idx = _STAGE_ORDER.index(current)
        if idx + 1 < len(_STAGE_ORDER):
            return _STAGE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


class SuspendReason(str, Enum):
    """挂起原因"""
    HUMAN_APPROVAL = "human_approval"
    AWAITING_TEST_RESULT = "awaiting_test_result"
    AWAITING_EVAL_SCORE = "awaiting_eval_score"
    MANUAL_PAUSE = "manual_pause"
    ERROR_RETRY = "error_retry"


@dataclass
class StageArtifact:
    """阶段产出物"""
    stage: SkillDevStage
    timestamp: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    file_paths: list[str] = field(default_factory=list)


@dataclass
class StageResult:
    """阶段执行结果"""
    success: bool
    artifact: StageArtifact | None = None
    error: str = ""
    should_suspend: bool = False
    suspend_reason: SuspendReason | None = None
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class SkillDevState:
    """SkillDev流水线状态（可序列化到checkpoint）

    确定性保证:
    - stage + attempt_count 唯一确定执行路径
    - artifacts 记录每阶段产出，不可变（append-only）
    - suspend_point 记录挂起位置，恢复时从这里继续
    """
    pipeline_id: str
    skill_name: str
    skill_description: str = ""
    stage: SkillDevStage = SkillDevStage.INIT
    previous_stage: SkillDevStage | None = None
    attempt_count: int = 0
    max_attempts: int = 3

    # 阶段产出（append-only）
    artifacts: list[StageArtifact] = field(default_factory=list)

    # 挂起点
    suspended: bool = False
    suspend_reason: SuspendReason | None = None
    suspend_at_stage: SkillDevStage | None = None
    suspend_timestamp: str = ""

    # 评估分数（EVALUATE阶段产出）
    eval_scores: dict[str, float] = field(default_factory=dict)
    improve_iterations: int = 0
    max_improve_iterations: int = 3

    # 上下文（各阶段共享）
    context: dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 最终产出
    package_path: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为dict（用于checkpoint存储）"""
        return {
            "pipeline_id": self.pipeline_id,
            "skill_name": self.skill_name,
            "skill_description": self.skill_description,
            "stage": self.stage.value,
            "previous_stage": self.previous_stage.value if self.previous_stage else None,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "artifacts": [
                {
                    "stage": a.stage.value,
                    "timestamp": a.timestamp,
                    "content": a.content,
                    "metadata": a.metadata,
                    "file_paths": a.file_paths,
                }
                for a in self.artifacts
            ],
            "suspended": self.suspended,
            "suspend_reason": self.suspend_reason.value if self.suspend_reason else None,
            "suspend_at_stage": self.suspend_at_stage.value if self.suspend_at_stage else None,
            "suspend_timestamp": self.suspend_timestamp,
            "eval_scores": self.eval_scores,
            "improve_iterations": self.improve_iterations,
            "max_improve_iterations": self.max_improve_iterations,
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "package_path": self.package_path,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillDevState:
        """从dict反序列化"""
        artifacts = [
            StageArtifact(
                stage=SkillDevStage(a["stage"]),
                timestamp=a.get("timestamp", ""),
                content=a.get("content", ""),
                metadata=a.get("metadata", {}),
                file_paths=a.get("file_paths", []),
            )
            for a in data.get("artifacts", [])
        ]
        return cls(
            pipeline_id=data["pipeline_id"],
            skill_name=data["skill_name"],
            skill_description=data.get("skill_description", ""),
            stage=SkillDevStage(data.get("stage", "init")),
            previous_stage=SkillDevStage(data["previous_stage"]) if data.get("previous_stage") else None,
            attempt_count=data.get("attempt_count", 0),
            max_attempts=data.get("max_attempts", 3),
            artifacts=artifacts,
            suspended=data.get("suspended", False),
            suspend_reason=SuspendReason(data["suspend_reason"]) if data.get("suspend_reason") else None,
            suspend_at_stage=SkillDevStage(data["suspend_at_stage"]) if data.get("suspend_at_stage") else None,
            suspend_timestamp=data.get("suspend_timestamp", ""),
            eval_scores=data.get("eval_scores", {}),
            improve_iterations=data.get("improve_iterations", 0),
            max_improve_iterations=data.get("max_improve_iterations", 3),
            context=data.get("context", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            package_path=data.get("package_path", ""),
            error_message=data.get("error_message", ""),
        )

    def touch(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def add_artifact(self, artifact: StageArtifact) -> None:
        """追加阶段产出（append-only）"""
        if not artifact.timestamp:
            artifact.timestamp = datetime.now().isoformat()
        self.artifacts.append(artifact)
        self.touch()

    def get_artifact(self, stage: SkillDevStage) -> StageArtifact | None:
        """获取指定阶段的最新产出"""
        for a in reversed(self.artifacts):
            if a.stage == stage:
                return a
        return None