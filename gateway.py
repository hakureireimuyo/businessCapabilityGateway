"""Gateway SDK — Python API for Agent to build and execute graphs.

Usage:
    from gateway import Graph

    g = Graph(plugin="amazon")
    products = g.keyword_search(keyword="halloween garland")
    market = g.market_analysis(products=products)
    g.output(g.chart_output(market=market))
    result = g.execute()
    # result = {"chart_output": {...}}
"""

from __future__ import annotations
from typing import Any

from core.graph.model import Graph as CoreGraph, GraphNode, GraphEdge
from core.registry.node_registry import get_registry
from core.graph.validator import GraphValidator
from core.graph.executor import GraphExecutor


class ArtifactPlaceholder:
    """Represents a future Artifact during graph construction.

    Each g.some_node(...) call returns one of these.
    Passing it to another g.some_node(...) creates an edge.
    """

    def __init__(self, node_id: str, output_key: str, artifact_type: type):
        self.node_id = node_id
        self.output_key = output_key
        self.artifact_type = artifact_type

    def __repr__(self) -> str:
        return (
            f"ArtifactPlaceholder("
            f"node={self.node_id!r}, "
            f"key={self.output_key!r}, "
            f"type={self.artifact_type.__name__!r})"
        )


class Graph:
    """Fluent graph builder — Agent's primary API.

    Calling g.some_node(param=value, input_name=placeholder)
    registers a node instance in the graph and returns an
    ArtifactPlaceholder for downstream use.

    No actual execution happens until g.execute() is called.
    """

    def __init__(self, plugin: str):
        self.plugin = plugin
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._outputs: list[str] = []
        self._counter: int = 0
        self._registry = get_registry()

        # Dynamically bind all registered nodes as methods
        specs = self._registry.list_specs(plugin)
        if not specs:
            raise ValueError(f"Plugin '{plugin}' has no registered nodes. "
                             f"Available: {self._registry.get_all_plugins()}")

        for spec_dict in specs:
            node_name = spec_dict["name"]
            if not hasattr(self, node_name):
                setattr(self, node_name, self._make_method(node_name))

    def _make_method(self, node_name: str):
        """Create a bound method that registers a node on each call."""

        def node_method(**kwargs) -> ArtifactPlaceholder:
            return self._add_node(node_name, kwargs)

        node_method.__name__ = node_name
        node_method.__doc__ = f"Register a '{node_name}' node in the graph."
        return node_method

    def _add_node(
        self, node_name: str, kwargs: dict[str, Any]
    ) -> ArtifactPlaceholder:
        """Register a node instance and its edges.

        Separates kwargs into:
          - Artifact refs (ArtifactPlaceholder values) → edges
          - Literal params (str/int/float/bool values) → node params
        """
        node_id = f"{node_name}_{self._counter}"
        self._counter += 1

        params = {}
        inputs: dict[str, ArtifactPlaceholder] = {}

        for key, value in kwargs.items():
            if isinstance(value, ArtifactPlaceholder):
                inputs[key] = value
            else:
                params[key] = value

        # Register the node
        self._nodes[node_id] = GraphNode(
            node_id=node_id,
            node_name=node_name,
            params=params,
        )

        # Create edges from input placeholders
        for input_name, placeholder in inputs.items():
            self._edges.append(GraphEdge(
                from_node=placeholder.node_id,
                from_output=placeholder.output_key,
                to_node=node_id,
                to_input=input_name,
            ))

        # Determine output info for the placeholder
        spec_node = self._registry.get_node(self.plugin, node_name)
        output_key = spec_node.output_spec.key if spec_node.output_spec else node_name
        output_type = (
            spec_node.output_spec.artifact_type
            if spec_node.output_spec else type(None)
        )

        return ArtifactPlaceholder(
            node_id=node_id,
            output_key=output_key,
            artifact_type=output_type,
        )

    def output(self, placeholder: ArtifactPlaceholder) -> None:
        """Mark a node's output as a final result.

        Args:
            placeholder: An ArtifactPlaceholder returned by a node call.
        """
        if placeholder.node_id not in self._nodes:
            raise ValueError(
                f"Node '{placeholder.node_id}' is not in this graph"
            )
        if placeholder.node_id not in self._outputs:
            self._outputs.append(placeholder.node_id)

    def execute(self) -> dict[str, Any]:
        """Validate and execute the graph.

        Returns:
            dict mapping output_key → raw data.
        """
        graph = CoreGraph(
            plugin=self.plugin,
            nodes=dict(self._nodes),
            edges=list(self._edges),
            outputs=list(self._outputs),
        )

        validator = GraphValidator()
        validator.validate_or_raise(graph)

        executor = GraphExecutor()
        return executor.execute(graph)
