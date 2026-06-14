"""Image Search Pipeline — plugin entry point.

Aggregates all sub-plugin registrations under the image_search project.
The gateway auto-discovers plugins one-level deep under plugins/,
so this file bridges the nested tag_alignment and gallery_dl packages.
"""

from core.registry.node_registry import register_nodes
from plugins.image_search.tag_alignment.nodes.source_nodes import TagQueryNode
from plugins.image_search.gallery_dl.nodes.source_nodes import SearchUrlNode
from plugins.image_search.gallery_dl.nodes.transform_nodes import ResultRangeNode, FilterByNode
from plugins.image_search.gallery_dl.nodes.sink_nodes import DownloadNode


def register():
    """Register all image_search sub-plugin nodes with the gateway."""
    register_nodes("tag_alignment", [
        TagQueryNode(),
    ])
    register_nodes("gallery_dl", [
        SearchUrlNode(),
        ResultRangeNode(),
        FilterByNode(),
        DownloadNode(),
    ])
