import { useEffect, useState } from "react";
import type { Context } from "@deepseek-ai/cordis";
import { createAppContext } from "./context";
import { registerNodePlugins } from "./nodes";
import { registerToolPlugins, registerLLMAdapter } from "./plugins";

let _ctx: Context | null = null;

export async function getCordisContext(): Promise<Context> {
  if (_ctx) return _ctx;
  _ctx = await createAppContext();
  registerNodePlugins(_ctx);
  registerToolPlugins(_ctx);
  registerLLMAdapter(_ctx);
  return _ctx;
}

export function useCordis(): Context | null {
  const [ctx, setCtx] = useState<Context | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCordisContext().then((c) => {
      if (!cancelled) setCtx(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return ctx;
}