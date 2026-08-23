"""测试PyInstaller打包的后端exe"""
import subprocess, time, socket, os, httpx, json

env = os.environ.copy()
env["DEEPSEEK_API_KEY"] = "sk-bc7e2fe1c7f24269a3d2382c1bf9c06e"
env["PORT"] = "8766"

print("启动后端exe...")
p = subprocess.Popen(
    [r"D:\tmp\hemres jinhua\HermesSwarm\dist\hermesswarm-backend.exe"],
    env=env,
    creationflags=0x00000008,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

time.sleep(12)

s = socket.socket()
s.settimeout(2)
r = s.connect_ex(("127.0.0.1", 8766))
s.close()

if r == 0:
    print("✓ 后端exe启动成功，端口8766监听中")
    resp = httpx.get("http://127.0.0.1:8766/api/health", timeout=5)
    health = resp.json()
    print(f"  status: {health['status']}")
    engine = health.get("engine", {})
    print(f"  tools_count: {engine.get('tools_count')}")
    print(f"  evolution_enabled: {engine.get('evolution_enabled')}")

    print("\n测试工作流执行...")
    workflow = {
        "name": "test",
        "nodes": [
            {"id": "input", "type": "input", "label": "输入", "position": {"x": 0, "y": 0}},
            {"id": "agent", "type": "agent", "label": "AI", "position": {"x": 200, "y": 0},
             "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
            {"id": "output", "type": "output", "label": "输出", "position": {"x": 400, "y": 0}},
        ],
        "edges": [
            {"id": "e1", "source": "input", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "output"},
        ],
    }
    resp = httpx.post(
        "http://127.0.0.1:8766/api/execute_workflow",
        json={"workflow_json": json.dumps(workflow), "input_data": "你好，用一句话自我介绍"},
        timeout=60,
    )
    result = json.loads(resp.json()["result"])
    print(f"  Status: {result['status']}")
    agent_out = result["outputs"].get("agent", {})
    if isinstance(agent_out, dict):
        print(f"  Output: {str(agent_out.get('output', ''))[:300]}")
else:
    print(f"✗ 后端exe启动失败 (err={r})")

p.terminate()
print("\n测试完成")