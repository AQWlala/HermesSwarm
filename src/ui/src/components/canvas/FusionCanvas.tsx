import React, { useCallback, useRef, useState, useEffect } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, addEdge, Connection, Edge, Node, Panel,
  useNodesState, useEdgesState, MarkerType, BackgroundVariant, NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import AgentNode from "./nodes/AgentNode";
import ToolNode from "./nodes/ToolNode";
import ConditionNode from "./nodes/ConditionNode";
import HitlNode from "./nodes/HitlNode";
import InputNode from "./nodes/InputNode";
import OutputNode from "./nodes/OutputNode";
import NodePalette from "./NodePalette";
import { useCordis } from "../../cordis/useCordis";
import type { CanvasNodeData } from "../../cordis/types";
import type { TemplateData } from "./WorkflowTemplates";

const nodeTypes: NodeTypes = {
  agent: AgentNode, tool: ToolNode, condition: ConditionNode,
  hitl: HitlNode, input: InputNode, output: OutputNode,
};

interface Props {
  template: TemplateData | null;
  onResult: (result: Record<string, unknown>) => void;
  onStatus: (status: string) => void;
}

const FusionCanvas: React.FC<Props> = ({ template, onResult, onStatus }) => {
  const ctx = useCordis();
  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<CanvasNodeData> | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [inputData, setInputData] = useState("");
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [hitlPrompt, setHitlPrompt] = useState<{ runId: string; nodeId: string; prompt: string } | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!template) return;
    setInputData(template.defaultInput);
    setNodes(template.nodes.map((n) => ({
      id: n.id, type: n.type, position: n.position,
      data: { label: n.label, config: (n.config || {}) as CanvasNodeData["config"] },
    })));
    setEdges(template.edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      type: "smoothstep", animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#0088cc" },
    })));
    setNodeStatuses({});
  }, [template, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(
      { ...params, type: "smoothstep", animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: "#0088cc" } }, eds
    )), [setEdges]
  );

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    const type = event.dataTransfer.getData("application/reactflow");
    if (!type || !wrapperRef.current || !ctx) return;
    const def = ctx.nodeTypes.get(type);
    const rect = wrapperRef.current.getBoundingClientRect();
    const newNode: Node<CanvasNodeData> = {
      id: `${type}_${Date.now()}`, type,
      position: { x: event.clientX - rect.left, y: event.clientY - rect.top },
      data: { label: def?.label || "节点", config: def?.getDefaultConfig() || {} },
    };
    setNodes((nds) => [...nds, newNode]);
  }, [setNodes, ctx]);

  const executeWorkflow = useCallback(async () => {
    if (!ctx || nodes.length === 0) return;
    setIsExecuting(true);
    onStatus("executing");
    setNodeStatuses({});
    try {
      const workflowData = ctx.workflow.fromCanvas(nodes, edges);
      const result = await ctx.workflow.execute(workflowData, inputData);
      onResult(result as unknown as Record<string, unknown>);
      onStatus("done");
      if (result?.outputs) {
        const statuses: Record<string, string> = {};
        for (const [nid, out] of Object.entries(result.outputs)) {
          statuses[nid] = out && typeof out === "object" && "error" in (out as object) ? "error" : "done";
        }
        setNodeStatuses(statuses);
      }
    } catch (e) {
      onResult({ error: String(e) });
      onStatus("error");
    }
    setIsExecuting(false);
  }, [nodes, edges, ctx, inputData, onResult, onStatus]);

  const submitHitl = useCallback(async (approved: boolean) => {
    if (!hitlPrompt || !ctx) return;
    try {
      await ctx.backend.invoke("hitl_reply", {
        run_id: hitlPrompt.runId, node_id: hitlPrompt.nodeId,
        answer: approved ? "approved" : "rejected",
      });
    } catch (e) { console.error("HITL reply failed:", e); }
    setHitlPrompt(null);
  }, [hitlPrompt, ctx]);

  useEffect(() => {
    if (!ctx) return;
    const handler = (data: any) => {
      if (data?.run_id && data?.node_id) {
        setHitlPrompt({ runId: data.run_id, nodeId: data.node_id, prompt: data.prompt || "请审批" });
      }
    };
    const unsub = ctx.on("hitl:request", handler);
    return () => { if (typeof unsub === "function") unsub(); };
  }, [ctx]);

  if (!ctx) return <div style={{ padding: 24, color: "#666" }}>正在初始化...</div>;

  const statusColor = (s: string) => s === "done" ? "#00cc88" : s === "error" ? "#cc0000" : s === "running" ? "#ffaa00" : "#ccc";

  return (
    <div style={{ width: "100%", height: "100%", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }} ref={wrapperRef}>
        <ReactFlow
          nodes={nodes.map((n) => ({ ...n, style: nodeStatuses[n.id] ? { border: `2px solid ${statusColor(nodeStatuses[n.id])}` } : undefined }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}
          onNodeClick={(_: React.MouseEvent, node: Node<CanvasNodeData>) => setSelectedNode(node)}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} />
          <Controls />
          <MiniMap zoomable pannable maskColor="rgba(16,22,26,0.3)" />
          <Panel position="top-right"><NodePalette /></Panel>
          <Panel position="top-left">
            <button onClick={executeWorkflow} disabled={isExecuting || nodes.length === 0}
              style={{
                padding: "10px 20px", background: isExecuting ? "#ccc" : "#00cc88",
                color: "#fff", border: "none", borderRadius: 6, cursor: isExecuting ? "not-allowed" : "pointer",
                fontSize: 15, fontWeight: "bold", boxShadow: "0 2px 8px rgba(0,204,136,0.3)",
              }}>
              {isExecuting ? "⏳ 执行中..." : "▶ 执行工作流"}
            </button>
          </Panel>
          {template && (
            <Panel position="bottom-center">
              <div style={{ display: "flex", gap: 8, alignItems: "center", background: "rgba(255,255,255,0.95)", padding: "8px 16px", borderRadius: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
                <span style={{ fontSize: 13, color: "#666", fontWeight: 600 }}>{template.inputLabel}:</span>
                <input type="text" value={inputData} onChange={(e) => setInputData(e.target.value)}
                  style={{ width: 450, padding: "6px 10px", border: "1px solid #ddd", borderRadius: 4, fontSize: 13 }} />
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>

      {hitlPrompt && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: 28, maxWidth: 520, boxShadow: "0 8px 32px rgba(0,0,0,0.3)" }}>
            <h3 style={{ marginBottom: 12 }}>🤔 人工审核</h3>
            <p style={{ color: "#333", marginBottom: 24, lineHeight: 1.6 }}>{hitlPrompt.prompt}</p>
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button onClick={() => submitHitl(false)} style={{ padding: "10px 24px", background: "#cc4444", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 }}>拒绝</button>
              <button onClick={() => submitHitl(true)} style={{ padding: "10px 24px", background: "#00cc88", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 }}>批准</button>
            </div>
          </div>
        </div>
      )}

      {selectedNode && (
        <div style={{ width: 300, background: "#fff", borderLeft: "1px solid #ddd", padding: 16, overflowY: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, margin: 0 }}>节点属性</h3>
            <button onClick={() => setSelectedNode(null)} style={{ border: "none", background: "none", cursor: "pointer", fontSize: 18, color: "#999" }}>×</button>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>标签</label>
            <input type="text" value={selectedNode.data.label || ""}
              onChange={(e) => {
                setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, label: e.target.value } } : n));
                setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, label: e.target.value } });
              }}
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 4 }} />
          </div>
          {selectedNode.type === "agent" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>Agent类型</label>
                <select value={(selectedNode.data.config?.agent_type as string) || "specialist"}
                  onChange={(e) => { const c = { ...selectedNode.data.config, agent_type: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: c } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: c } }); }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}>
                  <option value="specialist">Specialist</option>
                  <option value="leader">Leader</option>
                </select>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>模型</label>
                <select value={(selectedNode.data.config?.model as string) || "deepseek-chat"}
                  onChange={(e) => { const c = { ...selectedNode.data.config, model: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: c } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: c } }); }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}>
                  <option value="deepseek-chat">DeepSeek Chat</option>
                  <option value="deepseek-coder">DeepSeek Coder</option>
                </select>
              </div>
            </>
          )}
          {selectedNode.type === "tool" && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>工具名称</label>
              <select value={(selectedNode.data.config?.tool_name as string) || ""}
                  onChange={(e) => { const c = { ...selectedNode.data.config, tool_name: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: c } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: c } }); }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}>
                <option value="read_file">read_file</option>
                <option value="write_file">write_file</option>
                <option value="web_search">web_search</option>
                <option value="list_dir">list_dir</option>
                <option value="http_get">http_get</option>
                <option value="python_exec">python_exec</option>
                <option value="terminal">terminal</option>
              </select>
            </div>
          )}
          {selectedNode.type === "hitl" && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>提示语</label>
              <input type="text" value={(selectedNode.data.config?.prompt as string) || ""}
                onChange={(e) => { const c = { ...selectedNode.data.config, prompt: e.target.value };
                  setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: c } } : n));
                  setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: c } }); }}
                style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FusionCanvas;
