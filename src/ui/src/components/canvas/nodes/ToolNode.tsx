import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const ToolNode: React.FC<NodeProps> = ({ data }) => (
  <div style={{
    width: 180, background: "#fff", border: "2px solid #ff9800",
    borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(255,152,0,0.2)",
  }}>
    <Handle type="target" position={Position.Top} style={{ background: "#ff9800" }} />
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 20 }}>🔧</span>
      <div>
        <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "工具"}</div>
        <div style={{ fontSize: 11, color: "#666" }}>{data.config?.tool_name || "未选择"}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Bottom} style={{ background: "#ff9800" }} />
  </div>
);
export default ToolNode;