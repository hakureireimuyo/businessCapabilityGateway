"""Gallery-DL Plugin — entry point.

Exposes gallery-dl capabilities as composable Gateway nodes:
  - search_url    (entry)   — create download task from search URLs
  - result_range  (transform) — slice positional range
  - filter_by     (transform) — apply filter expression
  - download      (terminal) — execute download with limit allocation

Part of the Business Capability Gateway + Tag Alignment + Gallery Pipeline.
"""

from core.registry.node_registry import register_nodes
from plugins.image_search.gallery_dl.nodes.source_nodes import SearchUrlNode
from plugins.image_search.gallery_dl.nodes.transform_nodes import ResultRangeNode, FilterByNode
from plugins.image_search.gallery_dl.nodes.sink_nodes import DownloadNode


def register():
    """Register all gallery_dl plugin nodes with the gateway."""
    register_nodes("gallery_dl", [
        SearchUrlNode(),
        ResultRangeNode(),
        FilterByNode(),
        DownloadNode(),
    ])
