# ☤ HermesSwarm

> Hermes + JiuwenSwarm 融合CLI智能体，以JiuwenSwarm客户端为设计蓝本

## 概述

HermesSwarm 是一个**CLI终端智能体**（类似claude-code/codex），融合两大开源AI智能体项目的核心基因：

- **Hermes基因** (Nous Research): SKILL.md技能系统 + FTS5三表记忆 + Curator自进化 + 提示缓存不变性
- **JiuwenSwarm基因**: SkillDev确定性流水线 + Symphony图演进 + Agent Warm Pool + 事件背压
- **Codex基因** (OpenAI): 模块<500LoC + 协议分离 + API表面最小化

## 安装

```bash
# 开发安装
pip install -e .

# 运行
export DEEPSEEK_API_KEY="your-key"
hermesswarm
```

## 使用

直接输入文本与agent对话，或使用斜杠命令：

```
>>> 帮我读取 src/cli/main.py 并解释
>>> /skills              # 列出已加载技能
>>> /memory 搜索词       # 搜索记忆
>>> /curator             # 运行Curator自进化
>>> /skilldev my-skill   # 启动SkillDev流水线
>>> /help                # 查看所有命令
```

## 内置工具

| 工具 | 说明 | 权限 |
|------|------|------|
| read_file | 读取文件 | LOW |
| write_file | 写入文件 | MEDIUM |
| edit_file | 精确字符串替换 | MEDIUM |
| grep | 正则搜索文件内容 | LOW |
| glob | glob模式查找文件 | LOW |
| list_dir | 列出目录内容 | LOW |
| terminal | 执行shell命令 | HIGH |
| pytest_run | 运行pytest测试 | MEDIUM |

## 打包

```bash
pyinstaller hermesswarm-cli.spec --noconfirm
# 生成 dist/HermesSwarm.exe
```

## 项目结构

```
HermesSwarm/
├── src/
│   ├── cli/            # CLI REPL入口
│   ├── core/           # 引擎、配置、事件总线
│   ├── skills/         # SKILL.md + SkillDev流水线
│   ├── memory/         # FTS5三表记忆
│   ├── agents/         # Curator + Symphony + Evolution
│   ├── tools/          # 工具注册表 + MCP客户端
│   └── llm/            # LLM适配器 + Oneshot + 凭证池
├── skills/             # 预置SKILL.md技能
└── hermesswarm-cli.spec
```

## 协议

Apache-2.0
