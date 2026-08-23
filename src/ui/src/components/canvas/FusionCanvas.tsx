import React, { useCallback, useRef, useState } from "react";
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
    try {
      const workflowData = ctx.workflow.fromCanvas(nodes, edges);
      const result = await ctx.workflow.execute(workflowData);
      setExecResult(JSON.stringify(result, null, 2));
    } catch (e) {
      setExecResult(`执行失败: ${e}`);
    }
    setIsExecuting(false);
  }, [nodes, edges, ctx]);

  if (!ctx) {
    return <div style={{ padding: 24, color: "#666" }}>正在初始化 Cordis 插件系统...</div>;
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }} ref={wrapperRef}>
        <ReactFlow
          nodes={nodes}
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
      {selectedNode && (
        <div style={{ width: 300, background: "#fff", borderLeft: "1px solid #ddd", padding: 16, overflowY: "auto" }}>
          <h3 style={{ marginBottom: 12, fontSize: 16 }}>节点属性</h3>
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
          <pre style={{ fontSize: 11, color: "#999", background: "#f5f5f5", padding: 8, borderRadius: 4 }}>
            {JSON.stringify(selectedNode.data.config, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default FusionCanvas;
