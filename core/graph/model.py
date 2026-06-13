"""Graph: data model — first-class graph representation

Graph is the central composition unit:
  - which Node instances are used (nodes)
  - how their Artifacts connect (edges)
  - which outputs to return (outputs)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    """A Node instance placed in a graph."""
    node_id: str                    # unique within this graph ("search_1")
    node_name: str                  # registered Node name ("keyword_search")
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed edge: upstream output → downstream input."""
    from_node: str     # upstream node_id
    from_output: str   # upstream output key
    to_node: str       # downstream node_id
    to_input: str      # downstream input name


@dataclass
class Graph:
    """Complete graph description — nodes, edges, outputs."""
    plugin: str
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    def incoming_edges(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.to_node == node_id]

    def outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.from_node == node_id]

    def upstream_nodes(self, node_id: str) -> list[str]:
        return list({e.from_node for e in self.incoming_edges(node_id)})

    def downstream_nodes(self, node_id: str) -> list[str]:
        return list({e.to_node for e in self.outgoing_edges(node_id)})

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def to_dict(self) -> dict:
        return {
            "plugin": self.plugin,
            "nodes": {
                nid: {"node_name": gn.node_name, "params": gn.params}
                for nid, gn in self.nodes.items()
            },
            "edges": [
                {"from": e.from_node, "from_output": e.from_output,
                 "to": e.to_node, "to_input": e.to_input}
                for e in self.edges
            ],
            "outputs": self.outputs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Graph":
        nodes = {
            nid: GraphNode(
                node_id=nid,
                node_name=nd["node_name"],
                params=nd.get("params", {}),
            )
            for nid, nd in data["nodes"].items()
        }
        edges = [
            GraphEdge(
                from_node=e["from"], from_output=e["from_output"],
                to_node=e["to"], to_input=e["to_input"],
            )
            for e in data.get("edges", [])
        ]
        return cls(
            plugin=data["plugin"],
            nodes=nodes,
            edges=edges,
            outputs=data.get("outputs", []),
        )
