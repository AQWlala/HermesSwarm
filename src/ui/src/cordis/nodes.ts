import type { Context } from "@deepseek-ai/cordis";
import type { NodeTypeDef, NodeConfig, NodeExecutionResult } from "./types";

const inputNode: NodeTypeDef = {
  type: "input",
  label: "输入",
  icon: "📥",
  color: "#4caf50",
  getDefaultConfig: () => ({ schema: {} }),
  execute: async (input: unknown): Promise<NodeExecutionResult> => ({
    output: input,
    metadata: { passthrough: true },
  }),
};

const outputNode: NodeTypeDef = {
  type: "output",
  label: "输出",
  icon: "📤",
  color: "#607d8b",
  getDefaultConfig: () => ({ format: "json" }),
  execute: async (input: unknown, config: NodeConfig): Promise<NodeExecutionResult> => {
    if (config.format === "text") {
      return { output: String(input), metadata: { format: "text" } };
    }
    return { output: input, metadata: { format: config.format || "json" } };
  },
};

const agentNode: NodeTypeDef = {
  type: "agent",
  label: "智能体",
  icon: "🤖",
  color: "#0088cc",
  getDefaultConfig: () => ({
    agent_type: "specialist",
    model: "gpt-4",
    temperature: 0.7,
    tools: [],
  }),
  execute: async (
    input: unknown,
    config: NodeConfig,
    ctx: Context
  ): Promise<NodeExecutionResult> => {
    const messages = [
      { role: "system" as const, content: `You are a ${config.agent_type || "specialist"} agent.` },
      { role: "user" as const, content: String(input) },
    ];
    const response = await ctx.llm.chat(messages, {
      model: config.model,
      temperature: config.temperature,
    });
    return {
      output: response.content,
      metadata: {
        agent_type: config.agent_type,
        model: config.model,
        usage: response.usage,
      },
    };
  },
};

const toolNode: NodeTypeDef = {
  type: "tool",
  label: "工具",
  icon: "🔧",
  color: "#ff9800",
  getDefaultConfig: () => ({ tool_name: "", parameters: {} }),
  execute: async (
    input: unknown,
    config: NodeConfig,
    ctx: Context
  ): Promise<NodeExecutionResult> => {
    const toolName = config.tool_name || "";
    if (!toolName) {
      return { output: { error: "No tool specified" }, metadata: {} };
    }
    const params = { ...(config.parameters || {}), input };
    const result = await ctx.tools.execute(toolName, params);
    return { output: result, metadata: { tool: toolName } };
  },
};

const conditionNode: NodeTypeDef = {
  type: "condition",
  label: "条件",
  icon: "🔀",
  color: "#9c27b0",
  getDefaultConfig: () => ({ expression: "true" }),
  execute: async (input: unknown, config: NodeConfig): Promise<NodeExecutionResult> => {
    const expr = config.expression || "true";
    let result = true;
    try {
      result = Boolean(new Function("data", "input", `return ${expr}`)(input, input));
    } catch {
      result = true;
    }
    return { output: { condition: expr, result }, metadata: { branch: result ? "true" : "false" } };
  },
};

const hitlNode: NodeTypeDef = {
  type: "hitl",
  label: "人工审批",
  icon: "👤",
  color: "#e91e63",
  getDefaultConfig: () => ({ prompt: "请审批", timeout: 300 }),
  execute: async (
    input: unknown,
    config: NodeConfig,
    ctx: Context
  ): Promise<NodeExecutionResult> => {
    const prompt = config.prompt || `请审批: ${String(input).slice(0, 200)}`;
    const result = await ctx.backend.invoke<{ approved: boolean; reply: string }>("hitl_request", {
      prompt,
      input: String(input).slice(0, 500),
    });
    return {
      output: { approved: result.approved, reply: result.reply, input },
      metadata: { hitl: true, prompt },
    };
  },
};

const allNodePlugins = [inputNode, outputNode, agentNode, toolNode, conditionNode, hitlNode];

export function registerNodePlugins(ctx: Context): void {
  for (const def of allNodePlugins) {
    ctx.nodeTypes.register(def);
  }
}

export { inputNode, outputNode, agentNode, toolNode, conditionNode, hitlNode };