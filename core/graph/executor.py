"""Graph: executor — dependency-driven parallel scheduling

Replaces the old linear PipelineExecutor with topological + ThreadPoolExecutor.
Nodes execute as soon as all their input Artifacts are ready.
Independent nodes run in parallel.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .model import Graph, GraphNode
from ..registry.node_registry import get_registry
from ..runtime.context import ExecutionContext
from ..protocol.artifact import Artifact
from ..exceptions import ExecutionFailedError
from ..logger import get_logger

logger = get_logger(__name__)


class GraphExecutor:
    """Executes a validated Graph with dependency-driven parallel scheduling."""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self._registry = get_registry()

    def execute(self, graph: Graph) -> dict[str, Any]:
        """Execute the graph and return final outputs."""
        if not graph.nodes:
            return {}

        context = ExecutionContext(plugin_name=graph.plugin)
        start_time = time.time()

        # Build scheduling state
        in_degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
        downstream: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
        upstream_map: dict[str, list[tuple[str, str, str]]] = {nid: [] for nid in graph.nodes}

        for e in graph.edges:
            in_degree[e.to_node] = in_degree.get(e.to_node, 0) + 1
            downstream.setdefault(e.from_node, []).append(e.to_node)
            upstream_map.setdefault(e.to_node, []).append(
                (e.from_node, e.from_output, e.to_input)
            )

        # Map node_id → output_key for artifact resolution
        node_output_keys: dict[str, str] = {}
        for nid, gn in graph.nodes.items():
            spec = self._registry.get_node(graph.plugin, gn.node_name)
            if spec.output_spec:
                node_output_keys[nid] = spec.output_spec.key

        completed: set[str] = set()
        failed: dict[str, str] = {}
        artifacts: dict[str, Artifact] = {}

        ready = sorted(
            [nid for nid, deg in in_degree.items() if deg == 0],
            key=lambda nid: graph.nodes[nid].node_name,
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while ready:
                # Resolve inputs for ready nodes
                tasks: dict[str, dict[str, Artifact]] = {}
                for nid in ready:
                    resolved = {}
                    for from_node, from_output, to_input in upstream_map.get(nid, []):
                        art_key = node_output_keys.get(from_node, from_output)
                        if art_key in artifacts:
                            resolved[to_input] = artifacts[art_key]
                    tasks[nid] = resolved

                # Submit all ready nodes
                futures = {}
                for nid in ready:
                    gn = graph.nodes[nid]
                    future = pool.submit(
                        self._execute_node, gn, tasks[nid], context
                    )
                    futures[future] = nid

                ready = []

                for future in as_completed(futures):
                    nid = futures[future]
                    try:
                        artifact = future.result()
                        if artifact:
                            artifacts[artifact.key] = artifact
                            context.artifacts[artifact.key] = artifact
                        completed.add(nid)

                        for ds_id in downstream.get(nid, []):
                            if ds_id in in_degree:
                                in_degree[ds_id] -= 1
                                if in_degree[ds_id] == 0 and ds_id not in completed:
                                    ready.append(ds_id)

                    except Exception as exc:
                        failed[nid] = str(exc)
                        completed.add(nid)
                        logger.error("Node failed: %s — %s", nid, exc)

        # Collect results
        result: dict[str, Any] = {}
        for output_id in graph.outputs:
            gn = graph.nodes[output_id]
            spec = self._registry.get_node(graph.plugin, gn.node_name)
            if spec.output_spec:
                output_key = spec.output_spec.key
                if output_key in artifacts:
                    result[output_key] = artifacts[output_key].data

        elapsed = (time.time() - start_time) * 1000
        context.metadata["elapsed_ms"] = round(elapsed, 1)

        logger.info(
            "Graph executed: %d/%d nodes, %d failed, %.1fms",
            len(completed) - len(failed), len(graph.nodes), len(failed), elapsed,
        )

        if failed:
            first = list(failed.keys())[0]
            raise ExecutionFailedError(first, failed[first])

        return result

    def _execute_node(
        self, gn: GraphNode, resolved_inputs: dict[str, Artifact],
        context: ExecutionContext,
    ) -> Artifact:
        node = self._registry.get_node(context.plugin_name, gn.node_name)
        return node.execute(resolved_inputs, gn.params, context)
