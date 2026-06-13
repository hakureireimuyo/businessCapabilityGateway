"""Gateway SDK — Fluent Python API for building and executing node graphs.

This SDK is the primary interface for AI Agents to interact with
the Business Capability Gateway.

Usage:
    from gateway_sdk import Graph

    g = Graph(plugin="amazon")
    products = g.keyword_search(keyword="halloween garland")
    analysis = g.market_analysis(products=products)
    g.output(analysis)
    result = g.execute()
    # result = {"market_analysis": {...}}
"""

from .graph import Graph
from .placeholder import ArtifactPlaceholder
from .exceptions import GraphError

__all__ = ["Graph", "ArtifactPlaceholder", "GraphError"]
