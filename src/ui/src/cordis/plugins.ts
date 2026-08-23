import type { Context } from "@deepseek-ai/cordis";

export function registerToolPlugins(ctx: Context): void {
  ctx.tools.register(
    "read_file",
    { name: "read_file", description: "读取文件", parameters: { path: { type: "string" } } },
    async (params) => {
      return ctx.backend.invoke("execute_tool", {
        tool_name: "read_file",
        parameters: params,
      });
    }
  );

  ctx.tools.register(
    "write_file",
    {
      name: "write_file",
      description: "写入文件",
      parameters: { path: { type: "string" }, content: { type: "string" } },
    },
    async (params) => {
      return ctx.backend.invoke("execute_tool", {
        tool_name: "write_file",
        parameters: params,
      });
    }
  );

  ctx.tools.register(
    "web_search",
    { name: "web_search", description: "网页搜索", parameters: { query: { type: "string" } } },
    async (params) => {
      return ctx.backend.invoke("execute_tool", {
        tool_name: "web_search",
        parameters: params,
      });
    }
  );

  ctx.tools.register(
    "terminal",
    { name: "terminal", description: "执行终端命令", parameters: { command: { type: "string" } } },
    async (params) => {
      return ctx.backend.invoke("execute_tool", {
        tool_name: "terminal",
        parameters: params,
      });
    }
  );
}

export function registerLLMAdapter(ctx: Context): void {
  ctx.llm.registerAdapter("backend", async (messages, options) => {
    const result = await ctx.backend.invoke<{ content: string }>("chat", {
      message: messages[messages.length - 1]?.content || "",
      messages,
      options,
    });
    return { content: result.content || JSON.stringify(result) };
  });
}