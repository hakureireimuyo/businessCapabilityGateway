#!/usr/bin/env python3
"""Gateway Test Client v2.0

Validates all gateway API endpoints with the new Graph protocol.
Usage: python test_client.py
"""

import json
import sys
import urllib.request

BASE_URL = "http://localhost:8765"
PASS = "[PASS]"
FAIL = "[FAIL]"


def request(method: str, path: str, body: str | None = None) -> dict:
    """Send HTTP request to gateway."""
    url = f"{BASE_URL}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except urllib.error.URLError as e:
        return {"error": str(e)}


def run_test(name: str, fn):
    """Run a single test and report result."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    try:
        fn()
        print(f"  {PASS}")
    except Exception as e:
        print(f"  {FAIL}: {e}")
        import traceback
        traceback.print_exc()


# ========== Tests ==========

def test_health():
    """Health check"""
    result = request("GET", "/health")
    assert result.get("status") == "ok", f"Expected status=ok, got {result}"
    print(f"  Response: {json.dumps(result)}")


def test_list_plugins():
    """List plugins"""
    result = request("GET", "/plugins")
    assert isinstance(result, list)
    assert "amazon" in result
    print(f"  Plugins: {result}")


def test_list_nodes():
    """List Amazon plugin node specs (new protocol)"""
    result = request("GET", "/plugins/amazon/nodes")
    assert isinstance(result, list)
    print(f"  Amazon has {len(result)} node specs:")
    for spec in result:
        name = spec["name"]
        inputs = list(spec.get("input_specs", {}).keys())
        output = spec.get("output_spec", {}).get("key", "?") if spec.get("output_spec") else "?"
        params = list(spec.get("parameter_specs", {}).keys())
        print(f"    [{name}]  inputs={inputs}  output={output}  params={params}")


def test_simple_graph():
    """Simple 2-node graph: keyword_search → market_analysis"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland"}},
            "a1": {"node_name": "market_analysis", "params": {}},
        },
        "edges": [
            {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"},
        ],
        "outputs": ["a1"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    print(f"  Market size: {data['market_analysis']['market_size']}")
    print(f"  Avg price: ${data['market_analysis']['avg_price']}")
    print(f"  Competition score: {data['market_analysis']['competition_score']}/100")


def test_filtered_graph():
    """Graph with filter: search → filter → market_analysis"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland", "limit": 50}},
            "f1": {"node_name": "filter", "params": {"price_gte": 10.0, "price_lte": 50.0}},
            "a1": {"node_name": "market_analysis", "params": {}},
        },
        "edges": [
            {"from": "s1", "from_output": "products", "to": "f1", "to_input": "products"},
            {"from": "f1", "from_output": "filtered_products", "to": "a1", "to_input": "products"},
        ],
        "outputs": ["a1"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    ma = data["market_analysis"]
    print(f"  Filtered market size: {ma['market_size']}")
    print(f"  Filtered avg price: ${ma['avg_price']}")
    print(f"  Competition score: {ma['competition_score']}/100")


def test_parallel_analysis_graph():
    """Graph with parallel branches: search → sales_analysis + review_analysis → market_score"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland"}},
            "sales": {"node_name": "sales_analysis", "params": {}},
            "reviews": {"node_name": "review_analysis", "params": {}},
            "score": {"node_name": "market_score", "params": {"method": "weighted"}},
        },
        "edges": [
            {"from": "s1", "from_output": "products", "to": "sales", "to_input": "products"},
            {"from": "s1", "from_output": "products", "to": "reviews", "to_input": "products"},
            {"from": "sales", "from_output": "sales_metrics", "to": "score", "to_input": "sales"},
            {"from": "reviews", "from_output": "review_metrics", "to": "score", "to_input": "reviews"},
        ],
        "outputs": ["score"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    signal = data["market_signal"]
    print(f"  Market signal: {signal['market_signal_score']}/100")
    print(f"  Sales contribution: {signal['sales_contribution']}")
    print(f"  Rating contribution: {signal['rating_contribution']}")
    print(f"  Products analyzed: {signal['product_count']}")


def test_multi_output_graph():
    """Graph with multiple outputs: search → analysis → chart + report"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "s1": {"node_name": "keyword_search", "params": {"keyword": "bluetooth headphone"}},
            "a1": {"node_name": "competition_analysis", "params": {}},
            "o1": {"node_name": "chart_output", "params": {}},
            "o2": {"node_name": "json_output", "params": {}},
        },
        "edges": [
            {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"},
            {"from": "a1", "from_output": "competition_analysis", "to": "o1", "to_input": "data"},
            {"from": "a1", "from_output": "competition_analysis", "to": "o2", "to_input": "data"},
        ],
        "outputs": ["o1", "o2"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    assert "chart" in data, f"Expected 'chart' in outputs, got {list(data.keys())}"
    assert "json" in data, f"Expected 'json' in outputs, got {list(data.keys())}"
    print(f"  Output keys: {list(data.keys())}")
    print(f"  Chart source: {data['chart']['source']}")
    comp = data['json']
    print(f"  Competition: {comp.get('total_competitors', '?')} competitors, barrier={comp.get('entry_barrier_score', '?')}/100")


def test_invalid_graph_cycle():
    """Invalid graph: cyclic dependency (should fail validation)"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "a": {"node_name": "keyword_search", "params": {"keyword": "test"}},
            "b": {"node_name": "filter", "params": {}},
            "c": {"node_name": "sort", "params": {"by": "price"}},
        },
        "edges": [
            {"from": "a", "from_output": "products", "to": "b", "to_input": "products"},
            {"from": "b", "from_output": "filtered_products", "to": "c", "to_input": "products"},
            {"from": "c", "from_output": "sorted_products", "to": "b", "to_input": "products"},  # cycle!
        ],
        "outputs": ["c"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success") is False, "Expected validation failure for cycle"
    assert result["error"]["code"] == "INVALID_GRAPH"
    print(f"  Correctly rejected: {result['error']['message']}")


def test_invalid_type_mismatch():
    """Invalid graph: type mismatch (should fail validation)"""
    graph = {
        "plugin": "amazon",
        "nodes": {
            "s1": {"node_name": "keyword_search", "params": {"keyword": "test"}},
            "a1": {"node_name": "market_analysis", "params": {}},
            "a2": {"node_name": "market_score", "params": {}},
        },
        "edges": [
            {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"},
            # ERROR: market_analysis produces MarketAnalysis, but market_score.sales expects SalesMetrics
            {"from": "a1", "from_output": "market_analysis", "to": "a2", "to_input": "sales"},
            {"from": "a1", "from_output": "market_analysis", "to": "a2", "to_input": "reviews"},
        ],
        "outputs": ["a2"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success") is False, "Expected validation failure for type mismatch"
    assert result["error"]["code"] == "INVALID_GRAPH"
    print(f"  Correctly rejected: {result['error']['message']}")


def test_plugin_not_found():
    """Non-existent plugin"""
    graph = {
        "plugin": "nonexistent",
        "nodes": {"n1": {"node_name": "some_node", "params": {}}},
        "edges": [],
        "outputs": ["n1"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success") is False
    print(f"  Correct error: {result.get('error', {}).get('code', '?')}")


def test_node_not_found():
    """Non-existent node"""
    graph = {
        "plugin": "amazon",
        "nodes": {"n1": {"node_name": "ghost_node", "params": {}}},
        "edges": [],
        "outputs": ["n1"],
    }
    result = request("POST", "/execute", json.dumps(graph))
    assert result.get("success") is False
    print(f"  Correct error: {result.get('error', {}).get('code', '?')}")


# ========== Main ==========

def main():
    print("=" * 60)
    print("  Business Capability Gateway v2.0 — Integration Test")
    print(f"  Server: {BASE_URL}")
    print("  Protocol: Node + Graph (DAG)")
    print("=" * 60)

    # Check service is running
    try:
        request("GET", "/health")
    except Exception:
        print(f"\n{FAIL} Cannot connect to gateway service!")
        print("   Please start the service first: python main.py start")
        sys.exit(1)

    run_test("1. Health Check", test_health)
    run_test("2. List Plugins", test_list_plugins)
    run_test("3. List Node Specs (new protocol)", test_list_nodes)
    run_test("4. Simple Graph: search → market_analysis", test_simple_graph)
    run_test("5. Filtered Graph: search → filter → analysis", test_filtered_graph)
    run_test("6. Parallel Graph: sales + reviews → market_score", test_parallel_analysis_graph)
    run_test("7. Multi-output Graph: analysis → chart + json", test_multi_output_graph)
    run_test("8. Invalid: Cyclic Dependency", test_invalid_graph_cycle)
    run_test("9. Invalid: Type Mismatch", test_invalid_type_mismatch)
    run_test("10. Plugin Not Found", test_plugin_not_found)
    run_test("11. Node Not Found", test_node_not_found)

    print(f"\n{'='*60}")
    print("  All tests completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
