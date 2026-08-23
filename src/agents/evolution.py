"""自进化引擎 - 融合 Hermes Curator + JiuwenSwarm Skill自演进

Hermes基因: Curator后台技能维护, Learning Graph, 闭环学习
JiuwenSwarm基因: 信号检测, evolutions.json, Symphony动态图谱
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.events import EventBus, EventType


@dataclass
class EvolutionRecord:
    """进化记录"""
    timestamp: str
    trigger: str  # failure/success/feedback/signal
    feedback: str
    changes: list[dict[str, Any]]
    skill_id: str | None = None


class EvolutionEngine:
    """融合自进化引擎

    双重进化环:
    1. Hermes闭环: 反馈→分析→改进→应用→记录
    2. JiuwenSwarm信号: 执行异常→信号检测→evolutions.json
    """

    def __init__(
        self,
        config: Any,
        skill_registry: Any,
        memory: Any,
        event_bus: EventBus,
    ):
        self.config = config
        self.skill_registry = skill_registry
        self.memory = memory
        self.event_bus = event_bus
        self.history: list[EvolutionRecord] = []

    async def learn_from_execution(self, workflow: Any, result: dict[str, Any]) -> None:
        """从工作流执行中学习"""
        # 检测执行信号（JiuwenSwarm基因）
        signals = self._detect_signals(result)

        for signal in signals:
            await self._process_signal(signal)

        # Hermes基因: Curator自动状态转换
        if self.config.hermes.self_evolution:
            transitions = self.skill_registry.apply_automatic_transitions()
            if transitions["active_to_stale"] > 0 or transitions["stale_to_archived"] > 0:
                await self.event_bus.publish_simple(
                    EventType.EVOLUTION_COMPLETED,
                    {"transitions": transitions},
                    source="evolution_engine",
                )

    def _detect_signals(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        """检测进化信号（JiuwenSwarm基因: 信号检测）"""
        signals = []
        outputs = result.get("outputs", {})

        for node_id, output in outputs.items():
            if isinstance(output, dict) and output.get("error"):
                signals.append({
                    "type": "failure",
                    "node_id": node_id,
                    "error": output["error"],
                    "feedback": f"节点{node_id}执行失败: {output['error']}",
                })

        return signals

    async def _process_signal(self, signal: dict[str, Any]) -> None:
        """处理进化信号"""
        if signal["type"] == "failure":
            # 记录进化
            record = EvolutionRecord(
                timestamp=datetime.now().isoformat(),
                trigger="failure",
                feedback=signal["feedback"],
                changes=[{"action": "recorded", "signal": signal}],
            )
            self.history.append(record)

            # 进化相关技能
            if self.skill_registry:
                skills = self.skill_registry.discover_skills_for_task(signal["feedback"], limit=1)
                for skill in skills:
                    await self.skill_registry.evolve_skill(skill.id, signal["feedback"])

        await self.event_bus.publish_simple(
            EventType.EVOLUTION_TRIGGERED,
            {"signal": signal["type"], "feedback": signal["feedback"][:200]},
            source="evolution_engine",
        )

    def get_report(self) -> dict[str, Any]:
        """获取进化报告"""
        return {
            "total_evolutions": len(self.history),
            "recent": [
                {"timestamp": r.timestamp, "trigger": r.trigger, "changes": len(r.changes)}
                for r in self.history[-10:]
            ],
            "skill_stats": self.skill_registry.get_stats() if self.skill_registry else {},
        }
