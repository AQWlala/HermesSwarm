import React from "react";
import { useCordis } from "../../cordis/useCordis";

const NodePalette: React.FC = () => {
  const ctx = useCordis();

  const onDragStart = (e: React.DragEvent, type: string) => {
    e.dataTransfer.setData("application/reactflow", type);
    e.dataTransfer.effectAllowed = "move";
  };

  const nodeDefs = ctx?.nodeTypes.list() || [];

  return (
    <div
      style={{
        background: "#fff",
        padding: 12,
        borderRadius: 8,
        boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
        minWidth: 150,
      }}
    >
      <h4 style={{ margin: "0 0 8px 0", fontSize: 14 }}>
        节点库 {nodeDefs.length > 0 && `(${nodeDefs.length})`}
      </h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {nodeDefs.map(({ type, label, icon, color }) => (
          <div
            key={type}
            draggable
            onDragStart={(e) => onDragStart(e, type)}
            style={{
              padding: "8px 12px",
              background: "#f5f5f5",
              borderRadius: 4,
              cursor: "grab",
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 13,
              borderLeft: `3px solid ${color}`,
            }}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NodePalette;
