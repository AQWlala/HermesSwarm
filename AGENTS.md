# HermesSwarm - 开发规范

融合 Hermes + JiuwenSwarm 的CLI智能体，以JiuwenSwarm客户端为设计蓝本。

## 项目定位

HermesSwarm 是一个**CLI终端智能体**（类似claude-code/codex），融合：
- **Hermes基因**: SKILL.md技能系统 + FTS5三表记忆 + Curator自进化 + 提示缓存不变性
- **JiuwenSwarm基因**: SkillDev流水线 + Symphony图演进 + Agent Warm Pool + 事件背压
- **Codex基因**: 模块<500LoC + 协议分离 + API表面最小化

## 核心不变性

### 1. 提示缓存不变性（Hermes基因）
system prompt 在会话期间必须 byte-stable。任何变更（技能加载、工具集变更）默认延迟到下一会话生效。

### 2. 模块大小约束（Codex基因）
- Python模块目标 < 500 LoC
- 文件硬上限 ~800 LoC

### 3. Curator安全性（Hermes基因）
- 只触碰 `created_by: "agent"` 的技能
- 永不删除，最大破坏性操作是 archive
- pinned 技能豁免所有自动转换

## 项目结构

```
HermesSwarm/
├── src/
│   ├── cli/            # CLI REPL入口（主入口点）
│   │   ├── main.py     # REPL主循环
│   │   ├── commands.py # 斜杠命令
│   │   └── display.py  # Rich终端输出
│   ├── core/           # 引擎、配置、事件总线、安全解析
│   ├── skills/         # SKILL.md技能系统 + SkillDev流水线
│   ├── memory/         # FTS5三表记忆搜索
│   ├── agents/         # Curator + Symphony + Evolution
│   ├── tools/          # 工具注册表 + MCP客户端
│   ├── llm/            # LLM适配器 + Oneshot + 凭证池
│   └── workflow/       # 工作流引擎（保留但CLI不依赖）
├── skills/             # 预置SKILL.md技能
├── hermesswarm-cli.spec # PyInstaller CLI打包配置
└── pyproject.toml
```

## CLI使用

```bash
# pip安装
pip install -e .
hermesswarm

# 或直接运行
python -m src.cli.main

# 打包单exe
pyinstaller hermesswarm-cli.spec --noconfirm
```

## 安全规范

### 禁止
- `eval()` / `exec()` 无白名单限制
- `subprocess.run(shell=True)`
- 硬编码路径（用 `Path.expanduser()`）

### 必须
- 条件表达式用 `src.core.safe_eval.safe_eval()`
- `subprocess` 用 `shell=False` + `shlex.split()`
- LLM调用通过 `_retry_with_backoff()` 包装
