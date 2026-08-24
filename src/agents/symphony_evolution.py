"""Symphony图演进 - JiuwenSwarm基因

从会话历史反推plan_outcome，动态覆盖层调整技能图权重:
- 记录plan执行结果(success/failure/needs_input)
- 失败归因(terminal_edge / all_edges)
- 动态调整边权重

基因来源: JiuwenSwarm symphony/evolution/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PlanOutcome:
    """计划执行结果"""
    plan_id: str
    outcome: str  # success / failure / needs_input
    selected_edges: list[str] = field(default_factory=list)
    failed_edges: list[str] = field(default_factory=list)
    failure_attribution: str = ""  # terminal_edge / all_edges
    missing_inputs: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class EdgeWeight:
    """边权重"""
    base_weight: float = 1.0
    runtime_weight: float = 1.0
    success_count: int = 0
    failure_count: int = 0

    @property
    def effective_weight(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return self.base_weight
        success_rate = self.success_count / total
        return self.base_weight * (0.5 + success_rate)


class SymphonyEvolution:
    """Symphony图演进引擎

    从实际使用中学习，调整技能协作图的边权重。
    """

    def __init__(self, log_dir: str = "~/.hermesswarm/symphony"):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[PlanOutcome] = []
        self._edge_weights: dict[str, EdgeWeight] = {}
        self._load_events()

    def record_plan_outcome(self, outcome: PlanOutcome) -> None:
        """记录计划执行结果"""
        self._events.append(outcome)
        self._update_weights(outcome)
        self._save_event(outcome)

    def _update_weights(self, outcome: PlanOutcome) -> None:
        """更新边权重"""
        if outcome.outcome == "success":
            for edge in outcome.selected_edges:
                w = self._edge_weights.setdefault(edge, EdgeWeight())
                w.success_count += 1
        elif outcome.outcome == "failure":
            if outcome.failure_attribution == "terminal_edge":
                for edge in outcome.failed_edges:
                    w = self._edge_weights.setdefault(edge, EdgeWeight())
                    w.failure_count += 1
            else:
                for edge in outcome.selected_edges:
                    w = self._edge_weights.setdefault(edge, EdgeWeight())
                    w.failure_count += 1

    def get_effective_weights(self) -> dict[str, float]:
        """获取有效权重"""
        return {edge: w.effective_weight for edge, w in self._edge_weights.items()}

    def get_graph_stats(self) -> dict[str, Any]:
        """获取图统计"""
        return {
            "total_events": len(self._events),
            "total_edges": len(self._edge_weights),
            "success_events": sum(1 for e in self._events if e.outcome == "success"),
            "failure_events": sum(1 for e in self._events if e.outcome == "failure"),
            "top_edges": sorted(
                [(e, w.effective_weight) for e, w in self._edge_weights.items()],
                key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _save_event(self, outcome: PlanOutcome) -> None:
        """持久化事件"""
        log_file = self.log_dir / "events.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(outcome.__dict__, ensure_ascii=False) + "\n")

    def _load_events(self) -> None:
        """加载历史事件"""
        log_file = self.log_dir / "events.jsonl"
        if not log_file.exists():
            return
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line.strip())
                    outcome = PlanOutcome(**data)
                    self._events.append(outcome)
                    self._update_weights(outcome)
        except Exception:
            pass