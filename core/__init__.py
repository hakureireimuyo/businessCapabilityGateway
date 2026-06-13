"""Business Capability Gateway — Core v2.0

Protocol-based architecture: Node + immediate execution.

Modules:
  core.protocol    — Node protocol and Artifact type system
  core.registry    — Node registration and capability discovery
  core.runtime     — Execution context and response helpers
  core.plugin      — Plugin auto-discovery and loading
  core.sandbox     — AST validation and sandbox execution
  core.exceptions  — Gateway exception hierarchy
"""

from .protocol.artifact import ArtifactType, Artifact, InputSpec, OutputSpec, ParameterSpec
from .protocol.node import Node
from .registry.node_registry import NodeRegistry, get_registry, register_nodes
from .runtime.context import ExecutionContext
from .runtime.response import ActionResult
from .plugin.loader import discover_and_load_plugins
