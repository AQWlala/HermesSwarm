"""Curator自进化引擎 - Hermes基因的核心实现

提取自: hermes-agent/agent/curator.py
核心心智模型:
- 状态机: active → stale(30天) → archived(90天)
- 只触碰 created_by: "agent" 的技能（用户/内置技能不动）
- 永不删除，最大破坏性操作是archive
- pinned技能豁免所有自动转换
- LLM伞形技能构建: run_curator_review()

Learning Graph（Hermes基因: learning_graph.py）:
- SkillNode节点 + related_skills边 + memory-skill词法边
- 记忆分块: MEMORY.md按 \\n§\\n 分割
"""

from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.skills.registry import Skill, SkillRegistry, SkillState


class CuratorAction(str, Enum):
    KEEP = "keep"
    PATCH = "patch"
    ARCHIVE = "archive"
    RESTORE = "restore"


@dataclass
class SkillNode:
    """技能节点（Learning Graph）"""
    skill_id: str
    use_count: int = 0
    success_rate: float = 0.0
    related: list[str] = field(default_factory=list)
    memory_links: list[str] = field(default_factory=list)


@dataclass
class CuratorReview:
    """Curator审查结果"""
    skill_id: str
    action: CuratorAction
    reason: str
    suggested_patch: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LearningGraph:
    """学习图谱（Hermes基因: learning_graph.py）

    节点: 技能
    边: related_skills + memory-skill词法边
    """

    def __init__(self) -> None:
        self.nodes: dict[str, SkillNode] = {}

    def add_skill(self, skill: Skill) -> None:
        node = SkillNode(
            skill_id=skill.id,
            use_count=skill.usage.use_count,
            related=skill.metadata.related_skills[:],
        )
        self.nodes[skill.id] = node

    def link_memory(self, skill_id: str, memory_id: str) -> None:
        """建立记忆-技能词法边"""
        node = self.nodes.get(skill_id)
        if node and memory_id not in node.memory_links:
            node.memory_links.append(memory_id)

    def derive_lexical_edges(self, memories: dict[str, str]) -> int:
        """从记忆内容派生memory-skill词法边（Hermes基因）

        通过词汇重叠检测哪些记忆与哪些技能相关:
        - 提取技能description/tags的关键词
        - 提取记忆内容的关键词
        - 词汇重叠>阈值时建立边

        Args:
            memories: {memory_id: content}

        Returns:
            新建的边数
        """
        import re
        new_edges = 0
        for skill_id, node in self.nodes.items():
            skill = None
            for s in [self.nodes.get(sid) for sid in [skill_id]]:
                if s:
                    skill = s
                    break
            if not node.related and not node.memory_links:
                pass

            skill_keywords = set()
            if hasattr(self, '_skill_texts'):
                skill_keywords = self._skill_texts.get(skill_id, set())

            for mem_id, content in memories.items():
                if mem_id in node.memory_links:
                    continue
                content_words = set(re.findall(r'\w{3,}', content.lower()))
                if skill_keywords and content_words:
                    overlap = len(skill_keywords & content_words)
                    if overlap >= 2:
                        self.link_memory(skill_id, mem_id)
                        new_edges += 1
        return new_edges

    def set_skill_texts(self, skill_texts: dict[str, set[str]]) -> None:
        """设置技能关键词（供词法边派生）"""
        self._skill_texts = skill_texts

    def get_related(self, skill_id: str, depth: int = 1) -> list[str]:
        """获取相关技能（BFS遍历）"""
        if skill_id not in self.nodes:
            return []
        visited = {skill_id}
        frontier = [skill_id]
        for _ in range(depth):
            next_frontier = []
            for sid in frontier:
                node = self.nodes.get(sid)
                if not node:
                    continue
                for rel in node.related:
                    if rel not in visited and rel in self.nodes:
                        visited.add(rel)
                        next_frontier.append(rel)
            frontier = next_frontier
        return list(visited - {skill_id})

    def get_stats(self) -> dict[str, Any]:
        total_links = sum(len(n.related) for n in self.nodes.values())
        total_mem_links = sum(len(n.memory_links) for n in self.nodes.values())
        return {
            "nodes": len(self.nodes),
            "skill_edges": total_links,
            "memory_edges": total_mem_links,
        }


class Curator:
    """Curator后台技能维护引擎（Hermes基因: agent/curator.py）

    职责:
    1. apply_automatic_transitions() - 确定性状态转换（无LLM）
    2. run_curator_review() - LLM伞形技能构建
    3. backup() - pre-run tar.gz快照
    4. restore() - 从快照恢复

    不变性:
    - 只触碰 created_by: "agent" 的技能
    - 永不删除
    - pinned技能豁免
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        archive_dir: str = "~/.hermesswarm/skills/.archive",
        backup_dir: str = "~/.hermesswarm/skills/.backup",
    ) -> None:
        self.registry = skill_registry
        self.archive_dir = Path(archive_dir).expanduser()
        self.backup_dir = Path(backup_dir).expanduser()
        self.learning_graph = LearningGraph()
        self.reviews: list[CuratorReview] = []

    def rebuild_learning_graph(self) -> None:
        """重建学习图谱"""
        self.learning_graph = LearningGraph()
        for skill in self.registry.skills.values():
            self.learning_graph.add_skill(skill)

    def apply_automatic_transitions(
        self,
        stale_after_days: int = 30,
        archive_after_days: int = 90,
    ) -> dict[str, int]:
        """确定性状态转换（无LLM，Hermes基因）"""
        return self.registry.apply_automatic_transitions(
            stale_after_days=stale_after_days,
            archive_after_days=archive_after_days,
        )

    async def run_curator_review(
        self,
        llm_adapter: Any = None,
        max_skills: int = 10,
    ) -> list[CuratorReview]:
        """LLM伞形技能审查（Hermes基因: run_curator_review）

        对每个agent创建的技能:
        1. 收集使用遥测 + 进化历史
        2. 构建审查prompt
        3. LLM决定: keep/patch/archive
        4. 应用action
        """
        reviews: list[CuratorReview] = []
        candidates = [
            s for s in self.registry.skills.values()
            if s.usage.created_by == "agent"
            and not s.usage.pinned
            and s.usage.state != SkillState.ARCHIVED
        ][:max_skills]

        for skill in candidates:
            review = await self._review_skill(skill, llm_adapter)
            reviews.append(review)
            await self._apply_review(review)

        self.reviews.extend(reviews)
        return reviews

    async def _review_skill(self, skill: Skill, llm_adapter: Any) -> CuratorReview:
        """审查单个技能"""
        usage_summary = (
            f"use_count={skill.usage.use_count}, "
            f"patch_count={skill.usage.patch_count}, "
            f"state={skill.usage.state.value}"
        )

        if skill.usage.use_count == 0 and skill.usage.state == SkillState.STALE:
            return CuratorReview(
                skill_id=skill.id,
                action=CuratorAction.ARCHIVE,
                reason=f"零使用且已stale: {usage_summary}",
            )

        if skill.usage.use_count > 5 and not skill.evolution_history:
            return CuratorReview(
                skill_id=skill.id,
                action=CuratorAction.KEEP,
                reason=f"高频使用且无进化历史: {usage_summary}",
            )

        if llm_adapter and skill.evolution_history:
            try:
                prompt = self._build_review_prompt(skill)
                response = await llm_adapter.chat(prompt)
                action = self._parse_llm_action(response, skill.id)
                return action
            except Exception:
                pass

        return CuratorReview(
            skill_id=skill.id,
            action=CuratorAction.KEEP,
            reason=f"默认保留: {usage_summary}",
        )

    def _build_review_prompt(self, skill: Skill) -> str:
        """构建审查prompt（Hermes基因: 伞形技能）"""
        return (
            f"Review skill '{skill.id}':\n"
            f"Description: {skill.description}\n"
            f"Usage: use={skill.usage.use_count}, patch={skill.usage.patch_count}\n"
            f"State: {skill.usage.state.value}\n"
            f"Evolution history: {len(skill.evolution_history)} entries\n\n"
            f"Decide: keep, patch, or archive. Respond with JSON: "
            f'{{"action": "keep|patch|archive", "reason": "..."}}'
        )

    def _parse_llm_action(self, response: str, skill_id: str) -> CuratorReview:
        """解析LLM响应"""
        try:
            import re
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                data = json.loads(json_match.group())
                action_str = data.get("action", "keep").lower()
                try:
                    action = CuratorAction(action_str)
                except ValueError:
                    action = CuratorAction.KEEP
                return CuratorReview(
                    skill_id=skill_id,
                    action=action,
                    reason=data.get("reason", ""),
                )
        except Exception:
            pass
        return CuratorReview(skill_id=skill_id, action=CuratorAction.KEEP, reason="LLM解析失败")

    async def _apply_review(self, review: CuratorReview) -> None:
        """应用审查结果"""
        skill = self.registry.skills.get(review.skill_id)
        if not skill:
            return

        if review.action == CuratorAction.ARCHIVE:
            self.archive_skill(review.skill_id)
        elif review.action == CuratorAction.PATCH and review.suggested_patch:
            skill.body = review.suggested_patch
            self.registry.record_usage(review.skill_id, "patch")

    def archive_skill(self, skill_id: str) -> bool:
        """归档技能（移动到.archive目录，不删除）"""
        skill = self.registry.skills.get(skill_id)
        if not skill or skill.usage.pinned:
            return False

        self.archive_dir.mkdir(parents=True, exist_ok=True)
        if skill.file_path:
            src = Path(skill.file_path).parent
            dst = self.archive_dir / src.name
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))

        skill.usage.state = SkillState.ARCHIVED
        self.registry._save_usage()
        return True

    def restore_skill(self, skill_id: str) -> bool:
        """从归档恢复技能"""
        skill = self.registry.skills.get(skill_id)
        if not skill or skill.usage.state != SkillState.ARCHIVED:
            return False

        archived_path = self.archive_dir / skill_id
        if archived_path.exists():
            skills_root = Path(skill.file_path).parent.parent if skill.file_path else None
            if skills_root:
                dst = skills_root / skill_id
                if not dst.exists():
                    shutil.move(str(archived_path), str(dst))

        skill.usage.state = SkillState.ACTIVE
        self.registry._save_usage()
        return True

    def backup(self, label: str = "pre-run") -> Path | None:
        """创建tar.gz快照（Hermes基因: curator_backup.py）"""
        if not self.registry.skills:
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"curator_{label}_{timestamp}.tar.gz"

        skills_root = Path("~/.hermesswarm/skills").expanduser()
        if not skills_root.exists():
            return None

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(str(skills_root), arcname="skills", exclude=self._backup_exclude)
        return backup_path

    def _backup_exclude(self, path: str) -> bool:
        """排除备份中的临时文件"""
        parts = Path(path).parts
        return any(p in {".backup", "__pycache__"} for p in parts)

    def get_status(self) -> dict[str, Any]:
        """获取Curator状态"""
        return {
            "skill_stats": self.registry.get_stats(),
            "learning_graph": self.learning_graph.get_stats(),
            "total_reviews": len(self.reviews),
            "recent_reviews": [
                {
                    "skill_id": r.skill_id,
                    "action": r.action.value,
                    "reason": r.reason[:100],
                    "timestamp": r.timestamp,
                }
                for r in self.reviews[-5:]
            ],
        }