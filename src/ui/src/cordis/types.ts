import type { Context } from "@deepseek-ai/cordis";
import type { Node, Edge } from "reactflow";

export interface NodeConfig {
  agent_type?: string;
  model?: string;
  temperature?: number;
  tools?: string[];
  tool_name?: string;
  parameters?: Record<string, unknown>;
  expression?: string;
  prompt?: string;
  timeout?: number;
  schema?: Record<string, unknown>;
  format?: string;
  [key: string]: unknown;
}

export interface CanvasNodeData {
  label: string;
  config: NodeConfig;
}

export interface WorkflowNodeDef {
  id: string;
  type: string;
  label: string;
  position: { x: number; y: number };
  config: NodeConfig;
}

export interface WorkflowEdgeDef {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  condition?: string;
}

export interface WorkflowData {
  name: string;
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
}

export interface ExecutionResult {
  run_id: string;
  outputs: Record<string, unknown>;
  status: string;
}

export interface ToolSchema {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolResult {
  [key: string]: unknown;
}

export interface LLMMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  tool_call_id?: string;
  name?: string;
}

export interface LLMResponse {
  content: string;
  tool_calls?: Array<{
    id: string;
    function: { name: string; arguments: string };
  }>;
  usage?: { prompt_tokens: number; completion_tokens: number };
}

export interface NodeExecutionResult {
  output: unknown;
  metadata?: Record<string, unknown>;
}

export type NodeExecuteFn = (
  input: unknown,
  config: NodeConfig,
  ctx: Context
) => Promise<NodeExecutionResult>;

export interface NodeTypeDef {
  type: string;
  label: string;
  icon: string;
  color: string;
  execute: NodeExecuteFn;
  getDefaultConfig: () => NodeConfig;
}

declare module "@deepseek-ai/cordis" {
  interface Context {
    nodeTypes: NodeRegistry;
    tools: ToolService;
    llm: LLMService;
    workflow: WorkflowService;
    backend: BackendService;
  }

  interface Events {
    "node/registered"(type: string, def: NodeTypeDef): void;
    "node/unregistered"(type: string): void;
    "workflow/started"(name: string): void;
    "workflow/completed"(result: ExecutionResult): void;
    "workflow/error"(error: Error): void;
    "tool/registered"(name: string, schema: ToolSchema): void;
    "llm/request"(messages: LLMMessage[]): void;
    "llm/response"(response: LLMResponse): void;
  }
}

import type { Service } from "@deepseek-ai/cordis";

export declare class NodeRegistry extends Service {
  register(def: NodeTypeDef): void;
  unregister(type: string): void;
  get(type: string): NodeTypeDef | undefined;
  list(): NodeTypeDef[];
}

export declare class ToolService extends Service {
  register(name: string, schema: ToolSchema, handler: (params: Record<string, unknown>) => Promise<ToolResult>): void;
  execute(name: string, params: Record<string, unknown>): Promise<ToolResult>;
  list(): ToolSchema[];
}

export declare class LLMService extends Service {
  chat(messages: LLMMessage[], options?: Record<string, unknown>): Promise<LLMResponse>;
  registerAdapter(name: string, adapter: (messages: LLMMessage[], options?: Record<string, unknown>) => Promise<LLMResponse>): void;
}

export declare class WorkflowService extends Service {
  execute(data: WorkflowData, input?: unknown): Promise<ExecutionResult>;
  fromCanvas(nodes: Node<CanvasNodeData>[], edges: Edge[]): WorkflowData;
}

export declare class BackendService extends Service {
  invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}