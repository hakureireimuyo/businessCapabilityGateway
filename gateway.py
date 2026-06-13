"""Gateway SDK — Python API for Agent to build and execute graphs.

Local usage (no server needed):
    from gateway import Graph, init

    init()  # load all plugins into registry

    g = Graph(plugin="amazon")
    products = g.keyword_search(keyword="halloween garland")
    analysis = g.market_analysis(products=products)
    g.output(analysis)
    result = g.execute()
    # result = {"market_analysis": {...}}

Server-based usage (via POST /execute):
    from gateway import Graph
    # ... same SDK, submitted as Python script via HTTP
"""

from gateway_sdk import Graph, GraphError
from core.plugin.loader import discover_and_load_plugins


def init(plugins_dir: str | None = None) -> list[str]:
    """Discover and load all plugins into the global registry.

    Call this once at the start of a local script before using Graph.
    Returns a list of loaded plugin names.

    Args:
        plugins_dir: Optional custom plugins directory path.
                     Defaults to <project_root>/plugins/.
    """
    return discover_and_load_plugins(plugins_dir)


__all__ = ["Graph", "GraphError", "init"]
