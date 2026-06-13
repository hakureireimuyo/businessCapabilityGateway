"""Registry: NodeRegistry — capability discovery and Node lookup

Central index of all registered Nodes across all plugins.
Provides registration, lookup, and spec discovery (Agent-facing API).
"""

from typing import Any

from ..protocol.node import Node
from ..exceptions import NodeNotFoundException, PluginNotFoundException
from ..logger import get_logger

logger = get_logger(__name__)


class NodeRegistry:
    """Global node registry: {plugin_name: {node_name: Node instance}}"""

    def __init__(self):
        self._nodes: dict[str, dict[str, Node]] = {}

    def register(self, plugin_name: str, nodes: list[Node]) -> None:
        if plugin_name not in self._nodes:
            self._nodes[plugin_name] = {}
        for node in nodes:
            self._nodes[plugin_name][node.name] = node
            logger.info("Registered node: %s/%s", plugin_name, node.name)

    def unregister_plugin(self, plugin_name: str) -> None:
        if plugin_name in self._nodes:
            del self._nodes[plugin_name]
            logger.info("Unregistered plugin: %s", plugin_name)

    def get_node(self, plugin_name: str, node_name: str) -> Node:
        plugin_nodes = self._nodes.get(plugin_name)
        if plugin_nodes is None:
            raise PluginNotFoundException(plugin_name)
        node = plugin_nodes.get(node_name)
        if node is None:
            raise NodeNotFoundException(plugin_name, node_name)
        return node

    def get_all_plugins(self) -> list[str]:
        return sorted(self._nodes.keys())

    def list_nodes(self, plugin_name: str) -> list[Node]:
        return list(self._nodes.get(plugin_name, {}).values())

    def list_specs(self, plugin_name: str) -> list[dict[str, Any]]:
        return [n.to_spec_dict() for n in self.list_nodes(plugin_name)]

    def list_summaries(self, plugin_name: str) -> list[dict[str, Any]]:
        """Return lightweight summaries for all nodes in a plugin.
        Enough for Agent to pick which nodes to query for full specs."""
        return [n.to_summary_dict() for n in self.list_nodes(plugin_name)]

    def get_spec(self, plugin_name: str, node_name: str) -> dict[str, Any]:
        """Return the full protocol spec for a single node."""
        node = self.get_node(plugin_name, node_name)
        return node.to_spec_dict()

    def get_capabilities(self, plugin_name: str | None = None) -> dict:
        if plugin_name:
            return {"plugin": plugin_name, "nodes": self.list_summaries(plugin_name)}
        return {
            name: {"plugin": name, "nodes": self.list_summaries(name)}
            for name in self._nodes
        }


# ---- Global singleton ----

_registry: NodeRegistry | None = None


def get_registry() -> NodeRegistry:
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry


def register_nodes(plugin_name: str, nodes: list[Node]) -> None:
    get_registry().register(plugin_name, nodes)
