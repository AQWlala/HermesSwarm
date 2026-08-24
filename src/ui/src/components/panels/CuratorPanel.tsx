import React, { useState, useEffect } from "react";

interface CuratorStatus {
  skill_stats: Record<string, number>;
  learning_graph: Record<string, number>;
  total_reviews: number;
  recent_reviews: Array<{
    skill_id: string;
    action: string;
    reason: string;
    timestamp: string;
  }>;
}

const CuratorPanel: React.FC = () => {
  const [status, setStatus] = useState<CuratorStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [runResult, setRunResult] = useState<Record<string, unknown> | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/curator/status");
      const data = await resp.json();
      setStatus(data);
    } catch (e) {
      console.error("Failed to fetch curator status:", e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchStatus(); }, []);

  const runCurator = async () => {
    try {
      const resp = await fetch("/api/curator/run", { method: "POST" });
      const data = await resp.json();
      setRunResult(data);
      fetchStatus();
    } catch (e) {
      console.error("Failed to run curator:", e);
    }
  };

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: 18 }}>Curator 自进化引擎</h2>

      <button onClick={runCurator} style={{
        padding: "10px 20px", background: "#0066cc", color: "#fff",
        border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14,
        marginBottom: 16, fontWeight: 600,
      }}>运行 Curator 周期</button>

      {loading ? (
        <div style={{ color: "#999", padding: 20, textAlign: "center" }}>加载中...</div>
      ) : status ? (
        <>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>技能统计</h3>
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {Object.entries(status.skill_stats || {}).filter(([k]) => k !== "by_category").map(([key, value]) => (
              <div key={key} style={{
                padding: "8px 16px", background: "#f8f9fa", borderRadius: 8,
                textAlign: "center", minWidth: 70,
              }}>
                <div style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
                <div style={{ fontSize: 11, color: "#888" }}>{key}</div>
              </div>
            ))}
          </div>

          <h3 style={{ fontSize: 14, marginBottom: 8 }}>Learning Graph</h3>
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {Object.entries(status.learning_graph || {}).map(([key, value]) => (
              <div key={key} style={{
                padding: "8px 16px", background: "#f0f7ff", borderRadius: 8,
                textAlign: "center", minWidth: 70,
              }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#0066cc" }}>{value}</div>
                <div style={{ fontSize: 11, color: "#888" }}>{key}</div>
              </div>
            ))}
          </div>

          <h3 style={{ fontSize: 14, marginBottom: 8 }}>
            审查记录 (共{status.total_reviews || 0}次)
          </h3>
          {status.recent_reviews && status.recent_reviews.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {status.recent_reviews.map((r, i) => (
                <div key={i} style={{
                  border: "1px solid #e0e0e0", borderRadius: 8, padding: 10, background: "#fff",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{r.skill_id}</span>
                    <span style={{
                      padding: "2px 8px", borderRadius: 10, fontSize: 10,
                      background: r.action === "keep" ? "#e6f9f0" : r.action === "archive" ? "#fde8e8" : "#fff3e0",
                      color: r.action === "keep" ? "#008855" : r.action === "archive" ? "#cc0000" : "#cc8800",
                    }}>{r.action}</span>
                    <span style={{ fontSize: 11, color: "#999", marginLeft: "auto" }}>
                      {r.timestamp.slice(0, 19)}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#666" }}>{r.reason}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "#999", padding: 12, textAlign: "center" }}>暂无审查记录</div>
          )}
        </>
      ) : (
        <div style={{ color: "#999", padding: 20, textAlign: "center" }}>无法获取Curator状态</div>
      )}

      {runResult && (
        <div style={{
          marginTop: 20, padding: 12, background: "#e6f9f0",
          borderRadius: 8, border: "1px solid #008855",
        }}>
          <h4 style={{ fontSize: 13, margin: "0 0 8px 0", color: "#008855" }}>Curator运行结果</h4>
          <pre style={{ fontSize: 11, color: "#333", margin: 0, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(runResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default CuratorPanel;