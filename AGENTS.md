# HermesSwarm - 开发规范

融合 Hermes + JiuwenSwarm + Codex 三大AI智能体项目的基因级融合产品。

## 项目定位

HermesSwarm 是一个可视化智能体编排桌面应用，融合：
- **Hermes基因**: SKILL.md技能系统 + FTS5三表记忆 + Curator自进化 + 提示缓存不变性
- **JiuwenSwarm基因**: TeamManager多智能体协作 + SwarmBuildContext + 事件背压 + Skill自演进
- **Codex基因**: 模块<500LoC + 协议分离 + API表面最小化

## 核心不变性

### 1. 提示缓存不变性（Hermes基因）
system prompt 在会话期间必须 byte-stable。任何变更（技能加载、工具集变更）默认延迟到下一会话生效，不破坏当前会话的缓存。

### 2. 模块大小约束（Codex基因）
- Python模块目标 < 500 LoC（不含测试）
- 文件硬上限 ~800 LoC，必须拆分新模块
- 变更大小（机械）≤ 800行；（复杂逻辑）≤ 500行

### 3. 事件背压（JiuwenSwarm基因）
事件队列上限 64，满队列时短时超时重检（0.1s），检测孤儿队列避免永久阻塞。

### 4. Curator安全性（Hermes基因）
- 只触碰 `created_by: "agent"` 的技能
- 永不删除，最大破坏性操作是 archive
- pinned 技能豁免所有自动转换

## 项目结构

```
HermesSwarm/
├── src/
│   ├── core/           # 核心引擎、配置、事件总线、安全解析
│   ├── skills/         # SKILL.md技能系统（Hermes基因）
│   ├── memory/         # FTS5三表记忆搜索（Hermes基因）
│   ├── agents/         # 智能体系统
│   │   ├── curator.py  # Curator自进化引擎（Hermes基因）
│   │   ├── evolution.py # 进化引擎
│   │   ├── swarm/      # TeamManager + SwarmBuildContext（JiuwenSwarm基因）
│   │   ├── leader.py   # Leader智能体
│   │   └── specialist.py # Specialist智能体
│   ├── workflow/       # 工作流引擎（拓扑排序+并行+HITL+条件路由）
│   ├── tools/          # 工具注册表（AST自动发现+权限分层）
│   ├── llm/            # LLM适配器（重试+降级+连接池）
│   └── ui/             # React+TypeScript前端
├── skills/             # 预置SKILL.md技能
├── desktop_main.py     # 单exe入口点
├── hermesswarm-desktop.spec # PyInstaller打包配置
└── pyproject.toml
```

## 安全规范

### 禁止
- `eval()` / `exec()` 无白名单限制
- `subprocess.run(shell=True)`
- 硬编码 `~/.hermesswarm` 路径（用 `Path.expanduser()`）
- 在测试中读取源码文件文本

### 必须
- 条件表达式用 `src.core.safe_eval.safe_eval()`（AST解析，无逃逸）
- `exec()` 限制 `__builtins__` 白名单
- `subprocess` 用 `shell=False` + `shlex.split()`
- LLM调用通过 `_retry_with_backoff()` 包装

## 基因来源标注

每个模块的docstring必须标注基因来源：
```python
"""模块描述

Hermes基因: xxx
JiuwenSwarm基因: xxx
"""
```

## 测试

```bash
# Python测试
python -m pytest tests/ -v

# 前端类型检查
cd src/ui && npx tsc --noEmit

# 前端构建
cd src/ui && npx vite build

# 打包单exe
pyinstaller hermesswarm-desktop.spec --noconfirm
```

## 打包

单个 `HermesSwarm.exe`（~37MB），不分前后端：
- FastAPI serve 前端静态文件
- PyInstaller 打包前端 dist + skills 目录进 exe
- 双击启动，自动打开浏览器