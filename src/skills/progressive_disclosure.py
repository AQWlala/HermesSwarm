"""渐进式技能披露 - JiuwenSwarm基因

递归搜索引擎逐层披露技能树:
- 每次最多暴露N层深度
- LLM选择边界节点后下钻
- compact codes减少token
- prefix cache优化

基因来源: JiuwenSwarm symphony/retrieval/tree/progressive.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.skills.registry import Skill, SkillRegistry


@dataclass
class DisclosureConfig:
    """披露配置"""
    max_exposure_depth: int = 2
    max_items_per_layer: int = 12
    max_tokens: int = 4000


@dataclass
class ExposedFragment:
    """暴露的技能片段"""
    rendered_tree: str
    boundary_codes: dict[str, str] = field(default_factory=dict)
    depth: int = 0


class ProgressiveDisclosure:
    """渐进式技能披露引擎

    不一次性返回所有匹配技能，而是逐层暴露技能树。
    LLM可以选择边界节点下钻获取更详细的信息。
    """

    def __init__(self, registry: SkillRegistry, config: DisclosureConfig | None = None):
        self.registry = registry
        self.config = config or DisclosureConfig()
        self._code_counter: dict[str, int] = {}

    def _assign_compact_code(self, skill_id: str) -> str:
        """分配紧凑代码（减少token）"""
        if skill_id not in self._code_counter:
            self._code_counter[skill_id] = len(self._code_counter) + 1
        return str(self._code_counter[skill_id])

    def disclose(
        self,
        query: str,
        current_depth: int = 0,
        agent_name: str = "*",
    ) -> ExposedFragment:
        """披露技能树

        Args:
            query: 用户查询
            current_depth: 当前披露深度
            agent_name: 请求agent名称（可见性过滤）

        Returns:
            ExposedFragment包含渲染的技能树和边界代码
        """
        all_skills = self.registry.discover_skills_for_task(
            query, limit=self.config.max_items_per_layer * 2, agent_name=agent_name
        )

        visible = all_skills[:self.config.max_items_per_layer]
        boundary = all_skills[self.config.max_items_per_layer:]

        boundary_codes: dict[str, str] = {}
        for skill in boundary:
            code = self._assign_compact_code(skill.id)
            boundary_codes[code] = skill.id

        rendered = self._render_tree(visible, current_depth, bool(boundary))

        return ExposedFragment(
            rendered_tree=rendered,
            boundary_codes=boundary_codes,
            depth=current_depth + 1,
        )

    def _render_tree(
        self,
        skills: list[Skill],
        depth: int,
        has_more: bool,
    ) -> str:
        """渲染技能树"""
        lines = [f"# Skills (depth={depth}, count={len(skills)})"]
        for skill in skills:
            code = self._assign_compact_code(skill.id)
            lines.append(f"[{code}] {skill.name}: {skill.description[:80]}")
            if skill.metadata.tags:
                lines.append(f"    tags: {', '.join(skill.metadata.tags[:5])}")

        if has_more:
            lines.append("\n(more skills available, use drill_down(code) to explore)")
        return "\n".join(lines)

    def drill_down(
        self,
        boundary_code: str,
        boundary_codes: dict[str, str],
    ) -> Skill | None:
        """下钻到指定边界技能"""
        skill_id = boundary_codes.get(boundary_code)
        if not skill_id:
            return None
        return self.registry.skills.get(skill_id)

    def build_prompt_parts(
        self,
        query: str,
        agent_name: str = "*",
    ) -> tuple[list[dict[str, str]], str]:
        """构建披露prompt部分

        拆分为prefix_messages(可缓存)和suffix_text(查询特定):
        - prefix: 技能树渲染（相同候选树可复用KV cache）
        - suffix: 用户查询（每次不同）

        Returns:
            (prefix_messages, suffix_text)
        """
        fragment = self.disclose(query, agent_name=agent_name)
        prefix_messages = [
            {"role": "system", "content": "Skills are disclosed progressively. Use drill_down(code) to explore."},
            {"role": "user", "content": fragment.rendered_tree},
        ]
        suffix_text = f"Query: {query}"
        return prefix_messages, suffix_text