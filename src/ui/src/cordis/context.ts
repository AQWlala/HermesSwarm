import { Context, Service } from "@deepseek-ai/cordis";
import type {
  NodeTypeDef,
  ToolSchema,
  ToolResult,
  LLMMessage,
  LLMResponse,
  WorkflowData,
  ExecutionResult,

} from "./types";

class NodeRegistry extends Service {
  private types = new Map<string, NodeTypeDef>();

  constructor(ctx: Context) {
    super(ctx, "nodeTypes");
  }

  register(def: NodeTypeDef) {
    this.types.set(def.type, def);
    this.ctx.emit("node/registered", def.type, def);
  }

  unregister(type: string) {
    this.types.delete(type);
    this.ctx.emit("node/unregistered", type);
  }

  get(type: string): NodeTypeDef | undefined {
    return this.types.get(type);
  }

  list(): NodeTypeDef[] {
    return Array.from(this.types.values());
  }
}

class ToolService extends Service {
  private tools = new Map<
    string,
    { schema: ToolSchema; handler: (params: Record<string, unknown>) => Promise<ToolResult> }
  >();

  constructor(ctx: Context) {
    super(ctx, "tools");
  }

  register(
    name: string,
    schema: ToolSchema,
    handler: (params: Record<string, unknown>) => Promise<ToolResult>
  ) {
    this.tools.set(name, { schema, handler });
    this.ctx.emit("tool/registered", name, schema);
  }

  async execute(name: string, params: Record<string, unknown>): Promise<ToolResult> {
    const tool = this.tools.get(name);
    if (!tool) throw new Error(`Tool ${name} not found`);
    return tool.handler(params);
  }

  list(): ToolSchema[] {
    return Array.from(this.tools.values()).map((t) => t.schema);
  }
}

class LLMService extends Service {
  private adapters = new Map<
    string,
    (messages: LLMMessage[], options?: Record<string, unknown>) => Promise<LLMResponse>
  >();
  private defaultAdapter = "backend";

  constructor(ctx: Context) {
    super(ctx, "llm");
  }

  registerAdapter(
    name: string,
    adapter: (messages: LLMMessage[], options?: Record<string, unknown>) => Promise<LLMResponse>
  ) {
    this.adapters.set(name, adapter);
  }

  async chat(messages: LLMMessage[], options?: Record<string, unknown>): Promise<LLMResponse> {
    const adapterName = (options?.adapter as string) || this.defaultAdapter;
    const adapter = this.adapters.get(adapterName);
    if (!adapter) throw new Error(`LLM adapter ${adapterName} not found`);
    this.ctx.emit("llm/request", messages);
    const response = await adapter(messages, options);
    this.ctx.emit("llm/response", response);
    return response;
  }
}

class WorkflowService extends Service {
  constructor(ctx: Context) {
    super(ctx, "workflow");
  }

  async execute(data: WorkflowData, input?: unknown): Promise<ExecutionResult> {
    this.ctx.emit("workflow/started", data.name);
    try {
      const result = await this.ctx.backend.invoke<ExecutionResult>("execute_workflow", {
        workflowJson: JSON.stringify(data),
        inputData: input ? String(input) : "",
      });
      this.ctx.emit("workflow/completed", result);
      return result;
    } catch (e) {
      const error = e instanceof Error ? e : new Error(String(e));
      this.ctx.emit("workflow/error", error);
      throw error;
    }
  }

  fromCanvas(
    nodes: import("reactflow").Node<import("./types").CanvasNodeData>[],
    edges: import("reactflow").Edge[]
  ): WorkflowData {
    return {
      name: "HermesSwarm Workflow",
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type || "default",
        label: n.data.label,
        position: n.position,
        config: n.data.config || {},
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle || undefined,
        targetHandle: e.targetHandle || undefined,
        condition: (e.label as string) || undefined,
      })),
    };
  }
}

class BackendService extends Service {
  constructor(ctx: Context) {
    super(ctx, "backend");
  }

  async invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T> {
    const isTauri =
      typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
    if (isTauri) {
      const { invoke: tauriInvoke } = await import("@tauri-apps/api/tauri");
      return tauriInvoke<T>(cmd, args);
    }
    const res = await fetch(`http://localhost:8765/api/${cmd}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args || {}),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json() as Promise<T>;
  }
}

export async function createAppContext(): Promise<Context> {
  const ctx = new Context();
  await ctx.plugin(NodeRegistry);
  await ctx.plugin(ToolService);
  await ctx.plugin(LLMService);
  await ctx.plugin(BackendService);
  await ctx.plugin(WorkflowService);
  return ctx;
}

export { NodeRegistry, ToolService, LLMService, WorkflowService, BackendService };