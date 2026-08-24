"""SkillDev流水线编排器 - 确定性状态机

JiuwenSwarm基因: 确定性流水线 INIT→PLAN→GENERATE→VALIDATE→TEST→EVALUATE→IMPROVE→PACKAGE
- 每阶段完成后checkpoint持久化
- 挂起点支持人工干预和异步恢复
- IMPROVE→EVALUATE循环（受max_improve_iterations限制）
- 失败重试（受max_attempts限制）
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.skills.skilldev.schema import (
    SkillDevState,
    SkillDevStage,
    StageResult,
    SuspendReason,
    next_stage,
)
from src.skills.skilldev.store import SkillDevStore
from src.skills.skilldev.stages import create_all_stages


class SkillDevPipeline:
    """SkillDev确定性流水线

    使用方法:
        pipeline = SkillDevPipeline(llm_adapter=llm, skill_registry=reg)
        state = await pipeline.start("my-skill", "A skill that does X")
        # 或恢复:
        state = await pipeline.resume("pipeline-id")
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        skill_registry: Any = None,
        store: SkillDevStore | None = None,
    ):
        self.llm = llm_adapter
        self.skill_registry = skill_registry
        self.store = store or SkillDevStore()
        self.stages = create_all_stages(
            llm_adapter=llm_adapter,
            skill_registry=skill_registry,
        )

    async def start(
        self,
        skill_name: str,
        skill_description: str,
        pipeline_id: str | None = None,
    ) -> SkillDevState:
        """启动新流水线"""
        state = SkillDevState(
            pipeline_id=pipeline_id or f"skilldev_{uuid.uuid4().hex[:12]}",
            skill_name=skill_name,
            skill_description=skill_description,
        )
        self.store.save(state)
        return await self._run(state)

    async def resume(self, pipeline_id: str) -> SkillDevState | None:
        """恢复挂起的流水线"""
        state = self.store.load(pipeline_id)
        if state is None:
            return None
        if state.suspended:
            state.suspended = False
            state.suspend_reason = None
            state.suspend_at_stage = None
            state.suspend_timestamp = ""
            self.store.save(state)
        return await self._run(state)

    async def pause(self, pipeline_id: str) -> bool:
        """手动暂停流水线"""
        state = self.store.load(pipeline_id)
        if state is None or state.stage in (SkillDevStage.DONE, SkillDevStage.FAILED):
            return False
        state.suspended = True
        state.suspend_reason = SuspendReason.MANUAL_PAUSE
        state.suspend_at_stage = state.stage
        state.suspend_timestamp = datetime.now().isoformat()
        self.store.save(state)
        return True

    async def _run(self, state: SkillDevState) -> SkillDevState:
        """运行状态机直到完成或挂起"""
        while state.stage not in (SkillDevStage.DONE, SkillDevStage.FAILED, SkillDevStage.SUSPENDED):
            if state.suspended:
                break

            handler = self.stages.get(state.stage)
            if handler is None:
                state.stage = SkillDevStage.FAILED
                state.error_message = f"No handler for stage: {state.stage}"
                self.store.save(state)
                break

            try:
                result: StageResult = await handler.execute(state)
            except Exception as e:
                result = StageResult(success=False, error=str(e))

            if result.success:
                if result.artifact:
                    state.add_artifact(result.artifact)
                state.previous_stage = state.stage
                state.attempt_count = 0

                if state.stage == SkillDevStage.IMPROVE:
                    overall = state.context.get("eval_overall", 0.0)
                    if overall < 0.7 and state.improve_iterations < state.max_improve_iterations:
                        state.stage = SkillDevStage.EVALUATE
                    else:
                        state.stage = next_stage(state.stage) or SkillDevStage.DONE
                else:
                    nxt = next_stage(state.stage)
                    state.stage = nxt or SkillDevStage.DONE

                if result.should_suspend:
                    state.suspended = True
                    state.suspend_reason = result.suspend_reason
                    state.suspend_at_stage = state.stage
                    state.suspend_timestamp = datetime.now().isoformat()

                self.store.save(state)
            else:
                state.attempt_count += 1
                if state.attempt_count >= state.max_attempts:
                    state.stage = SkillDevStage.FAILED
                    state.error_message = result.error or "Max attempts exceeded"
                    self.store.save(state)
                    break
                self.store.save(state)

        return state

    def get_state(self, pipeline_id: str) -> SkillDevState | None:
        """获取流水线状态"""
        return self.store.load(pipeline_id)

    def list_pipelines(self) -> list[dict[str, Any]]:
        """列出所有流水线"""
        return self.store.list_pipelines()

    def list_suspended(self) -> list[dict[str, Any]]:
        """列出挂起的流水线"""
        return self.store.list_suspended()

    def delete(self, pipeline_id: str) -> bool:
        """删除流水线checkpoint"""
        return self.store.delete(pipeline_id)