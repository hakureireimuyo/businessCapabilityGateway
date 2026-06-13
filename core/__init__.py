"""Business Capability Gateway — Core v2.0

Protocol-based architecture: Node + Graph (DAG), not linear pipeline.

Modules:
  core.protocol    — Node protocol and Artifact type system
  core.graph       — Graph model, validation, and execution
  core.registry    — Node registration and capability discovery
  core.runtime     — Execution context and response helpers
  core.plugin      — Plugin auto-discovery and loading
"""

# Re-export most-used symbols for backward compatibility
from .protocol.artifact import ArtifactType, Artifact, InputSpec, OutputSpec, ParameterSpec
from .protocol.node import Node
from .graph.model import Graph, GraphNode, GraphEdge
from .graph.validator import GraphValidator
from .graph.executor import GraphExecutor
from .registry.node_registry import NodeRegistry, get_registry, register_nodes
from .runtime.context import ExecutionContext
from .runtime.response import ActionResult
from .plugin.loader import discover_and_load_plugins
