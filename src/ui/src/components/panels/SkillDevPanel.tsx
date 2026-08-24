import React, { useState, useEffect } from "react";

interface PipelineSummary {
  pipeline_id: string;
  skill_name: string;
  stage: string;
  suspended: boolean;
  updated_at: string;
}

interface PipelineDetail {
  pipeline_id: string;
  skill_name: string;
  skill_description: string;
  stage: string;
  previous_stage: string | null;
  attempt_count: number;
  max_attempts: number;
  artifacts: Array<{
    stage: string;
    timestamp: string;
    content: string;
    metadata: Record<string, unknown>;
    file_paths: string[];
  }>;
  suspended: boolean;
  suspend_reason: string | null;
  suspend_at_stage: string | null;
  eval_scores: Record<string, number>;
  improve_iterations: number;
  max_improve_iterations: number;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  package_path: string;
  error_message: string;
}

const STAGE_ORDER = ["init", "plan", "generate", "validate", "test", "evaluate", "improve", "package", "done"];

const STAGE_LABELS: Record<string, string> = {
  init: "初始化",
  plan: "规划",
  generate: "生成",
  validate: "验证",
  test: "测试",
  evaluate: "评估",
  improve: "改进",
  package: "打包",
  done: "完成",
  failed: "失败",
  suspended: "挂起",
};

const STAGE_COLORS: Record<string, string> = {
  init: "#666",
  plan: "#0066cc",
  generate: "#0088cc",
  validate: "#cc8800",
  test: "#cc66cc",
  evaluate: "#cc6600",
  improve: "#cc0066",
  package: "#008855",
  done: "#008855",
  failed: "#cc0000",
  suspended: "#cc8800",
};

const SkillDevPanel: React.FC = () => {
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
  const [selected, setSelected] = useState<PipelineDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [newSkillName, setNewSkillName] = useState("");
  const [newSkillDesc, setNewSkillDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchPipelines = async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/skilldev/pipelines");
      const data = await resp.json();
      setPipelines(data.pipelines || []);
    } catch (e) {
      console.error("Failed to fetch pipelines:", e);
    }
    setLoading(false);
  };

  const fetchDetail = async (id: string) => {
    try {
      const resp = await fetch(`/api/skilldev/state?id=${id}`);
      const data = await resp.json();
      setSelected(data);
    } catch (e) {
      console.error("Failed to fetch pipeline detail:", e);
    }
  };

  useEffect(() => { fetchPipelines(); }, []);

  const createPipeline = async () => {
    if (!newSkillName || !newSkillDesc) return;
    setCreating(true);
    try {
      const resp = await fetch("/api/skilldev/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_name: newSkillName, skill_description: newSkillDesc }),
      });
      const data = await resp.json();
      setNewSkillName("");
      setNewSkillDesc("");
      fetchPipelines();
      if (data.pipeline_id) fetchDetail(data.pipeline_id);
    } catch (e) {
      console.error("Failed to start pipeline:", e);
    }
    setCreating(false);
  };

  const resumePipeline = async (id: string) => {
    try {
      await fetch("/api/skilldev/resume", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_id: id }),
      });
      fetchPipelines();
      fetchDetail(id);
    } catch (e) {
      console.error("Failed to resume:", e);
    }
  };

  const pausePipeline = async (id: string) => {
    try {
      await fetch("/api/skilldev/pause", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_id: id }),
      });
      fetchPipelines();
      fetchDetail(id);
    } catch (e) {
      console.error("Failed to pause:", e);
    }
  };

  const currentStageIdx = selected ? STAGE_ORDER.indexOf(selected.stage) : -1;

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: 18 }}>SkillDev 确定性流水线</h2>

      <div style={{
        marginBottom: 20, padding: 12, background: "#f8f9fa",
        borderRadius: 8, border: "1px solid #e0e0e0",
      }}>
        <h3 style={{ fontSize: 13, margin: "0 0 8px 0" }}>创建新技能流水线</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            placeholder="技能名称 (如: code-review)"
            value={newSkillName}
            onChange={(e) => setNewSkillName(e.target.value)}
            style={{ flex: 1, minWidth: 150, padding: "8px 10px", borderRadius: 6, border: "1px solid #ddd", fontSize: 13 }}
          />
          <input
            placeholder="技能描述"
            value={newSkillDesc}
            onChange={(e) => setNewSkillDesc(e.target.value)}
            style={{ flex: 2, minWidth: 200, padding: "8px 10px", borderRadius: 6, border: "1px solid #ddd", fontSize: 13 }}
          />
          <button
            onClick={createPipeline}
            disabled={creating || !newSkillName || !newSkillDesc}
            style={{
              padding: "8px 16px", background: "#008855", color: "#fff",
              border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
              opacity: creating || !newSkillName || !newSkillDesc ? 0.5 : 1,
            }}
          >{creating ? "创建中..." : "启动"}</button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 16, flex: 1 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>
            流水线列表 ({pipelines.length})
            <button onClick={fetchPipelines} style={{
              marginLeft: 8, padding: "2px 8px", fontSize: 11,
              border: "1px solid #ddd", borderRadius: 4, background: "#fff", cursor: "pointer",
            }}>刷新</button>
          </h3>
          {loading ? (
            <div style={{ color: "#999", padding: 12, textAlign: "center" }}>加载中...</div>
          ) : pipelines.length === 0 ? (
            <div style={{ color: "#999", padding: 12, textAlign: "center" }}>暂无流水线</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {pipelines.map(p => (
                <div
                  key={p.pipeline_id}
                  onClick={() => fetchDetail(p.pipeline_id)}
                  style={{
                    padding: 10, borderRadius: 8, cursor: "pointer",
                    border: selected?.pipeline_id === p.pipeline_id ? "2px solid #0066cc" : "1px solid #e0e0e0",
                    background: selected?.pipeline_id === p.pipeline_id ? "#f0f7ff" : "#fff",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{p.skill_name}</span>
                    <span style={{
                      padding: "2px 8px", borderRadius: 10, fontSize: 10,
                      background: (STAGE_COLORS[p.stage] || "#666") + "20",
                      color: STAGE_COLORS[p.stage] || "#666",
                    }}>{STAGE_LABELS[p.stage] || p.stage}</span>
                    {p.suspended && (
                      <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 10, background: "#fff3e0", color: "#cc8800" }}>挂起</span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: "#999", marginTop: 4 }}>
                    {p.pipeline_id.slice(0, 20)}... · {p.updated_at.slice(0, 19)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <div style={{ width: 420, padding: 12, background: "#fff", borderRadius: 8, border: "1px solid #e0e0e0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ fontSize: 14, margin: 0 }}>{selected.skill_name}</h3>
              <div style={{ display: "flex", gap: 6 }}>
                {selected.suspended && (
                  <button onClick={() => resumePipeline(selected.pipeline_id)} style={{
                    padding: "4px 10px", fontSize: 11, background: "#008855", color: "#fff",
                    border: "none", borderRadius: 4, cursor: "pointer",
                  }}>恢复</button>
                )}
                {!selected.suspended && selected.stage !== "done" && selected.stage !== "failed" && (
                  <button onClick={() => pausePipeline(selected.pipeline_id)} style={{
                    padding: "4px 10px", fontSize: 11, background: "#cc8800", color: "#fff",
                    border: "none", borderRadius: 4, cursor: "pointer",
                  }}>暂停</button>
                )}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 6 }}>阶段进度</div>
              <div style={{ display: "flex", gap: 2, alignItems: "center" }}>
                {STAGE_ORDER.map((stage, i) => {
                  const reached = i <= currentStageIdx;
                  const current = stage === selected.stage;
                  return (
                    <React.Fragment key={stage}>
                      <div
                        title={STAGE_LABELS[stage]}
                        style={{
                          width: 28, height: 28, borderRadius: "50%",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: 9, fontWeight: 600,
                          background: current ? (STAGE_COLORS[stage] || "#666") : reached ? "#e6f9f0" : "#f5f5f5",
                          color: current ? "#fff" : reached ? "#008855" : "#999",
                          border: current ? "2px solid #000" : "2px solid transparent",
                        }}
                      >{stage.slice(0, 2)}</div>
                      {i < STAGE_ORDER.length - 1 && (
                        <div style={{
                          flex: 1, height: 2,
                          background: i < currentStageIdx ? "#008855" : "#e0e0e0",
                        }} />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>

            {selected.error_message && (
              <div style={{
                marginBottom: 12, padding: 8, background: "#fde8e8",
                borderRadius: 6, fontSize: 12, color: "#cc0000",
              }}>
                <strong>错误:</strong> {selected.error_message}
              </div>
            )}

            {Object.keys(selected.eval_scores).length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "#888", marginBottom: 6 }}>评估分数</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
                  {Object.entries(selected.eval_scores).map(([dim, score]) => (
                    <div key={dim} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <span style={{ fontSize: 11, color: "#666", width: 80 }}>{dim}</span>
                      <div style={{ flex: 1, height: 6, background: "#f0f0f0", borderRadius: 3, overflow: "hidden" }}>
                        <div style={{
                          width: `${score * 100}%`, height: "100%",
                          background: score >= 0.7 ? "#008855" : score >= 0.5 ? "#cc8800" : "#cc0000",
                        }} />
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 600, width: 30, textAlign: "right" }}>{(score * 100).toFixed(0)}</span>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: "#888", marginTop: 6 }}>
                  改进迭代: {selected.improve_iterations}/{selected.max_improve_iterations}
                </div>
              </div>
            )}

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 6 }}>阶段产出 ({selected.artifacts.length})</div>
              <div style={{ maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
                {selected.artifacts.map((a, i) => (
                  <div key={i} style={{
                    padding: 6, background: "#f8f9fa", borderRadius: 4, fontSize: 11,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600, color: STAGE_COLORS[a.stage] || "#666" }}>
                        {STAGE_LABELS[a.stage] || a.stage}
                      </span>
                      <span style={{ color: "#999" }}>{a.timestamp.slice(11, 19)}</span>
                    </div>
                    {a.file_paths.length > 0 && (
                      <div style={{ color: "#0066cc", marginTop: 2 }}>{a.file_paths[0]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {selected.package_path && (
              <div style={{
                padding: 8, background: "#e6f9f0", borderRadius: 6,
                fontSize: 12, color: "#008855",
              }}>
                <strong>已打包:</strong> {selected.package_path}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SkillDevPanel;