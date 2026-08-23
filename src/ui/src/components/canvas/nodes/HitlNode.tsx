import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const HitlNode: React.FC<NodeProps> = ({ data }) => (
  <div style={{
    width: 180, background: "#fff", border: "2px solid #e91e63",
    borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(233,30,99,0.2)",
  }}>
    <Handle type="target" position={Position.Top} style={{ background: "#e91e63" }} />
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 20 }}>👤</span>
      <div>
        <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "人工审批"}</div>
        <div style={{ fontSize: 11, color: "#666" }}>HITL</div>
      </div>
    </div>
    <Handle type="source" position={Position.Bottom} style={{ background: "#e91e63" }} />
  </div>
);
export default HitlNode;