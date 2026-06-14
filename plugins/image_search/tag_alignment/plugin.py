"""Tag Alignment Plugin — entry point.

Provides the tag_query node: fuzzy-match user tokens against
per-site tag tables and return top-3 candidates ordered by count.

Part of the Business Capability Gateway + Tag Alignment + Gallery Pipeline.
"""

from core.registry.node_registry import register_nodes
from plugins.image_search.tag_alignment.nodes.source_nodes import TagQueryNode


def register():
    """Register all tag_alignment plugin nodes with the gateway."""
    register_nodes("tag_alignment", [
        TagQueryNode(),
    ])
