"""技能注册中心 - 融合 Hermes SKILL.md格式 + JiuwenSwarm 单库+可见性

Hermes基因: YAML frontmatter + Markdown body, agentskills.io兼容
JiuwenSwarm基因: 单库 + skills-visibility.json可见性元数据
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class SkillOrigin(str, Enum):
    HERMES = "hermes"
    JIUWEN = "jiuwen"
    FUSION = "fusion"
    USER = "user"


class SkillState(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"
    PINNED = "pinned"


@dataclass
class SkillMetadata:
    """技能元数据（Hermes SKILL.md frontmatter格式）"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    license: str = ""
    platforms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    related_skills: list[str] = field(default_factory=list)


@dataclass
class SkillUsage:
    """技能使用遥测（Hermes基因: tools/skill_usage.py）"""
    use_count: int = 0
    view_count: int = 0
    patch_count: int = 0
    last_activity_at: str = ""
    state: SkillState = SkillState.ACTIVE
    pinned: bool = False
    created_by: str = "user"


@dataclass
class Skill:
    """技能定义（融合技能）

    Hermes基因: SKILL.md格式, 使用遥测, 自进化
    JiuwenSwarm基因: 来源标记, 可见性, 进化历史
    """
    id: str
    metadata: SkillMetadata
    body: str = ""  # Markdown body
    origin: SkillOrigin = SkillOrigin.FUSION
    usage: SkillUsage = field(default_factory=SkillUsage)
    evolution_history: list[dict[str, Any]] = field(default_factory=list)
    file_path: str = ""

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def evolution_score(self) -> float:
        base = 0.5
        bonus = len(self.evolution_history) * 0.05
        usage_bonus = min(self.usage.use_count * 0.01, 0.3)
        return min(base + bonus + usage_bonus, 1.0)


class SkillRegistry:
    """技能注册中心

    融合:
    - Hermes: SKILL.md发现, 使用遥测sidecar, Curator状态转换
    - JiuwenSwarm: 单库+可见性, Skill自演进
    """

    def __init__(self, config: Any = None):
        self.config = config
        self.skills: dict[str, Skill] = {}
        self.categories: dict[str, list[str]] = {}
        self.usage_file: Path = Path("~/.hermesswarm/skills/.usage.json").expanduser()

    def discover(self, skills_dir: str | Path) -> int:
        """发现技能（Hermes基因: 扫描SKILL.md）"""
        skills_dir = Path(skills_dir).expanduser()
        if not skills_dir.exists():
            return 0

        count = 0
        for skill_path in skills_dir.rglob("SKILL.md"):
            skill = self._parse_skill_file(skill_path)
            if skill:
                self.register(skill)
                count += 1
        return count

    def _parse_skill_file(self, path: Path) -> Skill | None:
        """解析SKILL.md文件（Hermes基因: YAML frontmatter + Markdown body）"""
        try:
            content = path.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
            if not match:
                return None

            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = match.group(2).strip()

            metadata = SkillMetadata(
                name=frontmatter.get("name", path.parent.name),
                description=frontmatter.get("description", ""),
                version=frontmatter.get("version", "1.0.0"),
                author=frontmatter.get("author", ""),
                license=frontmatter.get("license", ""),
                platforms=frontmatter.get("platforms", []),
                tags=frontmatter.get("metadata", {}).get("tags", []),
                category=frontmatter.get("metadata", {}).get("category", "general"),
                related_skills=frontmatter.get("metadata", {}).get("related_skills", []),
            )

            return Skill(
                id=metadata.name,
                metadata=metadata,
                body=body,
                file_path=str(path),
            )
        except Exception:
            return None

    def register(self, skill: Skill) -> None:
        """注册技能"""
        self.skills[skill.id] = skill
        cat = skill.metadata.category
        if cat not in self.categories:
            self.categories[cat] = []
        if skill.id not in self.categories[cat]:
            self.categories[cat].append(skill.id)

    def discover_skills_for_task(self, task: str, limit: int = 10) -> list[Skill]:
        """发现相关技能（融合匹配）"""
        keywords = task.lower().split()
        scored: list[tuple[float, Skill]] = []

        for skill in self.skills.values():
            if skill.usage.state == SkillState.ARCHIVED:
                continue
            score = self._match_score(skill, keywords)
            if score > 0:
                scored.append((score + skill.evolution_score * 0.3, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def _match_score(self, skill: Skill, keywords: list[str]) -> float:
        """匹配评分"""
        desc = skill.description.lower()
        tags = [t.lower() for t in skill.metadata.tags]
        cat = skill.metadata.category.lower()
        score = 0.0
        for kw in keywords:
            if kw in desc:
                score += 1.0
            if kw in tags:
                score += 0.8
            if kw in cat:
                score += 0.5
        return score

    def record_usage(self, skill_id: str, action: str = "use") -> None:
        """记录使用（Hermes基因: skill_usage.py）"""
        skill = self.skills.get(skill_id)
        if not skill:
            return
        if action == "use":
            skill.usage.use_count += 1
        elif action == "view":
            skill.usage.view_count += 1
        elif action == "patch":
            skill.usage.patch_count += 1
        skill.usage.last_activity_at = datetime.now().isoformat()

    async def evolve_skill(self, skill_id: str, feedback: str) -> Skill | None:
        """技能自进化（融合进化）

        Hermes基因: Curator闭环学习
        JiuwenSwarm基因: 信号检测 + evolutions.json
        """
        skill = self.skills.get(skill_id)
        if not skill:
            return None

        evolution = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "type": self._classify_feedback(feedback),
        }
        skill.evolution_history.append(evolution)
        return skill

    def _classify_feedback(self, feedback: str) -> str:
        lower = feedback.lower()
        if any(w in lower for w in ["好", "good", "great"]):
            return "positive"
        if any(w in lower for w in ["差", "错", "bad", "wrong"]):
            return "negative"
        return "neutral"

    def apply_automatic_transitions(
        self,
        stale_after_days: int = 30,
        archive_after_days: int = 90,
    ) -> dict[str, int]:
        """自动状态转换（Hermes基因: Curator.apply_automatic_transitions）"""
        now = datetime.now()
        transitions = {"active_to_stale": 0, "stale_to_archived": 0, "skipped_pinned": 0}

        for skill in self.skills.values():
            if skill.usage.pinned:
                transitions["skipped_pinned"] += 1
                continue
            if not skill.usage.last_activity_at:
                continue

            last = datetime.fromisoformat(skill.usage.last_activity_at)
            days_idle = (now - last).days

            if skill.usage.state == SkillState.ACTIVE and days_idle > stale_after_days:
                skill.usage.state = SkillState.STALE
                transitions["active_to_stale"] += 1
            elif skill.usage.state == SkillState.STALE and days_idle > archive_after_days:
                skill.usage.state = SkillState.ARCHIVED
                transitions["stale_to_archived"] += 1

        return transitions

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        return {
            "total": len(self.skills),
            "active": sum(1 for s in self.skills.values() if s.usage.state == SkillState.ACTIVE),
            "stale": sum(1 for s in self.skills.values() if s.usage.state == SkillState.STALE),
            "archived": sum(1 for s in self.skills.values() if s.usage.state == SkillState.ARCHIVED),
            "pinned": sum(1 for s in self.skills.values() if s.usage.pinned),
            "categories": len(self.categories),
        }
