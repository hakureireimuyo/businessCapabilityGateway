#!/usr/bin/env python3
"""Gateway Test Client

Validates all gateway API endpoints.
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
        req.add_header("Content-Type", "text/plain; charset=utf-8")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


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


def test_list_actions():
    """List Amazon plugin actions"""
    result = request("GET", "/plugins/amazon/actions")
    assert isinstance(result, list)
    print(f"  Amazon has {len(result)} actions:")
    for action in result:
        print(f"    [{action['type']:9}] {action['name']}")
        print(f"                 {action['description']}")


def test_market_analysis():
    """Keyword search > Filter > Market analysis"""
    bcl = (
        "amazon/search_by_keyword&keyword=halloween garland\n"
        "> filter&price_gte=10&price_lte=50\n"
        "> market_analysis()"
    )
    result = request("POST", "/execute", bcl)
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    print(f"  Market size: {data['market_size']}")
    print(f"  Avg price: ${data['avg_price']}")
    print(f"  Competition score: {data['competition_score']}/100")
    print(f"  Monthly sales: {data['total_monthly_sales']}")


def test_opportunity_analysis():
    """Keyword search > Find opportunities"""
    bcl = (
        "amazon/search_by_keyword&keyword=bluetooth headphone\n"
        "> find_opportunities&max_review=500"
    )
    result = request("POST", "/execute", bcl)
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    print(f"  Opportunities: {data['opportunity_count']}")
    for opp in data["opportunities"][:3]:
        print(f"    {opp['title']} (score: {opp['opportunity_score']}, "
              f"sales: {opp['monthly_sales']}, "
              f"reviews: {opp['review_count']})")


def test_competition_analysis():
    """Keyword search > Competition analysis"""
    bcl = (
        "amazon/search_by_keyword&keyword=halloween garland\n"
        "> competition_analysis()"
    )
    result = request("POST", "/execute", bcl)
    assert result.get("success"), f"Failed: {result}"
    data = result["data"]
    print(f"  Competitors: {data['total_competitors']}")
    print(f"  High-end: {data['high_end_count']}")
    print(f"  Low-end: {data['low_end_count']}")
    print(f"  Dominant: {data['dominant_players']}")
    print(f"  Entry barrier: {data['entry_barrier_score']}/100")


def test_invalid_pipeline():
    """Invalid pipeline: Sink > Transform (should fail)"""
    bcl = (
        "amazon/market_analysis&keyword=test\n"
        "> filter&price_gte=10"
    )
    result = request("POST", "/execute", bcl)
    assert result.get("success") is False, "Expected failure"
    print(f"  Correctly rejected: {result['error']['code']}")


def test_plugin_not_found():
    """Plugin not found"""
    bcl = "unknown/some_node"
    result = request("POST", "/execute", bcl)
    assert result.get("success") is False
    assert result["error"]["code"] == "PLUGIN_NOT_FOUND", \
        f"Expected PLUGIN_NOT_FOUND, got {result['error']['code']}"
    print(f"  Correct error: {result['error']['code']}")


def main():
    print("=" * 60)
    print("  Business Capability Gateway - Integration Test")
    print(f"  Server: {BASE_URL}")
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
    run_test("3. List Amazon Actions", test_list_actions)
    run_test("4. Market Analysis Pipeline", test_market_analysis)
    run_test("5. Opportunity Analysis Pipeline", test_opportunity_analysis)
    run_test("6. Competition Analysis Pipeline", test_competition_analysis)
    run_test("7. Invalid Pipeline Rejection", test_invalid_pipeline)
    run_test("8. Plugin Not Found Error", test_plugin_not_found)

    print(f"\n{'='*60}")
    print("  All tests completed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
