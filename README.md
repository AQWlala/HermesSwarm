# HermesSwarm ☤

> **基因级融合的可视化智能体编排平台** — Hermes Agent × JiuwenSwarm × 扣子式可视化画布

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://react.dev)
[![Tauri](https://img.shields.io/badge/Tauri-1.6+-orange.svg)](https://tauri.app)

## 🎯 项目定位

HermesSwarm 是一个**基因级融合**的可视化智能体编排桌面应用，将两个顶级开源AI智能体项目的核心基因融合重组：

| 基因来源 | 核心能力 | 融合贡献 |
|---------|---------|---------|
| **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** | 自进化学习、闭环技能进化、FTS5记忆、40+工具 | 自进化引擎、技能格式、记忆系统 |
| **[JiuwenSwarm](https://github.com/openJiuwen-ai/jiuwenswarm)** | 多智能体协作、SwarmFlow工作流、HITL、分布式 | 工作流引擎、Leader-Teammate、人机协同 |
| **扣子(Coze)式画布** | 可拖拽可视化编排 | React Flow画布、节点库、属性面板 |

## ✨ 核心特性

### 🧬 基因级融合
- **双重进化环**: Hermes闭环学习 + JiuwenSwarm Skill自演进
- **统一技能格式**: Hermes SKILL.md + JiuwenSwarm 单库可见性
- **融合记忆**: FTS5全文搜索 + 向量索引双索引

### 🎨 扣子式可视化画布
- **拖拽编排**: React Flow画布，6种节点类型
- **实时执行**: WebSocket推送节点状态
- **HITL审批**: 人机协同节点，支持人工审批门控

### 🤖 智能体系统
- **Leader-Teammate**: JiuwenSwarm多智能体协作架构
- **自进化**: Hermes Curator后台技能维护
- **分布式**: A2X注册中心 + pyzmq跨机器协作

### 🔧 工具与安全
- **70+工具**: Hermes 40+ + JiuwenSwarm 30+
- **权限分层**: tiered_policy 9步审批流程
- **沙箱隔离**: jiuwenbox bubblewrap沙箱

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│  L7 表现层: Tauri桌面应用 + React Flow画布              │
├─────────────────────────────────────────────────────────┤
│  L6 协议层: WebSocket + JSON-RPC                        │
├─────────────────────────────────────────────────────────┤
│  L5 工作流层: SwarmFlow + WorkflowRunState + HITL       │
├─────────────────────────────────────────────────────────┤
│  L4 智能体层: Leader + Specialist + TeamManager         │
├─────────────────────────────────────────────────────────┤
│  L3 进化层: Curator + LearningGraph + Skill自演进       │
├─────────────────────────────────────────────────────────┤
│  L2 能力层: Skills + Memory(FTS+向量) + Tools(70+)     │
├─────────────────────────────────────────────────────────┤
│  L1 基础层: Config + EventBus + SessionDB              │
└─────────────────────────────────────────────────────────┘
```

## 📦 安装与运行

### 前端开发
```bash
cd src/ui
npm install
npm run dev
```

### Python后端
```bash
pip install -e ".[dev]"
```

### 桌面应用打包
```bash
pyinstaller hermesswarm-desktop.spec --noconfirm
```

## 📁 项目结构

```
HermesSwarm/
├── src/
│   ├── core/           # 融合引擎、配置、事件总线
│   ├── agents/         # 智能体系统（Leader/Specialist/Evolution/Swarm）
│   ├── skills/         # 技能注册中心 + SkillDev流水线
│   ├── memory/         # 统一记忆（FTS5+向量）
│   ├── tools/          # 工具注册表 + MCP客户端
│   ├── workflow/       # 工作流引擎（SwarmFlow+状态机）
│   └── ui/             # React可视化画布前端
├── skills/             # 预置SKILL.md技能
├── desktop_main.py     # 单exe入口点
└── hermesswarm-desktop.spec  # PyInstaller打包配置
```

## 🗺️ 开发路线图

### Phase 0: Demo验证（1个月）
- [x] Week 1: 环境搭建 + 基因提取 + 项目骨架
- [ ] Week 2: 最小融合 + 画布原型
- [ ] Week 3: 融合执行引擎
- [ ] Week 4: 3个场景验证

### Phase 1: MVP开发（6个月）
- [ ] M1: 架构融合深化
- [ ] M2: 可视化画布完整版
- [ ] M3: 自进化引擎
- [ ] M4: 桌面应用打包
- [ ] M5: 场景模板市场
- [ ] M6: 打磨发布

## 📄 License

Apache-2.0 — 详见 [LICENSE](LICENSE)

## 🙏 �5 致谢

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Nous Research
- [JiuwenSwarm](https://github.com/openJiuwen-ai/jiuwenswarm) — openJiuwen-ai
- [React Flow](https://reactflow.dev) — 可视化画布引擎
- [Tauri](https://tauri.app) — 桌面应用框架