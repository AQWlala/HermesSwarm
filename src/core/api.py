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


class SkillDiscoverRequest(BaseModel):
    task: str = ""


class MemoryStoreRequest(BaseModel):
    content: str = ""
    type: str = "long"


class MemorySearchRequest(BaseModel):
    query: str = ""
    limit: int = 10


_engine: FusionEngine | None = None


async def get_engine() -> FusionEngine:
    global _engine
    if _engine is None:
        import os
        config = FusionConfig()
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            config.model.provider = "openai"
            config.model.api_key = api_key
            config.model.api_base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
            config.model.model_name = os.environ.get("LLM_MODEL", "deepseek-chat")
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

    @app.get("/api/skills")
    async def list_skills():
        engine = await get_engine()
        if engine._skill_registry:
            return {"skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "category": s.metadata.category,
                    "tags": s.metadata.tags,
                    "state": s.usage.state.value,
                    "use_count": s.usage.use_count,
                }
                for s in engine._skill_registry.skills.values()
            ], "stats": engine._skill_registry.get_stats()}
        return {"skills": [], "stats": {}}

    @app.post("/api/skills/discover")
    async def discover_skills(req: SkillDiscoverRequest):
        engine = await get_engine()
        if engine._skill_registry:
            skills = engine._skill_registry.discover_skills_for_task(req.task, limit=5)
            return {"skills": [{"id": s.id, "name": s.name, "description": s.description} for s in skills]}
        return {"skills": []}

    @app.post("/api/memory/store")
    async def memory_store(req: MemoryStoreRequest):
        engine = await get_engine()
        if engine._memory and req.content:
            from src.memory.unified import MemoryEntry
            import time
            entry = MemoryEntry(id=f"mem_{int(time.time()*1000)}", content=req.content, type=req.type)
            engine._memory.store(entry)
            return {"success": True, "id": entry.id}
        return {"success": False}

    @app.post("/api/memory/search")
    async def memory_search(req: MemorySearchRequest):
        engine = await get_engine()
        if engine._memory and req.query:
            results = engine._memory.search(req.query, limit=req.limit)
            return {"results": [
                {"id": r.id, "content": r.content[:200], "type": r.type, "score": r.score}
                for r in results
            ]}
        return {"results": []}

    @app.get("/api/curator/status")
    async def curator_status():
        engine = await get_engine()
        if engine._evolution and engine._evolution.curator:
            return engine._evolution.curator.get_status()
        return {"error": "curator not initialized"}

    @app.post("/api/curator/run")
    async def curator_run():
        engine = await get_engine()
        if engine._evolution:
            result = await engine._evolution.run_curator_cycle(llm_adapter=engine._llm)
            return result
        return {"error": "evolution engine not initialized"}

    @app.get("/api/teams")
    async def list_teams():
        return {"teams": []}

    return app


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """启动API服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
