#!/usr/bin/env python3
"""Gateway Test Client v2.0

Validates all gateway API endpoints using the Python SDK (script) interface.
Usage: python test_client.py
"""

import json
import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8765"
PASS = "[PASS]"
FAIL = "[FAIL]"


def request(method: str, path: str, body: str | None = None,
            content_type: str = "application/json") -> dict:
    """Send HTTP request to gateway."""
    url = f"{BASE_URL}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", content_type)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
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
    """List Amazon plugin node summaries"""
    result = request("GET", "/plugins/amazon/nodes")
    assert isinstance(result, list)
    print(f"  Amazon has {len(result)} node summaries:")
    for s in result:
        entry = "ENTRY" if s.get("is_entry") else "LINK"
        print(f"    [{s['name']}]  {entry}  output={s.get('output_key')}({s.get('output_type')})  "
              f"inputs={s.get('input_count')}")


def test_get_node_spec():
    """Get full spec for a single node"""
    result = request("GET", "/plugins/amazon/nodes/keyword_search")
    assert isinstance(result, dict)
    assert result["name"] == "keyword_search"
    assert "input_specs" in result
    assert "output_spec" in result
    assert "parameter_specs" in result
    print(f"  keyword_search full spec:")
    print(f"    inputs:  {list(result['input_specs'].keys())}")
    print(f"    output:  {result['output_spec']['key']} ({result['output_spec']['artifact_type']})")
    print(f"    params:  {list(result['parameter_specs'].keys())}")


def test_simple_graph():
    """Simple 2-node graph: keyword_search -> market_analysis"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
analysis = g.market_analysis(products=products)
g.output(analysis)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    ma = data["market_analysis"]
    print(f"  Market size: {ma['market_size']}")
    print(f"  Avg price: ${ma['avg_price']}")
    print(f"  Competition score: {ma['competition_score']}/100")


def test_filtered_graph():
    """Graph with filter: search -> filter -> market_analysis"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland", limit=50)
filtered = g.filter(products=products, price_gte=10.0, price_lte=50.0)
analysis = g.market_analysis(products=filtered)
g.output(analysis)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    ma = data["market_analysis"]
    print(f"  Filtered market size: {ma['market_size']}")
    print(f"  Filtered avg price: ${ma['avg_price']}")
    print(f"  Competition score: {ma['competition_score']}/100")


def test_parallel_analysis_graph():
    """Graph with parallel branches: search -> sales_analysis + review_analysis -> market_score"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
sales = g.sales_analysis(products=products)
reviews = g.review_analysis(products=products)
score = g.market_score(sales=sales, reviews=reviews, method="weighted")
g.output(score)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    signal = data["market_signal"]
    print(f"  Market signal: {signal['market_signal_score']}/100")
    print(f"  Sales contribution: {signal['sales_contribution']}")
    print(f"  Rating contribution: {signal['rating_contribution']}")
    print(f"  Products analyzed: {signal['product_count']}")


def test_multi_output_graph():
    """Graph with multiple outputs: search -> competition_analysis -> chart + json"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="bluetooth headphone")
analysis = g.competition_analysis(products=products)
chart = g.chart_output(data=analysis)
js = g.json_output(data=analysis)
g.output(chart)
g.output(js)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    assert "chart" in data, f"Expected 'chart' in outputs, got {list(data.keys())}"
    assert "json" in data, f"Expected 'json' in outputs, got {list(data.keys())}"
    print(f"  Output keys: {list(data.keys())}")
    print(f"  Chart source: {data['chart']['source']}")
    comp = data['json']
    print(f"  Competition: {comp.get('total_competitors', '?')} competitors, barrier={comp.get('entry_barrier_score', '?')}/100")


def test_type_mismatch():
    """Invalid graph: type mismatch (MarketAnalysis fed into SalesMetrics input)"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="test")
analysis = g.market_analysis(products=products)
# BUG: market_score expects sales=SalesMetrics but we pass MarketAnalysis
score = g.market_score(sales=analysis, reviews=analysis)
g.output(score)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success") is False, "Expected validation failure for type mismatch"
    assert result["error"]["code"] == "INVALID_GRAPH"
    print(f"  Correctly rejected: {result['error']['message']}")


def test_plugin_not_found():
    """Non-existent plugin"""
    script = """
g = Graph(plugin="nonexistent")
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success") is False
    print(f"  Correct error code: {result.get('error', {}).get('code', '?')}")
    print(f"  Message: {result.get('error', {}).get('message', '?')}")


def test_node_not_found():
    """Non-existent node method on Graph"""
    script = """
g = Graph(plugin="amazon")
products = g.ghost_node(keyword="test")
g.output(products)
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success") is False
    print(f"  Correct error code: {result.get('error', {}).get('code', '?')}")
    print(f"  Message: {result.get('error', {}).get('message', '?')}")


def test_missing_result():
    """Script without result = g.execute()"""
    script = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="test")
g.output(products)
x = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success") is False
    assert result["error"]["code"] == "INVALID_SCRIPT"
    print(f"  Correctly rejected: {result['error']['message']}")


def test_import_blocked():
    """Script attempting to import a module (AST validation rejects)"""
    script = """
import os
g = Graph(plugin="amazon")
result = g.execute()
"""
    result = request("POST", "/execute", script, content_type="text/plain")
    assert result.get("success") is False
    assert result["error"]["code"] == "INVALID_SCRIPT"
    print(f"  Correctly blocked: {result['error']['message']}")


# ========== Main ==========

def main():
    print("=" * 60)
    print("  Business Capability Gateway v2.0 — Integration Test")
    print(f"  Server: {BASE_URL}")
    print("  Protocol: Python SDK (text/plain)")
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
    run_test("3. List Node Summaries", test_list_nodes)
    run_test("4. Single Node Spec: keyword_search", test_get_node_spec)
    run_test("5. Simple Graph: search -> market_analysis", test_simple_graph)
    run_test("6. Filtered Graph: search -> filter -> analysis", test_filtered_graph)
    run_test("7. Parallel Graph: sales + reviews -> market_score", test_parallel_analysis_graph)
    run_test("8. Multi-output Graph: analysis -> chart + json", test_multi_output_graph)
    run_test("9. Invalid: Type Mismatch", test_type_mismatch)
    run_test("10. Plugin Not Found", test_plugin_not_found)
    run_test("11. Node Not Found", test_node_not_found)
    run_test("12. Missing result = g.execute()", test_missing_result)
    run_test("13. AST Blocked: import statement", test_import_blocked)

    print(f"\n{'='*60}")
    print("  All tests completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
