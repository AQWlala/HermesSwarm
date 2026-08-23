import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const InputNode: React.FC<NodeProps> = ({ data }) => (
  <div style={{
    width: 140, background: "#fff", border: "2px solid #4caf50",
    borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(76,175,80,0.2)",
  }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 20 }}>📥</span>
      <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "输入"}</div>
    </div>
    <Handle type="source" position={Position.Bottom} style={{ background: "#4caf50" }} />
  </div>
);
export default InputNode;