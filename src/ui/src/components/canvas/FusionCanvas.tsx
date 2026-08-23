import React, { useCallback, useRef, useState, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  Connection,
  Edge,
  Node,
  Panel,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  NodeTypes,
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

const nodeTypes: NodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  condition: ConditionNode,
  hitl: HitlNode,
  input: InputNode,
  output: OutputNode,
};

const FusionCanvas: React.FC = () => {
  const ctx = useCordis();
  const [nodes, setNodes, onNodesChange] = useNodesState<CanvasNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node<CanvasNodeData> | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [execResult, setExecResult] = useState<string | null>(null);
  const [inputData, setInputData] = useState("请输入工作流的初始数据...");
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, "pending" | "running" | "done" | "error">>({});
  const [hitlPrompt, setHitlPrompt] = useState<{ runId: string; nodeId: string; prompt: string } | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const onConnect = useCallback(
    (params: Connection | Edge) =>
      setEdges((eds) =>
        addEdge(
          { ...params, type: "smoothstep", animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: "#0088cc" } },
          eds
        )
      ),
    [setEdges]
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/reactflow");
      if (!type || !wrapperRef.current || !ctx) return;
      const def = ctx.nodeTypes.get(type);
      const rect = wrapperRef.current.getBoundingClientRect();
      const position = { x: event.clientX - rect.left, y: event.clientY - rect.top };
      const newNode: Node<CanvasNodeData> = {
        id: `${type}_${Date.now()}`,
        type,
        position,
        data: {
          label: def?.label || "节点",
          config: def?.getDefaultConfig() || {},
        },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes, ctx]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<CanvasNodeData>) => setSelectedNode(node), []);

  const executeWorkflow = useCallback(async () => {
    if (!ctx) return;
    setIsExecuting(true);
    setExecResult(null);
    setNodeStatuses({});
    try {
      const workflowData = ctx.workflow.fromCanvas(nodes, edges);
      const result = await ctx.workflow.execute(workflowData, inputData);
      setExecResult(JSON.stringify(result, null, 2));
      if (result?.outputs) {
        const statuses: Record<string, "pending" | "running" | "done" | "error"> = {};
        for (const [nid, out] of Object.entries(result.outputs)) {
          statuses[nid] = out && typeof out === "object" && "error" in out ? "error" : "done";
        }
        setNodeStatuses(statuses);
      }
    } catch (e) {
      setExecResult(`执行失败: ${e}`);
    }
    setIsExecuting(false);
  }, [nodes, edges, ctx, inputData]);

  const submitHitl = useCallback(async (approved: boolean) => {
    if (!hitlPrompt || !ctx) return;
    try {
      await ctx.backend.invoke("hitl_reply", {
        run_id: hitlPrompt.runId,
        node_id: hitlPrompt.nodeId,
        answer: approved ? "approved" : "rejected",
      });
    } catch (e) {
      console.error("HITL reply failed:", e);
    }
    setHitlPrompt(null);
  }, [hitlPrompt, ctx]);

  useEffect(() => {
    if (!ctx) return;
    const handler = (data: any) => {
      if (data?.run_id && data?.node_id) {
        setHitlPrompt({
          runId: data.run_id,
          nodeId: data.node_id,
          prompt: data.prompt || "请审批",
        });
      }
    };
    const unsub = ctx.on("hitl:request", handler);
    return () => { if (typeof unsub === "function") unsub(); };
  }, [ctx]);

  if (!ctx) {
    return <div style={{ padding: 24, color: "#666" }}>正在初始化 Cordis 插件系统...</div>;
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }} ref={wrapperRef}>
        <ReactFlow
          nodes={nodes.map((n) => ({
            ...n,
            style: nodeStatuses[n.id]
              ? {
                  border: nodeStatuses[n.id] === "done" ? "2px solid #00cc88"
                    : nodeStatuses[n.id] === "error" ? "2px solid #cc0000"
                    : nodeStatuses[n.id] === "running" ? "2px solid #ffaa00"
                    : "2px solid #ccc",
                }
              : undefined,
          }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} />
          <Controls />
          <MiniMap zoomable pannable maskColor="rgba(16,22,26,0.3)" />
          <Panel position="top-right">
            <NodePalette />
          </Panel>
          <Panel position="top-left">
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                onClick={executeWorkflow}
                disabled={isExecuting}
                style={{
                  padding: "8px 16px",
                  background: isExecuting ? "#ccc" : "#00cc88",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  cursor: isExecuting ? "not-allowed" : "pointer",
                  fontSize: "14px",
                  fontWeight: "bold",
                }}
              >
                {isExecuting ? "执行中..." : "▶ 执行工作流"}
              </button>
            </div>
          </Panel>
          <Panel position="bottom-center">
            <div style={{ display: "flex", gap: 8, alignItems: "center", background: "rgba(255,255,255,0.9)", padding: "6px 12px", borderRadius: 8 }}>
              <span style={{ fontSize: 12, color: "#666" }}>输入:</span>
              <input
                type="text"
                value={inputData}
                onChange={(e) => setInputData(e.target.value)}
                style={{ width: 400, padding: "4px 8px", border: "1px solid #ddd", borderRadius: 4, fontSize: 13 }}
              />
            </div>
          </Panel>
          {execResult && (
            <Panel position="bottom-left">
              <div
                style={{
                  background: "rgba(255,255,255,0.95)",
                  padding: 12,
                  borderRadius: 8,
                  maxWidth: 500,
                  maxHeight: 300,
                  overflow: "auto",
                  fontSize: 11,
                  fontFamily: "monospace",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                }}
              >
                <div style={{ fontWeight: "bold", marginBottom: 8 }}>执行结果:</div>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{execResult}</pre>
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>

      {hitlPrompt && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{ background: "#fff", borderRadius: 12, padding: 24, maxWidth: 500, boxShadow: "0 8px 32px rgba(0,0,0,0.3)" }}>
            <h3 style={{ marginBottom: 12 }}>🤔 人工审核</h3>
            <p style={{ color: "#333", marginBottom: 20 }}>{hitlPrompt.prompt}</p>
            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button onClick={() => submitHitl(false)} style={{ padding: "8px 20px", background: "#cc4444", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
                拒绝
              </button>
              <button onClick={() => submitHitl(true)} style={{ padding: "8px 20px", background: "#00cc88", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
                批准
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedNode && (
        <div style={{ width: 320, background: "#fff", borderLeft: "1px solid #ddd", padding: 16, overflowY: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, margin: 0 }}>节点属性</h3>
            <button onClick={() => setSelectedNode(null)} style={{ border: "none", background: "none", cursor: "pointer", fontSize: 18, color: "#999" }}>×</button>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>标签</label>
            <input
              type="text"
              value={selectedNode.data.label || ""}
              onChange={(e) => {
                setNodes((nds) =>
                  nds.map((n) => (n.id === selectedNode.id ? { ...n, data: { ...n.data, label: e.target.value } } : n))
                );
                setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, label: e.target.value } });
              }}
              style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 4 }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>类型</label>
            <span style={{ fontSize: 12, color: "#999" }}>{selectedNode.type}</span>
          </div>
          {selectedNode.type === "agent" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>Agent类型</label>
                <select
                  value={selectedNode.data.config?.agent_type || "specialist"}
                  onChange={(e) => {
                    const newConfig = { ...selectedNode.data.config, agent_type: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                  }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
                >
                  <option value="specialist">Specialist</option>
                  <option value="leader">Leader</option>
                </select>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>模型</label>
                <select
                  value={selectedNode.data.config?.model || "deepseek-chat"}
                  onChange={(e) => {
                    const newConfig = { ...selectedNode.data.config, model: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                  }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
                >
                  <option value="deepseek-chat">DeepSeek Chat</option>
                  <option value="deepseek-coder">DeepSeek Coder</option>
                  <option value="gpt-4o-mini">GPT-4o mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                </select>
              </div>
            </>
          )}
          {selectedNode.type === "tool" && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>工具名称</label>
              <input
                type="text"
                value={selectedNode.data.config?.tool_name || ""}
                onChange={(e) => {
                  const newConfig = { ...selectedNode.data.config, tool_name: e.target.value };
                  setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                  setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                }}
                style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
              />
            </div>
          )}
          {selectedNode.type === "hitl" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>提示语</label>
                <input
                  type="text"
                  value={selectedNode.data.config?.prompt || ""}
                  onChange={(e) => {
                    const newConfig = { ...selectedNode.data.config, prompt: e.target.value };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                  }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>超时(秒)</label>
                <input
                  type="number"
                  value={selectedNode.data.config?.timeout || 300}
                  onChange={(e) => {
                    const newConfig = { ...selectedNode.data.config, timeout: parseInt(e.target.value) || 300 };
                    setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                    setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                  }}
                  style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
                />
              </div>
            </>
          )}
          {selectedNode.type === "condition" && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>条件表达式</label>
              <input
                type="text"
                value={selectedNode.data.config?.expression || "true"}
                onChange={(e) => {
                  const newConfig = { ...selectedNode.data.config, expression: e.target.value };
                  setNodes((nds) => nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, config: newConfig } } : n));
                  setSelectedNode({ ...selectedNode, data: { ...selectedNode.data, config: newConfig } });
                }}
                style={{ width: "100%", padding: 6, border: "1px solid #ddd", borderRadius: 4 }}
              />
            </div>
          )}
          <div style={{ marginTop: 16 }}>
            <label style={{ display: "block", fontSize: 12, color: "#666", marginBottom: 4 }}>原始配置</label>
            <pre style={{ fontSize: 11, color: "#999", background: "#f5f5f5", padding: 8, borderRadius: 4, maxHeight: 200, overflow: "auto" }}>
              {JSON.stringify(selectedNode.data.config, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default FusionCanvas;
