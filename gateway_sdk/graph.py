"""SDK: Graph — fluent API for building and executing node graphs

This is the primary interface for Agents.  Each registered Node becomes
a method on the Graph object.  Calling it returns an ArtifactPlaceholder.
Passing a placeholder to another node call automatically creates an edge.
"""

from __future__ import annotations
from typing import Any

from core.graph.model import Graph as InternalGraph, GraphNode, GraphEdge
from core.graph.validator import GraphValidator
from core.graph.executor import GraphExecutor
from core.registry.node_registry import get_registry, NodeRegistry
from core.exceptions import (
    GatewayException,
    NodeNotFoundException,
    PluginNotFoundException,
)

from .placeholder import ArtifactPlaceholder
from .exceptions import GraphError


def _type_name(t: type) -> str:
    """Human-readable type name for error messages."""
    return getattr(t, "__name__", str(t))


class _NodeCall:
    """Callable proxy for a registered Node name on a Graph.

    Returned by Graph.__getattr__("node_name").  When called with keyword
    arguments, separates ArtifactPlaceholder references from literal
    parameters, validates them against the Node spec, creates a GraphNode
    and GraphEdges, and returns an ArtifactPlaceholder.
    """

    __slots__ = ("_graph", "_node_name", "_spec")

    def __init__(self, graph: "Graph", node_name: str):
        self._graph = graph
        self._node_name = node_name
        self._spec = graph._registry.get_node(graph._plugin, node_name)

    def __call__(self, **kwargs: Any) -> ArtifactPlaceholder:
        graph = self._graph
        spec = self._spec

        # 1. Separate kwargs into params and artifact references
        params: dict[str, Any] = {}
        edges: list[tuple[str, str, str]] = []  # (from_node, from_output, to_input)

        for key, value in kwargs.items():
            if isinstance(value, ArtifactPlaceholder):
                # Artifact reference → will create edge
                if key not in spec.input_specs:
                    raise GraphError(
                        f"Node '{self._node_name}' has no input named '{key}'. "
                        f"Available inputs: {list(spec.input_specs.keys())}"
                    )
                edges.append((value._node_id, value._output_key, key))
            else:
                params[key] = value

        # 2. Validate params against parameter_specs
        for pname, pspec in spec.parameter_specs.items():
            if pspec.required and pname not in params:
                raise GraphError(
                    f"Node '{self._node_name}' requires parameter '{pname}' "
                    f"({_type_name(pspec.param_type)})"
                )
        for pname, pvalue in params.items():
            if pname not in spec.parameter_specs:
                raise GraphError(
                    f"Node '{self._node_name}' has no parameter named '{pname}'. "
                    f"Available params: {list(spec.parameter_specs.keys())}"
                )
            expected_type = spec.parameter_specs[pname].param_type
            if not isinstance(pvalue, expected_type):
                raise GraphError(
                    f"Node '{self._node_name}' parameter '{pname}': "
                    f"expected {_type_name(expected_type)}, got {_type_name(type(pvalue))}"
                )

        # 3. Generate unique node_id
        graph._counter[self._node_name] = graph._counter.get(self._node_name, 0) + 1
        node_id = f"{self._node_name}_{graph._counter[self._node_name]}"

        # 4. Create GraphNode
        gn = GraphNode(node_id=node_id, node_name=self._node_name, params=params)
        graph._nodes[node_id] = gn

        # 5. Create GraphEdges for artifact references
        for from_node, from_output, to_input in edges:
            edge = GraphEdge(
                from_node=from_node,
                from_output=from_output,
                to_node=node_id,
                to_input=to_input,
            )
            graph._edges.append(edge)

        # 6. Return ArtifactPlaceholder
        output_key = spec.output_spec.key if spec.output_spec else node_id
        artifact_type = spec.output_spec.artifact_type if spec.output_spec else type(
            "Unknown", (), {}
        )
        return ArtifactPlaceholder(
            _node_id=node_id,
            _output_key=output_key,
            _artifact_type=artifact_type,
        )


class Graph:
    """Fluent API for building and executing node graphs.

    Usage:
        g = Graph(plugin="amazon")
        products = g.keyword_search(keyword="halloween garland")
        analysis = g.market_analysis(products=products)
        g.output(analysis)
        result = g.execute()
    """

    __slots__ = (
        "_plugin",
        "_registry",
        "_nodes",
        "_edges",
        "_output_ids",
        "_counter",
        "_validator",
        "_executor",
    )

    def __init__(self, plugin: str):
        """Create a new Graph for a specific plugin."""
        self._plugin = plugin
        self._registry: NodeRegistry = get_registry()

        # Verify plugin exists
        if plugin not in self._registry.get_all_plugins():
            available = self._registry.get_all_plugins()
            raise GraphError(
                f"Plugin '{plugin}' not found. Available: {available or '(none)'}"
            )

        # Internal state accumulated during method calls
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._output_ids: set[str] = set()
        self._counter: dict[str, int] = {}

        # Execution components (lazy)
        self._validator = GraphValidator()
        self._executor = GraphExecutor()

    @property
    def plugin(self) -> str:
        return self._plugin

    def __getattr__(self, name: str) -> _NodeCall:
        """Dynamic dispatch: any registered node name becomes a method.

        g.keyword_search(...) → _NodeCall(graph, "keyword_search")(...)
        """
        if name.startswith("_"):
            raise AttributeError(name)

        try:
            self._registry.get_node(self._plugin, name)
        except (PluginNotFoundException, NodeNotFoundException):
            raise GraphError(
                f"Node '{name}' not found in plugin '{self._plugin}'. "
                f"Use GET /plugins/{self._plugin}/nodes to see available nodes."
            ) from None

        return _NodeCall(self, name)

    def output(self, placeholder: ArtifactPlaceholder) -> None:
        """Mark a node's output as a final result.

        Multiple nodes can be marked as outputs; all of their data
        will be included in the execute() result.
        """
        if placeholder._node_id not in self._nodes:
            raise GraphError(
                f"ArtifactPlaceholder references unknown node '{placeholder._node_id}'"
            )
        self._output_ids.add(placeholder._node_id)

    def execute(self) -> dict[str, Any]:
        """Build the internal Graph, validate, execute, and return results.

        This is called at the end of an Agent's script. It:
          1. Builds the core.graph.model.Graph from accumulated state
          2. Validates via GraphValidator (7 layers)
          3. Executes via GraphExecutor (dependency-driven parallel)
          4. Returns a dict of {output_key: raw_data}
        """
        if not self._nodes:
            return {}

        # Build internal graph
        graph = InternalGraph(
            plugin=self._plugin,
            nodes=self._nodes,
            edges=list(self._edges),
            outputs=sorted(self._output_ids),
        )

        # Validate (raises InvalidGraphError on failure)
        self._validator.validate_or_raise(graph)

        # Execute
        result = self._executor.execute(graph)

        return result
