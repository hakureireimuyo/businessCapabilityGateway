"""Graph: validator — 7-layer protocol validation before execution

Layers:
  1. Node existence
  2. Parameter validity
  3. Input completeness
  4. Type compatibility
  5. Cycle detection (Kahn's algorithm)
  6. Output validity
  7. Business rules (single-plugin constraint)
"""

from .model import Graph
from ..registry.node_registry import get_registry
from ..exceptions import InvalidGraphError


class GraphValidator:
    """Validates a Graph against the node protocol before execution."""

    def __init__(self):
        self._registry = get_registry()

    def validate(self, graph: Graph) -> list[dict]:
        """Run all validation layers. Returns list of error dicts (empty = valid)."""
        errors: list[dict] = []

        errors.extend(self._check_node_existence(graph))
        if errors:
            return errors

        errors.extend(self._check_params(graph))
        errors.extend(self._check_input_completeness(graph))
        errors.extend(self._check_type_compatibility(graph))
        errors.extend(self._check_cycles(graph))
        errors.extend(self._check_outputs(graph))
        errors.extend(self._check_business_rules(graph))
        return errors

    def validate_or_raise(self, graph: Graph) -> None:
        errors = self.validate(graph)
        if errors:
            raise InvalidGraphError(errors)

    # Layer 1: Node existence
    def _check_node_existence(self, graph: Graph) -> list[dict]:
        errors = []
        for node_id, gn in graph.nodes.items():
            try:
                self._registry.get_node(graph.plugin, gn.node_name)
            except Exception:
                errors.append({
                    "layer": "NODE_NOT_FOUND", "node_id": node_id,
                    "node_name": gn.node_name, "plugin": graph.plugin,
                    "message": f"Node '{gn.node_name}' not found in plugin '{graph.plugin}'",
                })
        return errors

    # Layer 2: Parameter validity
    def _check_params(self, graph: Graph) -> list[dict]:
        errors = []
        for node_id, gn in graph.nodes.items():
            spec = self._registry.get_node(graph.plugin, gn.node_name)
            for pname, pspec in spec.parameter_specs.items():
                if pspec.required and pname not in gn.params:
                    errors.append({
                        "layer": "INVALID_PARAMS", "node_id": node_id,
                        "param": pname,
                        "message": f"Node '{node_id}' ({gn.node_name}): missing required parameter '{pname}'",
                    })
                if pname in gn.params and not isinstance(gn.params[pname], pspec.param_type):
                    errors.append({
                        "layer": "INVALID_PARAMS", "node_id": node_id,
                        "param": pname,
                        "expected": pspec.param_type.__name__,
                        "actual": type(gn.params[pname]).__name__,
                        "message": f"Node '{node_id}' ({gn.node_name}): parameter '{pname}' type mismatch",
                    })
            valid_params = set(spec.parameter_specs.keys())
            for pname in gn.params:
                if pname not in valid_params:
                    errors.append({
                        "layer": "INVALID_PARAMS", "node_id": node_id,
                        "param": pname,
                        "message": f"Node '{node_id}' ({gn.node_name}): unknown parameter '{pname}'",
                    })
        return errors

    # Layer 3: Input completeness
    def _check_input_completeness(self, graph: Graph) -> list[dict]:
        errors = []
        connected: dict[str, set[str]] = {}
        for e in graph.edges:
            connected.setdefault(e.to_node, set()).add(e.to_input)
        for node_id, gn in graph.nodes.items():
            spec = self._registry.get_node(graph.plugin, gn.node_name)
            connected_inputs = connected.get(node_id, set())
            for iname, ispec in spec.input_specs.items():
                if ispec.required and iname not in connected_inputs:
                    errors.append({
                        "layer": "UNSATISFIED_INPUT", "node_id": node_id,
                        "input": iname,
                        "message": f"Node '{node_id}' ({gn.node_name}): required input '{iname}' has no incoming edge",
                    })
        return errors

    # Layer 4: Type compatibility
    def _check_type_compatibility(self, graph: Graph) -> list[dict]:
        errors = []
        for e in graph.edges:
            from_gn = graph.nodes.get(e.from_node)
            to_gn = graph.nodes.get(e.to_node)
            if not from_gn or not to_gn:
                continue
            from_spec = self._registry.get_node(graph.plugin, from_gn.node_name)
            to_spec = self._registry.get_node(graph.plugin, to_gn.node_name)
            actual_type = from_spec.output_spec.artifact_type if from_spec.output_spec else None
            expected_input = to_spec.input_specs.get(e.to_input)
            if actual_type is None:
                errors.append({
                    "layer": "TYPE_MISMATCH",
                    "edge": {"from": e.from_node, "to": e.to_node},
                    "message": f"Node '{e.from_node}' has no output",
                })
            elif expected_input is None:
                errors.append({
                    "layer": "TYPE_MISMATCH",
                    "edge": {"from": e.from_node, "to": e.to_node},
                    "message": f"Node '{e.to_node}' has no input named '{e.to_input}'",
                })
            elif not issubclass(actual_type, expected_input.artifact_type):
                errors.append({
                    "layer": "TYPE_MISMATCH",
                    "edge": {"from": e.from_node, "from_output": e.from_output,
                             "to": e.to_node, "to_input": e.to_input},
                    "expected": expected_input.artifact_type.__name__,
                    "actual": actual_type.__name__,
                    "message": f"Type mismatch: {e.from_node}.{e.from_output} → {e.to_node}.{e.to_input}",
                })
        return errors

    # Layer 5: Cycle detection
    def _check_cycles(self, graph: Graph) -> list[dict]:
        in_degree = {nid: 0 for nid in graph.nodes}
        adj = {nid: [] for nid in graph.nodes}
        for e in graph.edges:
            if e.from_node in adj and e.to_node in in_degree:
                adj[e.from_node].append(e.to_node)
                in_degree[e.to_node] += 1
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if visited != len(graph.nodes):
            return [{
                "layer": "CYCLIC_DEPENDENCY",
                "message": f"Graph contains a cycle ({len(graph.nodes) - visited} nodes)",
            }]
        return []

    # Layer 6: Output validity
    def _check_outputs(self, graph: Graph) -> list[dict]:
        errors = []
        for output_id in graph.outputs:
            if output_id not in graph.nodes:
                errors.append({
                    "layer": "DANGLING_OUTPUT", "node_id": output_id,
                    "message": f"Output references unknown node '{output_id}'",
                })
        return errors

    # Layer 7: Business rules
    def _check_business_rules(self, graph: Graph) -> list[dict]:
        errors = []
        for node_id, gn in graph.nodes.items():
            try:
                self._registry.get_node(graph.plugin, gn.node_name)
            except Exception:
                errors.append({
                    "layer": "CROSS_PLUGIN", "node_id": node_id,
                    "message": f"Node '{gn.node_name}' not in plugin '{graph.plugin}'",
                })
        return errors
