"""技能注册中心 - 融合 Hermes SKILL.md格式 + JiuwenSwarm 单库+可见性

Hermes基因: YAML frontmatter + Markdown body, agentskills.io兼容
JiuwenSwarm基因: 单库 + skills-visibility.json可见性元数据
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


_EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".hermesswarm", ".archive"}

_SKILL_INVOCATION_MARKER = '[IMPORTANT: The user has invoked the "'
_SKILL_INVOCATION_SUFFIX = '" skill.]'


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
    """技能使用遥测（Hermes基因: tools/skill_usage.py）

    持久化到 ~/.hermesswarm/skills/.usage.json sidecar
    """
    use_count: int = 0
    view_count: int = 0
    patch_count: int = 0
    last_activity_at: str = ""
    state: SkillState = SkillState.ACTIVE
    pinned: bool = False
    created_by: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return {
            "use_count": self.use_count,
            "view_count": self.view_count,
            "patch_count": self.patch_count,
            "last_activity_at": self.last_activity_at,
            "state": self.state.value,
            "pinned": self.pinned,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillUsage:
        state_val = data.get("state", "active")
        try:
            state = SkillState(state_val)
        except ValueError:
            state = SkillState.ACTIVE
        return cls(
            use_count=data.get("use_count", 0),
            view_count=data.get("view_count", 0),
            patch_count=data.get("patch_count", 0),
            last_activity_at=data.get("last_activity_at", ""),
            state=state,
            pinned=data.get("pinned", False),
            created_by=data.get("created_by", "user"),
        )


@dataclass
class Skill:
    """技能定义（融合技能）

    Hermes基因: SKILL.md格式, 使用遥测, 自进化
    JiuwenSwarm基因: 来源标记, 可见性, 进化历史
    """
    id: str
    metadata: SkillMetadata
    body: str = ""
    origin: SkillOrigin = SkillOrigin.FUSION
    usage: SkillUsage = field(default_factory=SkillUsage)
    evolution_history: list[dict[str, Any]] = field(default_factory=list)
    file_path: str = ""
    visible_to: list[str] = field(default_factory=lambda: ["*"])

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

    def is_visible_to(self, agent_name: str) -> bool:
        if "*" in self.visible_to:
            return True
        return agent_name in self.visible_to

    def build_invocation_message(self, user_input: str) -> str:
        """构建技能调用消息（Hermes基因: 注入用户消息而非system prompt）

        格式: [IMPORTANT: The user has invoked the "<skill_name>" skill.]
        <skill_body>

        <user_input>
        """
        marker = f"{_SKILL_INVOCATION_MARKER}{self.name}{_SKILL_INVOCATION_SUFFIX}"
        return f"{marker}\n\n{self.body}\n\n{user_input}"


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
        self.visibility_file: Path = Path("~/.hermesswarm/skills/.visibility.json").expanduser()
        self._usage_loaded = False

    def discover(self, skills_dir: str | Path) -> int:
        """发现技能（Hermes基因: 扫描SKILL.md，排除.git/.venv/node_modules等）"""
        skills_dir = Path(skills_dir).expanduser()
        if not skills_dir.exists():
            return 0

        self._load_usage()
        count = 0
        for skill_path in self._rglob_skill_md(skills_dir):
            skill = self._parse_skill_file(skill_path)
            if skill:
                self.register(skill)
                count += 1
        self._merge_usage_into_skills()
        return count

    def _rglob_skill_md(self, root: Path):
        """递归扫描SKILL.md，排除常见非技能目录（Hermes基因）"""
        for path in root.rglob("SKILL.md"):
            if any(part in _EXCLUDED_DIRS for part in path.parts):
                continue
            yield path

    def _parse_skill_file(self, path: Path) -> Skill | None:
        """解析SKILL.md文件（Hermes基因: YAML frontmatter + Markdown body）"""
        try:
            content = path.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
            if not match:
                return None

            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = match.group(2).strip()

            meta_hermes = frontmatter.get("metadata", {}).get("hermes", {})
            metadata = SkillMetadata(
                name=frontmatter.get("name", path.parent.name),
                description=frontmatter.get("description", ""),
                version=frontmatter.get("version", "1.0.0"),
                author=frontmatter.get("author", ""),
                license=frontmatter.get("license", ""),
                platforms=frontmatter.get("platforms", []),
                tags=frontmatter.get("tags", meta_hermes.get("tags", [])),
                category=frontmatter.get("category", meta_hermes.get("category", "general")),
                related_skills=meta_hermes.get("related_skills", []),
            )

            skill_id = metadata.name
            existing = self.skills.get(skill_id)
            usage = existing.usage if existing else SkillUsage()

            return Skill(
                id=skill_id,
                metadata=metadata,
                body=body,
                file_path=str(path),
                usage=usage,
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

    def discover_skills_for_task(self, task: str, limit: int = 10, agent_name: str = "*") -> list[Skill]:
        """发现相关技能（融合匹配 + 可见性过滤）"""
        keywords = task.lower().split()
        scored: list[tuple[float, Skill]] = []

        for skill in self.skills.values():
            if skill.usage.state == SkillState.ARCHIVED:
                continue
            if not skill.is_visible_to(agent_name):
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
        name = skill.name.lower()
        score = 0.0
        for kw in keywords:
            if kw in name:
                score += 1.2
            if kw in desc:
                score += 1.0
            if kw in tags:
                score += 0.8
            if kw in cat:
                score += 0.5
        return score

    def record_usage(self, skill_id: str, action: str = "use") -> None:
        """记录使用（Hermes基因: skill_usage.py sidecar）"""
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
        self._save_usage()

    def _load_usage(self) -> None:
        """加载遥测sidecar（Hermes基因: ~/.hermesswarm/skills/.usage.json）"""
        if self._usage_loaded:
            return
        self._usage_loaded = True
        if not self.usage_file.exists():
            return
        try:
            data = json.loads(self.usage_file.read_text(encoding="utf-8"))
            self._cached_usage = {k: SkillUsage.from_dict(v) for k, v in data.items()}
        except Exception:
            self._cached_usage = {}

    def _merge_usage_into_skills(self) -> None:
        """将缓存的遥测合并到已注册技能"""
        cached = getattr(self, "_cached_usage", {})
        for skill_id, usage in cached.items():
            skill = self.skills.get(skill_id)
            if skill:
                skill.usage = usage

    def _save_usage(self) -> None:
        """持久化遥测到sidecar"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        data = {sid: s.usage.to_dict() for sid, s in self.skills.items()}
        self.usage_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_visibility(self) -> None:
        """加载技能可见性（JiuwenSwarm基因: skills-visibility.json）"""
        if not self.visibility_file.exists():
            return
        try:
            data = json.loads(self.visibility_file.read_text(encoding="utf-8"))
            for skill_id, visible_to in data.items():
                skill = self.skills.get(skill_id)
                if skill and isinstance(visible_to, list):
                    skill.visible_to = visible_to
        except Exception:
            pass

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
        self.record_usage(skill_id, "patch")
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
        """自动状态转换（Hermes基因: Curator.apply_automatic_transitions）

        不变性:
        - 只触碰 created_by: "agent" 的技能（用户/内置技能不动）
        - 永不删除，最大破坏性操作是archive
        - pinned技能豁免所有自动转换
        """
        now = datetime.now()
        transitions = {"active_to_stale": 0, "stale_to_archived": 0, "skipped_pinned": 0, "skipped_user": 0}

        for skill in self.skills.values():
            if skill.usage.pinned:
                transitions["skipped_pinned"] += 1
                continue
            if skill.usage.created_by != "agent":
                transitions["skipped_user"] += 1
                continue
            if not skill.usage.last_activity_at:
                continue

            try:
                last = datetime.fromisoformat(skill.usage.last_activity_at)
            except ValueError:
                continue
            days_idle = (now - last).days

            if skill.usage.state == SkillState.ACTIVE and days_idle > stale_after_days:
                skill.usage.state = SkillState.STALE
                transitions["active_to_stale"] += 1
            elif skill.usage.state == SkillState.STALE and days_idle > archive_after_days:
                skill.usage.state = SkillState.ARCHIVED
                transitions["stale_to_archived"] += 1

        self._save_usage()
        return transitions

    def pin(self, skill_id: str) -> bool:
        """固定技能（豁免自动转换）"""
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        skill.usage.pinned = True
        self._save_usage()
        return True

    def unpin(self, skill_id: str) -> bool:
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        skill.usage.pinned = False
        self._save_usage()
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取统计"""
        return {
            "total": len(self.skills),
            "active": sum(1 for s in self.skills.values() if s.usage.state == SkillState.ACTIVE),
            "stale": sum(1 for s in self.skills.values() if s.usage.state == SkillState.STALE),
            "archived": sum(1 for s in self.skills.values() if s.usage.state == SkillState.ARCHIVED),
            "pinned": sum(1 for s in self.skills.values() if s.usage.pinned),
            "categories": len(self.categories),
            "by_category": {k: len(v) for k, v in self.categories.items()},
        }

    def build_system_prompt_section(self, agent_name: str = "*") -> str:
        """构建技能列表的system prompt段（注入到system prompt）"""
        visible = [s for s in self.skills.values()
                    if s.usage.state != SkillState.ARCHIVED and s.is_visible_to(agent_name)]
        if not visible:
            return ""
        lines = ["## Available Skills"]
        for skill in sorted(visible, key=lambda s: s.name):
            lines.append(f"- **{skill.name}**: {skill.description}")
        return "\n".join(lines)
