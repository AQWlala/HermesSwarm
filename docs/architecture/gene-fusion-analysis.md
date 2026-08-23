# HermesSwarm 基因融合分析报告

> 基于 Hermes Agent v0.20.5 + JiuwenSwarm v0.2.5 + Codex 工程实践的真实基因提取

## 一、三项目基因图谱

### Hermes Agent 基因（自进化学习线）

| 基因 | 源路径 | 融合目标 | 提取方式 |
|------|--------|---------|---------|
| **Curator 自进化引擎** | `agent/curator.py` (87KB) | `src/agents/evolution/curator.py` | 直接复用核心逻辑，适配Skill格式 |
| **Learning Graph** | `agent/learning_graph.py` (11KB) | `src/agents/evolution/learning_graph.py` | 纯数据结构，直接复用 |
| **Skill SKILL.md 格式** | `skills/` + `agent/skill_utils.py` | `src/skills/format.py` | YAML frontmatter + Markdown body |
| **Skill Usage 遥测** | `tools/skill_usage.py` (52KB) | `src/skills/usage.py` | Sidecar JSON + 原子写入 + 跨进程锁 |
| **Learn Prompt** | `agent/learn_prompt.py` (14KB) | `src/skills/learn_prompt.py` | /learn 命令提示构建 |
| **MemoryProvider ABC** | `agent/memory_provider.py` (17KB) | `src/memory/provider.py` | 纯ABC，直接作为基类 |
| **MemoryManager** | `agent/memory_manager.py` (52KB) | `src/memory/manager.py` | 编排器，适配集成点 |
| **Tool Registry** | `tools/registry.py` (56KB) | `src/tools/registry.py` | AST自动发现机制 |
| **SessionDB (FTS5)** | `hermes_state.py` (620KB) | `src/memory/session_db.py` | SQLite + FTS5 全文搜索 |
| **Prompt Builder** | `agent/prompt_builder.py` (129KB) | `src/core/prompt_builder.py` | 系统提示组装 |
| **Context Compressor** | `agent/context_compressor.py` (397KB) | `src/core/compressor.py` | 上下文压缩 |
| **多平台网关** | `gateway/platforms/base.py` (331KB) | `src/gateway/platforms/` | BasePlatformAdapter |
| **Web UI 技术栈** | `web/package.json` | `src/ui/` | React 19 + Vite + Tailwind |

### JiuwenSwarm 基因（多智能体协作线）

| 基因 | 源路径 | 融合目标 | 提取方式 |
|------|--------|---------|---------|
| **SwarmBuildContext** | `agents/swarm/context.py` (8KB) | `src/agents/swarm/context.py` | 声明式Spec装配上下文 |
| **Swarm Assembly** | `agents/swarm/assembly.py` (13KB) | `src/agents/swarm/assembly.py` | enrich_team_spec_for_swarm() |
| **Swarm Providers** | `agents/swarm/providers/` (36个元素) | `src/agents/swarm/providers/` | 能力工厂 |
| **TeamManager** | `agents/harness/team/team_manager.py` (108KB) | `src/agents/team/manager.py` | Team生命周期管理 |
| **SwarmFlow 算子** | openjiuwen上游 `swarmflow` | `src/workflow/operators.py` | agent/parallel/pipeline/human |
| **WorkflowRunState** | `handlers/workflow_state.py` (49KB) | `src/workflow/state.py` | 纯pydantic状态机 |
| **HITL 契约** | `common/schema/swarmflow_reply.py` | `src/workflow/hitl.py` | SwarmflowReplyParams |
| **分布式运行时** | `distributed_runtime.py` (14KB) | `src/agents/team/distributed.py` | pyzmq + PostgreSQL |
| **A2X 注册中心** | `agents/harness/team/a2x/` | `src/agents/team/a2x/` | 空闲节点注册 |
| **Skill 自演进 Rails** | `evolution_rails.py` (30KB) | `src/skills/evolution_rails.py` | 信号检测 + 自动演进 |
| **Symphony 动态图谱** | `symphony/evolution/` | `src/skills/symphony/` | 事件流 + overlay重建 |
| **MemoryIndexManager** | `memory/manager.py` (44KB) | `src/memory/index_manager.py` | SQLite+FTS+向量索引 |
| **权限分层策略** | `permissions/` + `builtin_rules.yaml` | `src/tools/permissions.py` | tiered_policy 9步流程 |
| **jiuwenbox 沙箱** | `jiuwenbox/` 整包 | `src/sandbox/` | bubblewrap隔离 |
| **IM 渠道** | `gateway/im_pipeline/` | `src/gateway/im/` | 飞书/钉钉/企业微信/小艺 |

### Codex 工程实践基因（架构治理线）

| 实践 | 借鉴方式 |
|------|---------|
| **协议/传输/客户端分离** | `src/protocol/` + `src/transport/` + `src/client/` |
| **ext/ 隔离可插拔能力** | `src/ext/` 存放agent/connectors/skills/mcp等 |
| **utils/ 微模块策略** | `src/utils/` 每个模块<500 LoC |
| **Rust↔TS 类型自动生成** | ts-rs / prost + ts-proto |
| **AGENTS.md 代码规范** | 集中治理AI编码规范 |
| **供应链硬化** | cargo-deny + pnpm trust policy |
| **模块大小硬上限** | <500 LoC，超800必须拆 |

## 二、基因融合矩阵

```
                    Hermes基因          JiuwenSwarm基因        融合结果
                    ──────────          ──────────────        ────────
自进化              Curator(后台)   +   Skill自演进Rails  →   双重进化环
                    Learning Graph  +   Symphony动态图谱  →   可视化学习图谱
                    Learn Prompt    +   /evolve命令       →   统一进化入口

技能系统            SKILL.md格式    +   单库+可见性元数据  →   统一技能格式
                    skill_usage     +   evolutions.json   →   使用+进化追踪
                    skills_hub      +   Swarm Skills Hub  →   统一技能中心

记忆系统            MemoryProvider  +   MemoryIndexManager→   统一记忆ABC
                    SessionDB(FTS5)+   向量索引           →   FTS+向量双索引
                    MEMORY.md       +   Coding Memory     →   分层记忆

智能体              AIAgent(单)     +   TeamManager(多)   →   单+多智能体统一
                    子代理委派      +   Leader-Teammate   →   委派+团队协作
                    prompt缓存      +   SwarmBuildContext →   缓存+装配上下文

工作流              CLI/TUI         +   SwarmFlow算子     →   可视化SwarmFlow
                    cron调度        +   WorkflowRunState  →   状态机工作流
                    -               +   HITL              →   人机协同节点

工具系统            Tool Registry   +   权限分层策略      →   注册+审批统一
                    40+工具         +   30+工具           →   70+工具池
                    MCP集成         +   A2X协议           →   MCP+A2X双协议

网关                20+平台适配器   +   10+IM渠道         →   全平台覆盖
                    Telegram等      +   飞书/钉钉等       →   国际+国内

安全                命令审批        +   jiuwenbox沙箱     →   审批+沙箱双重
                    DM配对          +   Landlock/Seccomp  →   多层隔离
```

## 三、融合架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  L7 表现层: Tauri桌面应用 + Web UI + TUI                        │
│     React Flow画布 + 节点库 + 属性面板 + 执行监控               │
├─────────────────────────────────────────────────────────────────┤
│  L6 协议层: WebSocket(画布↔引擎) + JSON-RPC(Tauri↔Python)      │
├─────────────────────────────────────────────────────────────────┤
│  L5 工作流层: SwarmFlow引擎 + WorkflowRunState + HITL           │
│     算子: agent/parallel/pipeline/human/human_session           │
├─────────────────────────────────────────────────────────────────┤
│  L4 智能体层: Leader + Specialist + TeamManager                 │
│     SwarmBuildContext装配 + 分布式(A2X+pyzmq)                  │
├─────────────────────────────────────────────────────────────────┤
│  L3 进化层: Curator + LearningGraph + Skill自演进 + Symphony    │
│     双重进化环: Hermes闭环 + JiuwenSwarm信号检测               │
├─────────────────────────────────────────────────────────────────┤
│  L2 能力层: Skills(统一格式) + Memory(FTS+向量) + Tools(70+)   │
│     权限分层策略 + jiuwenbox沙箱                                │
├─────────────────────────────────────────────────────────────────┤
│  L1 基础层: Config + EventBus + SessionDB + Provider适配        │
├─────────────────────────────────────────────────────────────────┤
│  L0 网关层: Telegram/Discord/Slack + 飞书/钉钉/企业微信/小艺   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心数据流

```
用户拖拽画布 → 生成Workflow JSON
    ↓ WebSocket
工作流引擎解析 → 创建WorkflowRunState
    ↓ 拓扑排序
节点执行队列 → 并行/串行执行
    ↓
每个节点:
  ├── Agent节点 → SwarmBuildContext装配 → Leader/Teammate执行
  ├── Tool节点 → Tool Registry查找 → 权限审批 → 执行
  ├── Condition节点 → 评估表达式 → 路由
  └── HITL节点 → 发布human_prompt事件 → 等待前端回复
    ↓
执行结果 → WorkflowRunState.apply() → delta
    ↓ WebSocket broadcast
前端画布更新节点状态
    ↓
工作流完成 → 触发自进化
    ├── Hermes Curator: 技能状态转换 + 合并优化
    └── JiuwenSwarm: 信号检测 + evolutions.json
    ↓
Learning Graph更新 → 可视化展示
```

## 四、基因提取优先级（Phase 0 Demo范围）

### P0: 必须提取（Week 1-2）
1. **SwarmBuildContext + 装配框架** — 智能体装配基础
2. **WorkflowRunState 状态机** — 工作流核心
3. **Tool Registry** — 工具注册发现
4. **MemoryProvider ABC** — 记忆抽象
5. **Skill SKILL.md 格式** — 技能定义

### P1: 重要提取（Week 3）
6. **SwarmFlow 算子** — 工作流算子
7. **HITL 契约** — 人机协同
8. **权限分层策略** — 安全基础
9. **React Flow 画布** — 可视化前端

### P2: 后续提取（Phase 1）
10. **Curator 自进化** — 闭环学习
11. **TeamManager** — 多智能体管理
12. **分布式运行时** — 跨机器协作
13. **多平台网关** — 全渠道接入