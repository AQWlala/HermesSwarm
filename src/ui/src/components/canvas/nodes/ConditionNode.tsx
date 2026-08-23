import React from "react";
import { Handle, Position, NodeProps } from "reactflow";

const ConditionNode: React.FC<NodeProps> = ({ data }) => (
  <div style={{
    width: 160, background: "#fff", border: "2px solid #9c27b0",
    borderRadius: 8, padding: 12, boxShadow: "0 2px 8px rgba(156,39,176,0.2)",
  }}>
    <Handle type="target" position={Position.Top} style={{ background: "#9c27b0" }} />
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 20 }}>🔀</span>
      <div style={{ fontWeight: "bold", fontSize: 14 }}>{data.label || "条件"}</div>
    </div>
    <div style={{ fontSize: 11, color: "#666", marginTop: 4, fontFamily: "monospace" }}>
      {data.config?.expression || "true"}
    </div>
    <Handle type="source" position={Position.Bottom} id="true" style={{ background: "#4caf50", left: "30%" }} />
    <Handle type="source" position={Position.Bottom} id="false" style={{ background: "#f44336", left: "70%" }} />
  </div>
);
export default ConditionNode;