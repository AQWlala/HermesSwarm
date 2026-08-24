import React, { useState, useEffect } from "react";

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  state: string;
  use_count: number;
}

interface SkillStats {
  total: number;
  active: number;
  stale: number;
  archived: number;
  pinned: number;
  categories: number;
}

const SkillsPanel: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTask, setSearchTask] = useState("");
  const [discovered, setDiscovered] = useState<Skill[]>([]);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/skills");
      const data = await resp.json();
      setSkills(data.skills || []);
      setStats(data.stats || null);
    } catch (e) {
      console.error("Failed to fetch skills:", e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchSkills(); }, []);

  const discoverSkills = async () => {
    if (!searchTask.trim()) return;
    try {
      const resp = await fetch("/api/skills/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: searchTask }),
      });
      const data = await resp.json();
      setDiscovered(data.skills || []);
    } catch (e) {
      console.error("Failed to discover skills:", e);
    }
  };

  const stateColor = (state: string) => {
    if (state === "active") return "#008855";
    if (state === "stale") return "#cc8800";
    if (state === "archived") return "#999";
    return "#666";
  };

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: 18 }}>技能管理</h2>

      {stats && (
        <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
          {[
            { label: "总数", value: stats.total, color: "#333" },
            { label: "活跃", value: stats.active, color: "#008855" },
            { label: "过期", value: stats.stale, color: "#cc8800" },
            { label: "归档", value: stats.archived, color: "#999" },
            { label: "固定", value: stats.pinned, color: "#0066cc" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              padding: "8px 16px", background: "#f8f9fa", borderRadius: 8,
              textAlign: "center", minWidth: 70,
            }}>
              <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
              <div style={{ fontSize: 11, color: "#888" }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>按任务发现技能</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={searchTask}
            onChange={(e) => setSearchTask(e.target.value)}
            placeholder="输入任务描述..."
            style={{ flex: 1, padding: "8px 12px", border: "1px solid #ddd", borderRadius: 6, fontSize: 13 }}
            onKeyDown={(e) => e.key === "Enter" && discoverSkills()}
          />
          <button onClick={discoverSkills} style={{
            padding: "8px 16px", background: "#0066cc", color: "#fff",
            border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
          }}>发现</button>
        </div>
        {discovered.length > 0 && (
          <div style={{ marginTop: 8, padding: 12, background: "#f0f7ff", borderRadius: 6 }}>
            <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>匹配的技能:</div>
            {discovered.map((s) => (
              <div key={s.id} style={{ fontSize: 13, padding: "4px 0" }}>
                <strong>{s.name}</strong>: {s.description}
              </div>
            ))}
          </div>
        )}
      </div>

      <h3 style={{ fontSize: 14, marginBottom: 8 }}>所有技能 ({skills.length})</h3>
      {loading ? (
        <div style={{ color: "#999", padding: 20, textAlign: "center" }}>加载中...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {skills.map((skill) => (
            <div key={skill.id} style={{
              border: "1px solid #e0e0e0", borderRadius: 8, padding: 12,
              background: "#fff",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 14, fontWeight: 600 }}>{skill.name}</span>
                <span style={{
                  padding: "2px 8px", borderRadius: 10, fontSize: 10, fontWeight: 600,
                  background: `${stateColor(skill.state)}15`, color: stateColor(skill.state),
                }}>{skill.state}</span>
                <span style={{ fontSize: 11, color: "#888", marginLeft: "auto" }}>
                  使用{skill.use_count}次 · {skill.category}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>{skill.description}</div>
              {skill.tags.length > 0 && (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {skill.tags.map((tag) => (
                    <span key={tag} style={{
                      padding: "1px 6px", background: "#f0f0f0", borderRadius: 4, fontSize: 10, color: "#666",
                    }}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SkillsPanel;