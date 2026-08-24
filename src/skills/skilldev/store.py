"""SkillDev checkpoint存储 - 确定性恢复保证

JiuwenSwarm基因: 每个阶段完成后持久化状态，支持从任意挂起点恢复
使用JSON文件存储（原子写入：先写临时文件再rename）
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.skills.skilldev.schema import SkillDevState


class SkillDevStore:
    """SkillDev状态存储 - checkpoint持久化

    存储路径: ~/.hermesswarm/skilldev/checkpoints/{pipeline_id}.json
    原子写入: 先写 .tmp 再 rename，避免中途崩溃导致损坏
    """

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".hermesswarm" / "skilldev" / "checkpoints"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, pipeline_id: str) -> Path:
        """获取pipeline的checkpoint路径"""
        safe_id = pipeline_id.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_id}.json"

    def save(self, state: SkillDevState) -> None:
        """保存状态（原子写入）"""
        state.touch()
        target = self._path_for(state.pipeline_id)
        tmp = target.with_suffix(".json.tmp")
        data = state.to_dict()
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(str(tmp), str(target))

    def load(self, pipeline_id: str) -> SkillDevState | None:
        """加载状态"""
        path = self._path_for(pipeline_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SkillDevState.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def delete(self, pipeline_id: str) -> bool:
        """删除checkpoint"""
        path = self._path_for(pipeline_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_pipelines(self) -> list[dict[str, Any]]:
        """列出所有pipeline的摘要"""
        result = []
        for path in self.base_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "pipeline_id": data.get("pipeline_id", ""),
                    "skill_name": data.get("skill_name", ""),
                    "stage": data.get("stage", ""),
                    "suspended": data.get("suspended", False),
                    "updated_at": data.get("updated_at", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return result

    def list_suspended(self) -> list[dict[str, Any]]:
        """列出所有挂起的pipeline"""
        return [p for p in self.list_pipelines() if p.get("suspended")]