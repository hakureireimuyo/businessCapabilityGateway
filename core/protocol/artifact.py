"""Protocol: Artifact type system — data contract between nodes"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


class ArtifactType:
    """Base class for all Artifact types.

    Plugins define their type hierarchy by subclassing.
    Type compatibility uses issubclass: a subtype can flow into
    any input that expects a supertype.
    """
    pass


@dataclass
class Artifact:
    """Runtime artifact instance — the data that flows between nodes.

    Each Node.execute() returns exactly one Artifact.
    GraphExecutor stores produced Artifacts in ExecutionContext.artifacts
    and resolves them as inputs for downstream nodes.
    """
    key: str                      # storage key (matches Node.output_spec.key)
    type: type[ArtifactType]      # concrete ArtifactType subclass
    data: Any                     # the actual business data
    produced_by: str              # node name that produced this
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InputSpec:
    """Protocol: a single input that a Node declares it consumes."""
    name: str
    artifact_type: type[ArtifactType]
    required: bool = True
    description: str = ""


@dataclass
class OutputSpec:
    """Protocol: the single output that a Node produces.

    Each Node has exactly one output. Multi-output needs are met
    by splitting into separate nodes.
    """
    key: str
    artifact_type: type[ArtifactType]
    description: str = ""


@dataclass
class ParameterSpec:
    """Protocol: a single literal parameter that a Node accepts."""
    name: str
    param_type: type
    required: bool = False
    default: Any = None
    description: str = ""
