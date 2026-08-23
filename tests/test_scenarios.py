"""HermesSwarm 3个场景验证

场景1: 内容生产 - 并行分支(选题→写作 + SEO优化 + 配图建议) → HITL审核 → 输出
场景2: 数据分析 - 数据读取 → 分析 → 条件分支(正常→报告 / 异常→告警) → 输出
场景3: 代码审查 - 读取代码 → 审查 + 安全检查(并行) → HITL确认 → 输出
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

API = "http://127.0.0.1:8765/api"


SCENARIO_1_CONTENT = {
    "name": "内容生产工作流",
    "nodes": [
        {"id": "input", "type": "input", "label": "主题输入", "position": {"x": 0, "y": 200}},
        {"id": "agent_topic", "type": "agent", "label": "选题分析",
         "position": {"x": 200, "y": 100},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "agent_write", "type": "agent", "label": "内容写作",
         "position": {"x": 400, "y": 100},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "agent_seo", "type": "agent", "label": "SEO优化",
         "position": {"x": 400, "y": 250},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "agent_image", "type": "agent", "label": "配图建议",
         "position": {"x": 400, "y": 400},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "hitl_review", "type": "hitl", "label": "人工审核",
         "position": {"x": 600, "y": 250},
         "config": {"prompt": "请审核内容生产结果", "timeout": 10}},
        {"id": "output", "type": "output", "label": "发布输出",
         "position": {"x": 800, "y": 250}},
    ],
    "edges": [
        {"id": "e1", "source": "input", "target": "agent_topic"},
        {"id": "e2", "source": "agent_topic", "target": "agent_write"},
        {"id": "e3", "source": "agent_topic", "target": "agent_seo"},
        {"id": "e4", "source": "agent_topic", "target": "agent_image"},
        {"id": "e5", "source": "agent_write", "target": "hitl_review"},
        {"id": "e6", "source": "agent_seo", "target": "hitl_review"},
        {"id": "e7", "source": "agent_image", "target": "hitl_review"},
        {"id": "e8", "source": "hitl_review", "target": "output"},
    ],
}

SCENARIO_2_DATA = {
    "name": "数据分析工作流",
    "nodes": [
        {"id": "input", "type": "input", "label": "数据源", "position": {"x": 0, "y": 200}},
        {"id": "tool_read", "type": "tool", "label": "读取数据",
         "position": {"x": 200, "y": 200},
         "config": {"tool_name": "web_search", "parameters": {"query": "sales data"}}},
        {"id": "agent_analyze", "type": "agent", "label": "数据分析",
         "position": {"x": 400, "y": 200},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "condition", "type": "condition", "label": "异常检测",
         "position": {"x": 600, "y": 200},
         "config": {"expression": "true"}},
        {"id": "agent_report", "type": "agent", "label": "生成报告",
         "position": {"x": 800, "y": 100},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "agent_alert", "type": "agent", "label": "发送告警",
         "position": {"x": 800, "y": 300},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "output", "type": "output", "label": "分析结果",
         "position": {"x": 1000, "y": 200}},
    ],
    "edges": [
        {"id": "e1", "source": "input", "target": "tool_read"},
        {"id": "e2", "source": "tool_read", "target": "agent_analyze"},
        {"id": "e3", "source": "agent_analyze", "target": "condition"},
        {"id": "e4", "source": "condition", "target": "agent_report"},
        {"id": "e5", "source": "condition", "target": "agent_alert"},
        {"id": "e6", "source": "agent_report", "target": "output"},
        {"id": "e7", "source": "agent_alert", "target": "output"},
    ],
}

SCENARIO_3_CODE = {
    "name": "代码审查工作流",
    "nodes": [
        {"id": "input", "type": "input", "label": "代码路径", "position": {"x": 0, "y": 200}},
        {"id": "tool_read", "type": "tool", "label": "读取代码",
         "position": {"x": 200, "y": 200},
         "config": {"tool_name": "read_file", "parameters": {"path": "src/core/engine.py"}}},
        {"id": "agent_review", "type": "agent", "label": "代码审查",
         "position": {"x": 400, "y": 100},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "agent_security", "type": "agent", "label": "安全检查",
         "position": {"x": 400, "y": 300},
         "config": {"agent_type": "specialist", "model": "deepseek-chat"}},
        {"id": "hitl_confirm", "type": "hitl", "label": "人工确认",
         "position": {"x": 600, "y": 200},
         "config": {"prompt": "请确认代码审查结果", "timeout": 10}},
        {"id": "output", "type": "output", "label": "审查报告",
         "position": {"x": 800, "y": 200}},
    ],
    "edges": [
        {"id": "e1", "source": "input", "target": "tool_read"},
        {"id": "e2", "source": "tool_read", "target": "agent_review"},
        {"id": "e3", "source": "tool_read", "target": "agent_security"},
        {"id": "e4", "source": "agent_review", "target": "hitl_confirm"},
        {"id": "e5", "source": "agent_security", "target": "hitl_confirm"},
        {"id": "e6", "source": "hitl_confirm", "target": "output"},
    ],
}


async def run_scenario(
    client: httpx.AsyncClient,
    name: str,
    workflow: dict,
    input_data: str,
) -> dict:
    """运行单个场景"""
    print(f"\n{'='*60}")
    print(f"  场景: {name}")
    print(f"  节点数: {len(workflow['nodes'])}, 边数: {len(workflow['edges'])}")
    print(f"{'='*60}")

    body = {
        "workflow_json": json.dumps(workflow, ensure_ascii=False),
        "input_data": input_data,
    }
    resp = await client.post(f"{API}/execute_workflow", json=body, timeout=60)
    result = json.loads(resp.json()["result"])

    print(f"  Run ID: {result['run_id']}")
    print(f"  Status: {result['status']}")

    if "layers" in result:
        print(f"  拓扑层级: {len(result['layers'])} 层")
        for i, layer in enumerate(result["layers"]):
            print(f"    Layer {i}: {layer}")

    print(f"  输出节点:")
    for node_id, output in result["outputs"].items():
        summary = json.dumps(output, ensure_ascii=False, default=str)
        if len(summary) > 120:
            summary = summary[:120] + "..."
        print(f"    {node_id}: {summary}")

    return result


async def main():
    print("HermesSwarm 3场景验证")
    print(f"API: {API}")

    async with httpx.AsyncClient() as client:
        health = await client.get(f"{API}/health")
        if health.json()["status"] != "ok":
            print("API未就绪!")
            sys.exit(1)
        print("API就绪 ✓")

        results = {}

        results["content"] = await run_scenario(
            client, "内容生产", SCENARIO_1_CONTENT,
            "AI智能体编排平台的商业价值分析",
        )

        results["data"] = await run_scenario(
            client, "数据分析", SCENARIO_2_DATA,
            "2024年Q4销售数据CSV",
        )

        results["code"] = await run_scenario(
            client, "代码审查", SCENARIO_3_CODE,
            "src/core/engine.py",
        )

        print(f"\n{'='*60}")
        print("  验证总结")
        print(f"{'='*60}")
        all_passed = True
        for name, result in results.items():
            status = result.get("status", "unknown")
            has_layers = "layers" in result
            output_count = len(result.get("outputs", {}))
            passed = status == "completed" and output_count > 0
            all_passed = all_passed and passed
            mark = "✓" if passed else "✗"
            print(f"  {mark} {name}: status={status}, outputs={output_count}, layers={has_layers}")

        if all_passed:
            print("\n  全部3个场景验证通过! ✓")
        else:
            print("\n  部分场景未通过 ✗")

        return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)