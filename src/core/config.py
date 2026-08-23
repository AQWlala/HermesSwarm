"""统一配置系统 - 融合 Hermes 和 JiuwenSwarm 配置基因"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class GeneSource(Enum):
    """基因来源标识"""
    HERMES = "hermes"
    JIUWEN = "jiuwen"
    FUSION = "fusion"


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str = "openai"
    model_name: str = "gpt-4"
    api_base: str = ""
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class HermesGenes:
    """Hermes 基因配置"""
    self_evolution: bool = True
    closed_loop_learning: bool = True
    fts5_search: bool = True
    cross_session_memory: bool = True
    skills_auto_create: bool = True
    max_skills: int = 100


@dataclass
class JiuwenGenes:
    """JiuwenSwarm 基因配置"""
    multi_agent: bool = True
    swarmflow: bool = True
    leader_orchestration: bool = True
    hitl: bool = True
    distributed: bool = False
    team_max_size: int = 5
    collaboration_mode: str = "hybrid"


@dataclass
class FusionConfig:
    """融合配置 - HermesSwarm 核心配置"""

    # 基因开关
    hermes: HermesGenes = field(default_factory=HermesGenes)
    jiwen: JiuwenGenes = field(default_factory=JiuwenGenes)

    # 模型配置
    model: ModelConfig = field(default_factory=ModelConfig)

    # 工作流配置
    workflow_timeout: int = 300
    max_parallel_nodes: int = 10

    # 记忆配置
    memory_db_path: str = "~/.hermesswarm/memory.db"

    # 安全配置
    tool_approval_required: bool = True
    file_whitelist: list[str] = field(default_factory=list)

    # 桌面应用配置
    api_port: int = 8765
    websocket_port: int = 8766

    @classmethod
    def from_yaml(cls, path: str | Path) -> FusionConfig:
        """从 YAML 文件加载配置"""
        path = Path(path).expanduser()
        if not path.exists():
            config = cls()
            config.save_yaml(path)
            return config

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config = cls()
        if "hermes" in data:
            config.hermes = HermesGenes(**data["hermes"])
        if "jiuwen" in data:
            config.jiwen = JiuwenGenes(**data["jiuwen"])
        if "model" in data:
            config.model = ModelConfig(**data["model"])
        for key in ("workflow_timeout", "max_parallel_nodes", "memory_db_path",
                     "tool_approval_required", "api_port", "websocket_port"):
            if key in data:
                setattr(config, key, data[key])
        return config

    def save_yaml(self, path: str | Path) -> None:
        """保存配置到 YAML 文件"""
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "hermes": self.hermes.__dict__,
            "jiuwen": self.jiwen.__dict__,
            "model": self.model.__dict__,
            "workflow_timeout": self.workflow_timeout,
            "max_parallel_nodes": self.max_parallel_nodes,
            "memory_db_path": self.memory_db_path,
            "tool_approval_required": self.tool_approval_required,
            "api_port": self.api_port,
            "websocket_port": self.websocket_port,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def get_default_config_path(self) -> Path:
        """获取默认配置文件路径"""
        return Path("~/.hermesswarm/config.yaml").expanduser()
