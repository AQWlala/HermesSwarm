import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const OutputNode: React.FC<NodeProps> = ({ data }) => (
  <div style={{
    width: 140, background: "#fff", border: "2px solid #607d8b",
    borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(96,125,139,0.2)",
  }}>
    <Handle type="target" position={Position.Top} style={{ background: "#607d8b" }} />
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 20 }}>📤</span>
      <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "输出"}</div>
    </div>
  </div>
);
export default OutputNode;