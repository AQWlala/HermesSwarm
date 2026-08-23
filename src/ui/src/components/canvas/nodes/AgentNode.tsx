import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const AgentNode: React.FC<NodeProps> = ({ data }) => {
  const config = data.config || {};
  return (
    <div style={{
      width: 200, background: "#fff", border: "2px solid #0088cc",
      borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(0,136,204,0.2)",
    }}>
      <Handle type="target" position={Position.Top} id="input" style={{ background: "#0088cc" }} />
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 20 }}>🤖</span>
        <div>
          <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "智能体"}</div>
          <div style={{ fontSize: 11, color: "#666", textTransform: "uppercase" }}>
            {config.agent_type || "specialist"}
          </div>
        </div>
      </div>
      <div style={{ background: "#f8f9fa", borderRadius: 4, padding: 8, fontSize: 12 }}>
        <div>模型: <b>{config.model || "gpt-4"}</b></div>
        <div>温度: <b>{config.temperature ?? 0.7}</b></div>
      </div>
      <Handle type="source" position={Position.Bottom} id="output" style={{ background: "#0088cc" }} />
    </div>
  );
};
export default AgentNode;