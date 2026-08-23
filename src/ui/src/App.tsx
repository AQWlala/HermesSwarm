import React, { useState } from "react";
import FusionCanvas from "./components/canvas/FusionCanvas";

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"canvas" | "skills" | "memory" | "config">("canvas");

  return (
    <div className="app-layout">
      <div className="sidebar">
        <h1>☤ HermesSwarm</h1>
        <button className={activeTab === "canvas" ? "active" : ""} onClick={() => setActiveTab("canvas")}>
          🎨 可视化画布
        </button>
        <button className={activeTab === "skills" ? "active" : ""} onClick={() => setActiveTab("skills")}>
          📚 技能管理
        </button>
        <button className={activeTab === "memory" ? "active" : ""} onClick={() => setActiveTab("memory")}>
          🧠 记忆系统
        </button>
        <button className={activeTab === "config" ? "active" : ""} onClick={() => setActiveTab("config")}>
          ⚙️ 配置
        </button>
        <div style={{ marginTop: "auto", fontSize: 11, color: "#666" }}>
          v0.1.0 · 基因级融合
        </div>
      </div>
      <div className="main-content">
        {activeTab === "canvas" && (
          <>
            <div className="toolbar">
              <span style={{ fontSize: 14, fontWeight: "bold" }}>工作流编排</span>
              <span style={{ fontSize: 12, color: "#666" }}>拖拽节点构建工作流 → 点击执行</span>
            </div>
            <div className="canvas-container">
              <FusionCanvas />
            </div>
          </>
        )}
        {activeTab === "skills" && (
          <div style={{ padding: 24 }}>
            <h2>技能管理</h2>
            <p style={{ color: "#666", marginTop: 8 }}>融合 Hermes SKILL.md + JiuwenSwarm 单库可见性</p>
          </div>
        )}
        {activeTab === "memory" && (
          <div style={{ padding: 24 }}>
            <h2>记忆系统</h2>
            <p style={{ color: "#666", marginTop: 8 }}>融合 Hermes FTS5 + JiuwenSwarm 向量索引</p>
          </div>
        )}
        {activeTab === "config" && (
          <div style={{ padding: 24 }}>
            <h2>配置</h2>
            <p style={{ color: "#666", marginTop: 8 }}>Hermes基因 + JiuwenSwarm基因 开关配置</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;