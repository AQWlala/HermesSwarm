"""用户视角完整验证"""
import httpx, json, sys

API = "http://127.0.0.1:8765/api"

def main():
    # 1. 后端API健康检查
    print("=" * 60)
    print("  1. 后端API健康检查")
    print("=" * 60)
    r = httpx.get(f"{API}/health", timeout=10)
    health = r.json()
    print(f"  status: {health['status']}")
    engine = health.get("engine", {})
    print(f"  initialized: {engine.get('initialized')}")
    print(f"  tools_count: {engine.get('tools_count')}")
    print(f"  skills_count: {engine.get('skills_count')}")
    print(f"  evolution_enabled: {engine.get('evolution_enabled')}")

    # 2. 工具列表
    print("\n" + "=" * 60)
    print("  2. 可用工具")
    print("=" * 60)
    r = httpx.get(f"{API}/tools", timeout=10)
    tools = r.json().get("tools", [])
    for t in tools:
        print(f"  - {t['name']}: {t['description']}")

    # 3. 执行简单对话工作流
    print("\n" + "=" * 60)
    print("  3. 简单对话工作流")
    print("=" * 60)
    workflow = {
        "name": "对话测试",
        "nodes": [
            {"id": "input", "type": "input", "label": "输入", "position": {"x": 0, "y": 0}},
            {"id": "agent", "type": "agent", "label": "AI助手", "position": {"x": 200, "y": 0},
             "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
            {"id": "output", "type": "output", "label": "输出", "position": {"x": 400, "y": 0}},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "output"},
        ],
    }
    r = httpx.post(
        f"{API}/execute_workflow",
        json={"workflow_json": json.dumps(workflow), "input_data": "用一句话介绍AI智能体"},
        timeout=60,
    )
    result = json.loads(r.json()["result"])
    print(f"  Status: {result['status']}")
    agent_out = result["outputs"].get("agent", {})
    if isinstance(agent_out, dict):
        output_text = agent_out.get("output", "(无)")
        print(f"  Agent输出: {output_text[:500]}")
    else:
        print(f"  Agent输出: {str(agent_out)[:500]}")

    # 4. 内容生产工作流
    print("\n" + "=" * 60)
    print("  4. 内容生产工作流(多Agent并行)")
    print("=" * 60)
    workflow2 = {
        "name": "内容生产",
        "nodes": [
            {"id": "input", "type": "input", "label": "主题", "position": {"x": 0, "y": 200}},
            {"id": "agent1", "type": "agent", "label": "选题分析", "position": {"x": 200, "y": 100},
             "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
            {"id": "agent2", "type": "agent", "label": "内容写作", "position": {"x": 400, "y": 100},
             "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
            {"id": "agent3", "type": "agent", "label": "SEO优化", "position": {"x": 400, "y": 250},
             "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
            {"id": "output", "type": "output", "label": "输出", "position": {"x": 600, "y": 200}},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "agent1"},
            {"id": "e2", "source": "agent1", "target": "agent2"},
            {"id": "e3", "source": "agent1", "target": "agent3"},
            {"id": "e4", "source": "agent2", "target": "output"},
            {"id": "e5", "source": "agent3", "target": "output"},
        ],
    }
    r = httpx.post(
        f"{API}/execute_workflow",
        json={"workflow_json": json.dumps(workflow2), "input_data": "AI编程助手的商业价值"},
        timeout=120,
    )
    result2 = json.loads(r.json()["result"])
    print(f"  Status: {result2['status']}")
    print(f"  拓扑层级: {result2.get('layers', [])}")
    for nid, out in result2["outputs"].items():
        if isinstance(out, dict) and "output" in out:
            print(f"  [{nid}] {out.get('agent', '?')}: {str(out['output'])[:200]}")
        elif isinstance(out, dict) and "error" in out:
            print(f"  [{nid}] ERROR: {out['error'][:200]}")
        else:
            print(f"  [{nid}] {str(out)[:200]}")

    # 5. 工具调用
    print("\n" + "=" * 60)
    print("  5. 工具调用(read_file)")
    print("=" * 60)
    r = httpx.post(
        f"{API}/execute_tool",
        json={"tool_name": "read_file", "parameters": {"path": "README.md"}},
        timeout=10,
    )
    print(f"  结果: {str(r.json().get('result', ''))[:300]}")

    print("\n" + "=" * 60)
    print("  验证完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()