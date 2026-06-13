"""Protocol: Node base class — the protocol implementation unit

Each Node is a protocol implementation unit. It declares:
  - input_specs:    what Artifacts it consumes
  - output_spec:    what Artifact it produces (single)
  - parameter_specs: what literal parameters it accepts

There is no NodeType. Whether a node acts as a "source" (no inputs),
"transform" (in+out of same type), or "sink" (final output) is
determined by its position in a specific graph, not by a class label.
"""

from abc import ABC, abstractmethod
from typing import Any

from .artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from ..runtime.context import ExecutionContext


class Node(ABC):
    """Protocol implementation unit exposed by plugins to the gateway.

    Subclasses declare their protocol via class attributes and implement
    execute() as a function: inputs + params → output Artifact.

    Constraints:
      - Must be stateless (each execute() call independent).
      - Must not call other nodes directly.
      - Must not access external state (database OK through Repository).
    """

    name: str = ""                             # unique within plugin
    plugin: str = ""                           # owning plugin domain
    description: str = ""                      # one-line English description

    input_specs: dict[str, InputSpec] = {}     # inputs this node consumes
    output_spec: OutputSpec | None = None      # single output this node produces
    parameter_specs: dict[str, ParameterSpec] = {}  # literal parameters

    @abstractmethod
    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        """Execute this node's business logic.

        Args:
            inputs: Resolved input Artifacts, keyed by input name.
            params: Resolved literal parameter values with defaults applied.
            context: Global execution context (read metadata, do NOT
                     write to context.artifacts — the executor does that).

        Returns:
            The Artifact produced by this node.
        """
        ...

    def to_spec_dict(self) -> dict[str, Any]:
        """Generate API-friendly node specification for capability discovery."""
        spec: dict[str, Any] = {
            "name": self.name,
            "plugin": self.plugin,
            "description": self.description,
            "input_specs": {
                name: {
                    "artifact_type": s.artifact_type.__name__,
                    "required": s.required,
                    "description": s.description,
                }
                for name, s in self.input_specs.items()
            },
            "output_spec": {
                "key": self.output_spec.key,
                "artifact_type": self.output_spec.artifact_type.__name__,
                "description": self.output_spec.description,
            } if self.output_spec else None,
            "parameter_specs": {
                name: {
                    "type": s.param_type.__name__,
                    "required": s.required,
                    "default": s.default,
                    "description": s.description,
                }
                for name, s in self.parameter_specs.items()
            },
        }
        return spec
