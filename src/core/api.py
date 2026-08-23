"""FastAPI HTTP服务器 - 供前端开发模式调用

Tauri生产模式用IPC，开发模式用HTTP降级
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import FusionConfig
from src.core.engine import FusionEngine


class WorkflowRequest(BaseModel):
    workflow_json: str = ""
    input_data: str = ""


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class HitlReplyRequest(BaseModel):
    run_id: str
    node_id: str
    answer: str


class ExecuteToolRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any] = {}


_engine: FusionEngine | None = None


async def get_engine() -> FusionEngine:
    global _engine
    if _engine is None:
        config = FusionConfig()
        _engine = FusionEngine(config=config)
        await _engine.initialize()
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if _engine:
        await _engine.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="HermesSwarm API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "tauri://localhost"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        engine = await get_engine()
        return {"status": "ok", "engine": engine.get_status()}

    @app.post("/api/greet")
    async def greet(name: str = "HermesSwarm"):
        return {"result": f"Hello {name}, welcome to HermesSwarm!"}

    @app.post("/api/execute_workflow")
    async def execute_workflow(req: WorkflowRequest):
        engine = await get_engine()
        workflow_data = json.loads(req.workflow_json) if req.workflow_json else {}
        input_data = req.input_data or None
        result = await engine.execute_workflow(workflow_data, input_data)
        return {"result": json.dumps(result, default=str, ensure_ascii=False)}

    @app.post("/api/start_python_backend")
    async def start_backend():
        return {"result": "Python backend already running on port 8765"}

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        engine = await get_engine()
        result = await engine.chat(req.message, req.session_id)
        return {"result": result}

    @app.post("/api/hitl_request")
    async def hitl_request(prompt: str = "", input: str = ""):
        return {"approved": True, "reply": "auto-approved", "prompt": prompt}

    @app.post("/api/hitl_reply")
    async def hitl_reply(req: HitlReplyRequest):
        engine = await get_engine()
        success = engine.submit_hitl_reply(req.run_id, req.node_id, req.answer)
        return {"success": success}

    @app.get("/api/tools")
    async def list_tools():
        engine = await get_engine()
        return {"tools": engine.get_tools()}

    @app.post("/api/execute_tool")
    async def execute_tool(req: ExecuteToolRequest):
        engine = await get_engine()
        if engine._tool_registry:
            result = await engine._tool_registry.execute(
                req.tool_name, req.parameters, req.parameters
            )
            return {"result": result}
        return {"error": "Tool registry not initialized"}

    return app


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """启动API服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
