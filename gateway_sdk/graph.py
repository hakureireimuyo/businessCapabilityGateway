"""SDK: Graph — fluent API for building and executing node graphs

Each registered Node becomes a method on the Graph object.
Calling a node method immediately executes the node — there is no
intermediate Graph representation, no deferred validation pass,
and no separate scheduling phase.  Python's own execution order
naturally enforces the dependency DAG.
"""

from __future__ import annotations
from typing import Any

from core.protocol.artifact import Artifact
from core.registry.node_registry import get_registry, NodeRegistry
from core.runtime.context import ExecutionContext
from core.exceptions import NodeNotFoundException, PluginNotFoundException

from .exceptions import GraphError


def _type_name(t: type) -> str:
    """Human-readable type name for error messages."""
    return getattr(t, "__name__", str(t))


class _NodeCall:
    """Callable proxy for a registered Node name on a Graph.

    Returned by Graph.__getattr__("node_name").  When called with keyword
    arguments, separates Artifact references from literal parameters,
    validates them against the Node spec, executes the node immediately,
    and returns the resulting Artifact.
    """

    __slots__ = ("_graph", "_node_name", "_spec")

    def __init__(self, graph: "Graph", node_name: str):
        self._graph = graph
        self._node_name = node_name
        self._spec = graph._registry.get_node(graph._plugin, node_name)

    def __call__(self, **kwargs: Any) -> Artifact:
        graph = self._graph
        spec = self._spec

        # 1. Separate kwargs into params (literal) and inputs (Artifact)
        params: dict[str, Any] = {}
        inputs: dict[str, Artifact] = {}

        for key, value in kwargs.items():
            if isinstance(value, Artifact):
                # Artifact reference — validate input name and type compatibility
                if key not in spec.input_specs:
                    raise GraphError(
                        f"Node '{self._node_name}' has no input named '{key}'. "
                        f"Available inputs: {list(spec.input_specs.keys())}"
                    )
                expected_type = spec.input_specs[key].artifact_type
                actual_type = value.type
                if not issubclass(actual_type, expected_type):
                    raise GraphError(
                        f"Type mismatch: {actual_type.__name__} cannot feed into "
                        f"{expected_type.__name__} "
                        f"(input '{key}' of node '{self._node_name}')"
                    )
                inputs[key] = value
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

        # 3. Validate required inputs are satisfied
        for iname, ispec in spec.input_specs.items():
            if ispec.required and iname not in inputs:
                raise GraphError(
                    f"Node '{self._node_name}' requires input '{iname}' "
                    f"({ispec.artifact_type.__name__})"
                )

        # 4. Execute immediately
        artifact = spec.execute(inputs, params, graph._context)

        # 5. Track artifact in context (for debugging / introspection)
        graph._context.artifacts[artifact.key] = artifact

        return artifact


class Graph:
    """Fluent API for immediate node execution.

    Usage:
        g = Graph(plugin="amazon")
        products = g.keyword_search(keyword="halloween garland")
        analysis = g.market_analysis(products=products)
        g.output(analysis)
        result = g.execute()
    """

    __slots__ = ("_plugin", "_registry", "_outputs", "_context")

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

        self._outputs: list[Artifact] = []
        self._context = ExecutionContext(plugin_name=plugin)

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

    def output(self, artifact: Artifact) -> None:
        """Mark a node's output Artifact as a final result.

        Multiple artifacts can be marked; all will be included in execute().
        """
        self._outputs.append(artifact)

    def execute(self) -> dict[str, Any]:
        """Return collected outputs as {output_key: raw_data}.

        Since nodes execute immediately when called, this method simply
        formats the artifacts marked via output() into the result dict.
        """
        return {a.key: a.data for a in self._outputs}
