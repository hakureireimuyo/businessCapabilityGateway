"""SDK: ArtifactPlaceholder — represents the future output of a node call"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.protocol.artifact import ArtifactType


@dataclass(frozen=True)
class ArtifactPlaceholder:
    """Returned by Graph node method calls.

    Represents the future output of a Node instance placed in the graph.
    When passed as a keyword argument to another node call, the SDK
    automatically creates a GraphEdge connecting the two nodes.

    Attributes:
        _node_id: Unique node instance ID in this graph (e.g. "keyword_search_1").
        _output_key: The output_spec.key of the producing node (e.g. "products").
        _artifact_type: The ArtifactType subclass this placeholder carries.
    """

    _node_id: str
    _output_key: str
    _artifact_type: "type[ArtifactType]"

    def __repr__(self) -> str:
        return (
            f"ArtifactPlaceholder(node={self._node_id!r}, "
            f"output={self._output_key!r}, "
            f"type={self._artifact_type.__name__})"
        )
