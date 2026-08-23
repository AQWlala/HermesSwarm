import React from "react";

export interface TemplateData {
  id: string;
  name: string;
  description: string;
  icon: string;
  inputLabel: string;
  defaultInput: string;
  nodes: Array<{
    id: string;
    type: string;
    label: string;
    position: { x: number; y: number };
    config?: Record<string, unknown>;
  }>;
  edges: Array<{ id: string; source: string; target: string }>;
}

export const TEMPLATES: TemplateData[] = [
  {
    id: "content",
    name: "内容生产",
    description: "选题分析 → 并行(内容写作 + SEO优化) → 输出",
    icon: "📝",
    inputLabel: "主题",
    defaultInput: "AI编程助手的商业价值分析",
    nodes: [
      { id: "input", type: "input", label: "主题输入", position: { x: 0, y: 200 } },
      { id: "agent1", type: "agent", label: "选题分析", position: { x: 200, y: 200 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "agent2", type: "agent", label: "内容写作", position: { x: 420, y: 100 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "agent3", type: "agent", label: "SEO优化", position: { x: 420, y: 300 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "output", type: "output", label: "发布输出", position: { x: 640, y: 200 } },
    ],
    edges: [
      { id: "e1", source: "input", target: "agent1" },
      { id: "e2", source: "agent1", target: "agent2" },
      { id: "e3", source: "agent1", target: "agent3" },
      { id: "e4", source: "agent2", target: "output" },
      { id: "e5", source: "agent3", target: "output" },
    ],
  },
  {
    id: "data",
    name: "数据分析",
    description: "数据读取 → 分析 → 条件分支(报告/告警) → 输出",
    icon: "📊",
    inputLabel: "数据描述",
    defaultInput: "2024年Q4销售数据下降20%，需要分析原因",
    nodes: [
      { id: "input", type: "input", label: "数据源", position: { x: 0, y: 200 } },
      { id: "tool1", type: "tool", label: "读取数据", position: { x: 200, y: 200 },
        config: { tool_name: "web_search", parameters: { query: "sales data 2024" } } },
      { id: "agent1", type: "agent", label: "数据分析", position: { x: 400, y: 200 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "cond", type: "condition", label: "异常检测", position: { x: 600, y: 200 },
        config: { expression: "true" } },
      { id: "agent2", type: "agent", label: "生成报告", position: { x: 800, y: 100 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "agent3", type: "agent", label: "发送告警", position: { x: 800, y: 300 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "output", type: "output", label: "分析结果", position: { x: 1000, y: 200 } },
    ],
    edges: [
      { id: "e1", source: "input", target: "tool1" },
      { id: "e2", source: "tool1", target: "agent1" },
      { id: "e3", source: "agent1", target: "cond" },
      { id: "e4", source: "cond", target: "agent2" },
      { id: "e5", source: "cond", target: "agent3" },
      { id: "e6", source: "agent2", target: "output" },
      { id: "e7", source: "agent3", target: "output" },
    ],
  },
  {
    id: "code",
    name: "代码审查",
    description: "读取代码 → 并行(代码审查 + 安全检查) → HITL确认 → 输出",
    icon: "🔍",
    inputLabel: "代码路径",
    defaultInput: "src/core/engine.py",
    nodes: [
      { id: "input", type: "input", label: "代码路径", position: { x: 0, y: 200 } },
      { id: "tool1", type: "tool", label: "读取代码", position: { x: 200, y: 200 },
        config: { tool_name: "read_file", parameters: { path: "src/core/engine.py" } } },
      { id: "agent1", type: "agent", label: "代码审查", position: { x: 400, y: 100 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "agent2", type: "agent", label: "安全检查", position: { x: 400, y: 300 },
        config: { agent_type: "specialist", model: "deepseek-chat" } },
      { id: "hitl1", type: "hitl", label: "人工确认", position: { x: 620, y: 200 },
        config: { prompt: "请确认代码审查结果是否通过", timeout: 30 } },
      { id: "output", type: "output", label: "审查报告", position: { x: 840, y: 200 } },
    ],
    edges: [
      { id: "e1", source: "input", target: "tool1" },
      { id: "e2", source: "tool1", target: "agent1" },
      { id: "e3", source: "tool1", target: "agent2" },
      { id: "e4", source: "agent1", target: "hitl1" },
      { id: "e5", source: "agent2", target: "hitl1" },
      { id: "e6", source: "hitl1", target: "output" },
    ],
  },
];

interface Props {
  onSelect: (template: TemplateData) => void;
  activeId: string | null;
}

const WorkflowTemplates: React.FC<Props> = ({ onSelect, activeId }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h4 style={{ margin: "0 0 4px 0", fontSize: 13, color: "#666" }}>工作流模板</h4>
      {TEMPLATES.map((t) => (
        <button
          key={t.id}
          onClick={() => onSelect(t)}
          style={{
            padding: "10px 12px",
            background: activeId === t.id ? "#e8f4fd" : "#f8f8f8",
            border: activeId === t.id ? "2px solid #0088cc" : "1px solid #e0e0e0",
            borderRadius: 8,
            cursor: "pointer",
            textAlign: "left",
            display: "flex",
            flexDirection: "column",
            gap: 4,
            transition: "all 0.2s",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 18 }}>{t.icon}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#333" }}>{t.name}</span>
          </div>
          <span style={{ fontSize: 11, color: "#888", lineHeight: 1.4 }}>{t.description}</span>
        </button>
      ))}
    </div>
  );
};

export default WorkflowTemplates;