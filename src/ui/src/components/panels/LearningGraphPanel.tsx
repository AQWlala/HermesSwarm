import React, { useState, useEffect } from "react";

interface GraphNode {
  id: string;
  label: string;
  use_count: number;
  success_rate: number;
  related: string[];
  memory_links: string[];
  state: string;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  type: "related" | "memory" | "lexical";
}

interface LearningGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    active_nodes: number;
    stale_nodes: number;
    archived_nodes: number;
  };
}

const STATE_COLORS: Record<string, string> = {
  active: "#008855",
  stale: "#cc8800",
  archived: "#999999",
  pinned: "#0066cc",
};

const EDGE_COLORS: Record<string, string> = {
  related: "#0066cc",
  memory: "#cc8800",
  lexical: "#cc66cc",
};

const LearningGraphPanel: React.FC = () => {
  const [data, setData] = useState<LearningGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterState, setFilterState] = useState<string>("all");
  const [showEdges, setShowEdges] = useState<Record<string, boolean>>({
    related: true,
    memory: true,
    lexical: true,
  });

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/curator/learning_graph");
      const json = await resp.json();
      setData(json);
    } catch (e) {
      console.error("Failed to fetch learning graph:", e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchGraph(); }, []);

  const filteredNodes = data?.nodes.filter(n =>
    filterState === "all" || n.state === filterState
  ) || [];

  const visibleEdges = data?.edges.filter(e => showEdges[e.type]) || [];

  const nodePositions = React.useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const nodes = filteredNodes;
    const radius = 180;
    const cx = 250;
    const cy = 220;
    nodes.forEach((node, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2;
      positions[node.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      };
    });
    return positions;
  }, [filteredNodes]);

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: 18 }}>Learning Graph 可视化</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
        <button onClick={fetchGraph} style={{
          padding: "6px 14px", background: "#0066cc", color: "#fff",
          border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
        }}>刷新</button>

        <select
          value={filterState}
          onChange={(e) => setFilterState(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #ddd", fontSize: 13 }}
        >
          <option value="all">全部状态</option>
          <option value="active">Active</option>
          <option value="stale">Stale</option>
          <option value="archived">Archived</option>
          <option value="pinned">Pinned</option>
        </select>

        {(["related", "memory", "lexical"] as const).map(t => (
          <label key={t} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={showEdges[t]}
              onChange={(e) => setShowEdges({ ...showEdges, [t]: e.target.checked })}
            />
            <span style={{ color: EDGE_COLORS[t] }}>● {t}</span>
          </label>
        ))}
      </div>

      {loading ? (
        <div style={{ color: "#999", padding: 20, textAlign: "center" }}>加载中...</div>
      ) : data ? (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            {Object.entries(data.stats || {}).map(([key, value]) => (
              <div key={key} style={{
                padding: "8px 16px", background: "#f8f9fa", borderRadius: 8,
                textAlign: "center", minWidth: 80,
              }}>
                <div style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
                <div style={{ fontSize: 11, color: "#888" }}>{key.replace(/_/g, " ")}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 16, flex: 1 }}>
            <div style={{
              flex: 1, background: "#fafafa", borderRadius: 8,
              border: "1px solid #e0e0e0", position: "relative", minHeight: 480,
            }}>
              <svg width="100%" height="480" style={{ display: "block" }}>
                {visibleEdges.map((edge, i) => {
                  const src = nodePositions[edge.source];
                  const tgt = nodePositions[edge.target];
                  if (!src || !tgt) return null;
                  return (
                    <line
                      key={i}
                      x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                      stroke={EDGE_COLORS[edge.type]}
                      strokeWidth={1 + edge.weight * 2}
                      strokeOpacity={0.4 + edge.weight * 0.4}
                    />
                  );
                })}
                {filteredNodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;
                  const color = STATE_COLORS[node.state] || "#666";
                  const isSelected = selectedNode?.id === node.id;
                  const r = 12 + Math.min(node.use_count, 20);
                  return (
                    <g
                      key={node.id}
                      onMouseEnter={() => setSelectedNode(node)}
                      style={{ cursor: "pointer" }}
                    >
                      <circle
                        cx={pos.x} cy={pos.y} r={r}
                        fill={color}
                        fillOpacity={isSelected ? 0.9 : 0.6}
                        stroke={isSelected ? "#000" : color}
                        strokeWidth={isSelected ? 3 : 1.5}
                      />
                      <text
                        x={pos.x} y={pos.y + r + 14}
                        textAnchor="middle"
                        fontSize={10}
                        fill="#333"
                      >
                        {node.label.length > 16 ? node.label.slice(0, 14) + "…" : node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
              <div style={{
                position: "absolute", bottom: 8, left: 8, fontSize: 10, color: "#888",
                background: "rgba(255,255,255,0.8)", padding: "2px 6px", borderRadius: 4,
              }}>
                {filteredNodes.length} 节点 · {visibleEdges.length} 边
              </div>
            </div>

            {selectedNode && (
              <div style={{
                width: 280, padding: 12, background: "#fff",
                borderRadius: 8, border: "1px solid #e0e0e0",
              }}>
                <h3 style={{ fontSize: 14, margin: "0 0 8px 0" }}>{selectedNode.label}</h3>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
                  ID: <code>{selectedNode.id}</code>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
                  <div style={{ padding: 8, background: "#f8f9fa", borderRadius: 6 }}>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>{selectedNode.use_count}</div>
                    <div style={{ fontSize: 10, color: "#888" }}>使用次数</div>
                  </div>
                  <div style={{ padding: 8, background: "#f8f9fa", borderRadius: 6 }}>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>
                      {(selectedNode.success_rate * 100).toFixed(0)}%
                    </div>
                    <div style={{ fontSize: 10, color: "#888" }}>成功率</div>
                  </div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <span style={{
                    padding: "2px 8px", borderRadius: 10, fontSize: 11,
                    background: (STATE_COLORS[selectedNode.state] || "#666") + "20",
                    color: STATE_COLORS[selectedNode.state] || "#666",
                  }}>{selectedNode.state}</span>
                </div>
                {selectedNode.related.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>关联技能</div>
                    {selectedNode.related.map(r => (
                      <div key={r} style={{ fontSize: 12, color: "#0066cc" }}>· {r}</div>
                    ))}
                  </div>
                )}
                {selectedNode.memory_links.length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>记忆链接</div>
                    {selectedNode.memory_links.map(m => (
                      <div key={m} style={{ fontSize: 12, color: "#cc8800" }}>· {m}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <div style={{ color: "#999", padding: 20, textAlign: "center" }}>无法获取Learning Graph数据</div>
      )}
    </div>
  );
};

export default LearningGraphPanel;