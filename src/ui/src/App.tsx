import React, { useState } from "react";
import FusionCanvas from "./components/canvas/FusionCanvas";
import WorkflowTemplates, { type TemplateData } from "./components/canvas/WorkflowTemplates";
import SkillsPanel from "./components/panels/SkillsPanel";
import MemoryPanel from "./components/panels/MemoryPanel";
import CuratorPanel from "./components/panels/CuratorPanel";
import LearningGraphPanel from "./components/panels/LearningGraphPanel";
import SkillDevPanel from "./components/panels/SkillDevPanel";

type TabId = "canvas" | "skills" | "memory" | "curator" | "graph" | "skilldev";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "canvas", label: "工作流画布", icon: "🎨" },
  { id: "skills", label: "技能管理", icon: "⚡" },
  { id: "memory", label: "记忆系统", icon: "🧠" },
  { id: "curator", label: "Curator", icon: "🔄" },
  { id: "graph", label: "Learning Graph", icon: "📊" },
  { id: "skilldev", label: "SkillDev", icon: "🔧" },
];

const App: React.FC = () => {
  const [tab, setTab] = useState<TabId>("canvas");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateData | null>(null);
  const [execResult, setExecResult] = useState<Record<string, unknown> | null>(null);
  const [, setExecStatus] = useState<string>("idle");

  const renderResult = () => {
    if (!execResult) return null;
    const outputs = (execResult as any).outputs || {};
    const status = (execResult as any).status || "unknown";
    const layers = (execResult as any).layers || [];

    return (
      <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <span style={{
            padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600,
            background: status === "completed" ? "#e6f9f0" : status === "failed" ? "#fde8e8" : "#f5f5f5",
            color: status === "completed" ? "#008855" : status === "failed" ? "#cc0000" : "#666",
          }}>
            {status === "completed" ? "✓ 完成" : status === "failed" ? "✗ 失败" : status}
          </span>
          {layers.length > 0 && <span style={{ fontSize: 12, color: "#888" }}>{layers.length}层拓扑</span>}
        </div>

        {layers.length > 0 && (
          <div style={{ marginBottom: 16, padding: "8px 12px", background: "#f8f9fa", borderRadius: 6, fontSize: 11, color: "#666" }}>
            {layers.map((layer: string[], i: number) => (
              <div key={i}>Layer {i}: [{layer.join(", ")}]</div>
            ))}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {Object.entries(outputs).map(([nodeId, output]) => {
            const isObj = typeof output === "object" && output !== null;
            const isError = isObj && "error" in (output as object);
            const agentName = isObj ? (output as any).agent : null;
            const outputText = isObj ? (output as any).output : output;
            const skills = isObj ? (output as any).skills_used : null;

            return (
              <div key={nodeId} style={{
                border: `1px solid ${isError ? "#cc0000" : "#e0e0e0"}`,
                borderRadius: 8, overflow: "hidden",
              }}>
                <div style={{
                  padding: "8px 12px", background: isError ? "#fde8e8" : "#f8f9fa",
                  display: "flex", alignItems: "center", gap: 8,
                  borderBottom: `1px solid ${isError ? "#cc0000" : "#e0e0e0"}`,
                }}>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{nodeId}</span>
                  {agentName && <span style={{ fontSize: 12, color: "#666" }}>· {agentName}</span>}
                  {skills && skills.length > 0 && <span style={{ fontSize: 11, color: "#888" }}>· 技能: {skills.join(", ")}</span>}
                  {isError && <span style={{ fontSize: 12, color: "#cc0000", marginLeft: "auto" }}>错误</span>}
                </div>
                <div style={{ padding: 12, fontSize: 13, lineHeight: 1.6, color: "#333", maxHeight: 300, overflowY: "auto" }}>
                  {isError ? (
                    <span style={{ color: "#cc0000" }}>{String((output as any).error)}</span>
                  ) : outputText ? (
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: 13 }}>{String(outputText)}</pre>
                  ) : (
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 11, color: "#888" }}>
                      {JSON.stringify(output, null, 2).slice(0, 2000)}
                    </pre>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="app-layout">
      <div className="sidebar">
        <h1>☤ HermesSwarm</h1>
        <div style={{ marginBottom: 16 }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                width: "100%", padding: "10px 12px", marginBottom: 4,
                border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
                background: tab === t.id ? "#0066cc" : "transparent",
                color: tab === t.id ? "#fff" : "#333",
                fontWeight: tab === t.id ? 600 : 400,
              }}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </div>
        {tab === "canvas" && (
          <div style={{ marginBottom: 16 }}>
            <WorkflowTemplates onSelect={setSelectedTemplate} activeId={selectedTemplate?.id || null} />
          </div>
        )}
        <div style={{ marginTop: "auto", fontSize: 11, color: "#666" }}>
          v0.7.0 · DeepSeek LLM
        </div>
      </div>
      <div className="main-content">
        {tab === "canvas" && (
          <>
            <div className="toolbar">
              <span style={{ fontSize: 14, fontWeight: "bold" }}>
                {selectedTemplate ? `${selectedTemplate.icon} ${selectedTemplate.name}` : "🎨 可视化画布"}
              </span>
              <span style={{ fontSize: 12, color: "#666" }}>
                {selectedTemplate ? selectedTemplate.description : "选择左侧模板或拖拽节点构建工作流"}
              </span>
            </div>
            <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
              <div className="canvas-container" style={{ flex: 1 }}>
                <FusionCanvas template={selectedTemplate} onResult={setExecResult} onStatus={setExecStatus} />
              </div>
              {execResult && (
                <div style={{ width: 400, borderLeft: "1px solid #ddd", background: "#fff", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                  <div style={{ padding: "12px 16px", borderBottom: "1px solid #ddd", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ margin: 0, fontSize: 15 }}>执行结果</h3>
                    <button onClick={() => setExecResult(null)} style={{ border: "none", background: "none", cursor: "pointer", fontSize: 16, color: "#999" }}>×</button>
                  </div>
                  {renderResult()}
                </div>
              )}
            </div>
          </>
        )}
        {tab === "skills" && <SkillsPanel />}
        {tab === "memory" && <MemoryPanel />}
        {tab === "curator" && <CuratorPanel />}
        {tab === "graph" && <LearningGraphPanel />}
        {tab === "skilldev" && <SkillDevPanel />}
      </div>
    </div>
  );
};

export default App;
