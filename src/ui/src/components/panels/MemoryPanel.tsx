import React, { useState } from "react";

interface MemoryResult {
  id: string;
  content: string;
  type: string;
  score: number;
}

const MemoryPanel: React.FC = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemoryResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [storeContent, setStoreContent] = useState("");
  const [storeType, setStoreType] = useState("long");
  const [storeMsg, setStoreMsg] = useState("");

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const resp = await fetch("/api/memory/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 20 }),
      });
      const data = await resp.json();
      setResults(data.results || []);
    } catch (e) {
      console.error("Search failed:", e);
    }
    setLoading(false);
  };

  const store = async () => {
    if (!storeContent.trim()) return;
    try {
      const resp = await fetch("/api/memory/store", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: storeContent, type: storeType }),
      });
      const data = await resp.json();
      if (data.success) {
        setStoreMsg(`已存储 (ID: ${data.id})`);
        setStoreContent("");
        setTimeout(() => setStoreMsg(""), 3000);
      }
    } catch (e) {
      setStoreMsg("存储失败");
    }
  };

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: 18 }}>记忆系统</h2>

      <div style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>存储记忆</h3>
        <textarea
          value={storeContent}
          onChange={(e) => setStoreContent(e.target.value)}
          placeholder="输入要存储的内容..."
          style={{
            width: "100%", minHeight: 60, padding: "8px 12px",
            border: "1px solid #ddd", borderRadius: 6, fontSize: 13,
            resize: "vertical", boxSizing: "border-box",
          }}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
          <select
            value={storeType}
            onChange={(e) => setStoreType(e.target.value)}
            style={{ padding: "6px 8px", border: "1px solid #ddd", borderRadius: 6, fontSize: 12 }}
          >
            <option value="long">长期记忆</option>
            <option value="short">短期记忆</option>
            <option value="episodic">情景记忆</option>
            <option value="semantic">语义记忆</option>
          </select>
          <button onClick={store} style={{
            padding: "6px 16px", background: "#008855", color: "#fff",
            border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
          }}>存储</button>
          {storeMsg && <span style={{ fontSize: 12, color: "#008855" }}>{storeMsg}</span>}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>搜索记忆 (FTS5三表路由)</h3>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索内容 (支持中英文、代码)..."
            style={{ flex: 1, padding: "8px 12px", border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
            onKeyDown={(e) => e.key === "Enter" && search()}
          />
          <button onClick={search} style={{
            padding: "8px 16px", background: "#0066cc", color: "#fff",
            border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
          }}>搜索</button>
        </div>

        {loading ? (
          <div style={{ color: "#999", padding: 20, textAlign: "center" }}>搜索中...</div>
        ) : results.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {results.map((r) => (
              <div key={r.id} style={{
                border: "1px solid #e0e0e0", borderRadius: 8, padding: 12, background: "#fff",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{
                    padding: "2px 8px", borderRadius: 10, fontSize: 10,
                    background: r.type === "long" ? "#e6f9f0" : r.type === "episodic" ? "#fff3e0" : "#f0f7ff",
                    color: r.type === "long" ? "#008855" : r.type === "episodic" ? "#cc8800" : "#0066cc",
                  }}>{r.type}</span>
                  <span style={{ fontSize: 11, color: "#999", marginLeft: "auto" }}>
                    score: {r.score.toFixed(4)}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#333", lineHeight: 1.5 }}>{r.content}</div>
              </div>
            ))}
          </div>
        ) : query ? (
          <div style={{ color: "#999", padding: 20, textAlign: "center" }}>无结果</div>
        ) : null}
      </div>
    </div>
  );
};

export default MemoryPanel;