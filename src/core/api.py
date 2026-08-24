"""FastAPI HTTP服务器 - 供前端开发模式调用

Tauri生产模式用IPC，开发模式用HTTP降级
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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


class SkillDevStartRequest(BaseModel):
    skill_name: str
    skill_description: str


class SkillDevResumeRequest(BaseModel):
    pipeline_id: str


class SkillDevPauseRequest(BaseModel):
    pipeline_id: str


class OneshotRequest(BaseModel):
    prompt: str
    template: str = ""
    system: str = ""


class MCPConnectRequest(BaseModel):
    name: str
    command: str = ""
    args: list[str] = []
    transport: str = "stdio"


class MCPCallToolRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


class SymphonyRecordRequest(BaseModel):
    plan_id: str
    outcome: str
    selected_edges: list[str] = []
    failed_edges: list[str] = []
    failure_attribution: str = ""


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

    # v0.7.0: WebSocket流式事件
    @app.websocket("/ws/events")
    async def ws_events(ws: WebSocket):
        engine = await get_engine()
        if not engine._websocket:
            await ws.close()
            return
        await engine._websocket.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except Exception:
                    pass
        except WebSocketDisconnect:
            engine._websocket.disconnect(ws)

    @app.get("/api/websocket/status")
    async def ws_status():
        engine = await get_engine()
        if engine._websocket:
            return engine._websocket.get_status()
        return {"connections": 0}

    # v0.7.0: Learning Graph可视化
    @app.get("/api/curator/learning_graph")
    async def learning_graph():
        engine = await get_engine()
        if not engine._evolution or not engine._evolution.curator:
            return {"nodes": [], "edges": [], "stats": {}}
        lg = engine._evolution.curator.learning_graph
        nodes = []
        for skill_id, node in lg.nodes.items():
            skill = engine._skill_registry.skills.get(skill_id) if engine._skill_registry else None
            nodes.append({
                "id": skill_id,
                "label": skill.name if skill else skill_id,
                "use_count": node.use_count,
                "success_rate": node.success_rate,
                "related": node.related,
                "memory_links": node.memory_links,
                "state": skill.usage.state.value if skill else "unknown",
            })
        edges = []
        for node_data in nodes:
            for rel in node_data["related"]:
                edges.append({"source": node_data["id"], "target": rel, "weight": 1.0, "type": "related"})
            for mem in node_data["memory_links"]:
                edges.append({"source": node_data["id"], "target": mem, "weight": 0.8, "type": "memory"})
        stats = lg.get_stats()
        state_counts = {}
        for n in nodes:
            state_counts[n["state"]] = state_counts.get(n["state"], 0) + 1
        stats["active_nodes"] = state_counts.get("active", 0)
        stats["stale_nodes"] = state_counts.get("stale", 0)
        stats["archived_nodes"] = state_counts.get("archived", 0)
        return {"nodes": nodes, "edges": edges, "stats": stats}

    # v0.7.0: SkillDev流水线端点
    @app.get("/api/skilldev/pipelines")
    async def skilldev_list():
        engine = await get_engine()
        if engine._skilldev:
            return {"pipelines": engine._skilldev.list_pipelines()}
        return {"pipelines": []}

    @app.get("/api/skilldev/state")
    async def skilldev_state(id: str):
        engine = await get_engine()
        if engine._skilldev:
            state = engine._skilldev.get_state(id)
            if state:
                return state.to_dict()
        return {"error": "pipeline not found"}

    @app.post("/api/skilldev/start")
    async def skilldev_start(req: SkillDevStartRequest):
        engine = await get_engine()
        if engine._skilldev:
            state = await engine._skilldev.start(req.skill_name, req.skill_description)
            return {"pipeline_id": state.pipeline_id, "stage": state.stage.value, "suspended": state.suspended}
        return {"error": "skilldev not initialized"}

    @app.post("/api/skilldev/resume")
    async def skilldev_resume(req: SkillDevResumeRequest):
        engine = await get_engine()
        if engine._skilldev:
            state = await engine._skilldev.resume(req.pipeline_id)
            if state:
                return {"pipeline_id": state.pipeline_id, "stage": state.stage.value, "suspended": state.suspended}
        return {"error": "pipeline not found"}

    @app.post("/api/skilldev/pause")
    async def skilldev_pause(req: SkillDevPauseRequest):
        engine = await get_engine()
        if engine._skilldev:
            success = await engine._skilldev.pause(req.pipeline_id)
            return {"success": success}
        return {"success": False}

    # v0.7.0: Oneshot无状态LLM调用
    @app.post("/api/oneshot")
    async def oneshot(req: OneshotRequest):
        engine = await get_engine()
        from src.llm.oneshot import OneshotCaller
        caller = OneshotCaller(llm=engine._llm)
        prompt = req.prompt
        if req.template:
            prompt = f"{req.template}: {req.prompt}"
        result = await caller.call(prompt, system=req.system)
        return {"result": result}

    # v0.7.0: MCP客户端端点
    @app.get("/api/mcp/status")
    async def mcp_status():
        engine = await get_engine()
        if engine._mcp_client:
            return engine._mcp_client.get_status()
        return {"servers": [], "connected": [], "tools": 0}

    @app.get("/api/mcp/tools")
    async def mcp_tools():
        engine = await get_engine()
        if engine._mcp_client:
            return {"tools": engine._mcp_client.get_tools()}
        return {"tools": []}

    @app.post("/api/mcp/connect")
    async def mcp_connect(req: MCPConnectRequest):
        engine = await get_engine()
        if engine._mcp_client:
            from src.tools.mcp_client import MCPServerConfig
            config = MCPServerConfig(name=req.name, command=req.command, args=req.args, transport=req.transport)
            engine._mcp_client.register_server(config)
            success = await engine._mcp_client.connect(req.name)
            return {"success": success, "tools": engine._mcp_client.get_tools()}
        return {"success": False}

    @app.post("/api/mcp/call")
    async def mcp_call(req: MCPCallToolRequest):
        engine = await get_engine()
        if engine._mcp_client:
            result = await engine._mcp_client.call_tool(req.tool_name, req.arguments)
            return {"result": result}
        return {"error": "mcp not initialized"}

    # v0.7.0: Symphony图演进端点
    @app.get("/api/symphony/stats")
    async def symphony_stats():
        engine = await get_engine()
        if engine._symphony:
            return engine._symphony.get_graph_stats()
        return {}

    @app.get("/api/symphony/weights")
    async def symphony_weights():
        engine = await get_engine()
        if engine._symphony:
            return {"weights": engine._symphony.get_effective_weights()}
        return {"weights": {}}

    @app.post("/api/symphony/record")
    async def symphony_record(req: SymphonyRecordRequest):
        engine = await get_engine()
        if engine._symphony:
            from src.agents.symphony_evolution import PlanOutcome
            outcome = PlanOutcome(
                plan_id=req.plan_id,
                outcome=req.outcome,
                selected_edges=req.selected_edges,
                failed_edges=req.failed_edges,
                failure_attribution=req.failure_attribution,
            )
            engine._symphony.record_plan_outcome(outcome)
            return {"success": True}
        return {"success": False}

    # v0.7.0: 项目规范端点
    @app.get("/api/project/spec")
    async def project_spec():
        engine = await get_engine()
        if engine._project_context:
            spec = engine._project_context.discover_spec()
            if spec:
                return {"path": str(spec[1]), "content": spec[0][:5000]}
            return {"path": None, "content": None}
        return {"path": None, "content": None}

    # v0.7.0: Warm Pool端点
    @app.get("/api/warm_pool/status")
    async def warm_pool_status():
        engine = await get_engine()
        if engine._warm_pool:
            return {
                "max_size": engine._warm_pool.max_size,
                "current_size": len(engine._warm_pool._slots),
                "prewarm_enabled": engine._warm_pool.prewarm_enabled,
            }
        return {}

    # v0.7.0: 凭证池端点
    @app.get("/api/credentials/status")
    async def credentials_status():
        from src.llm.credential_pool import CredentialPool
        pool = CredentialPool()
        pool.load_from_env()
        return pool.get_status()

    return app


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765):
    """启动API服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
