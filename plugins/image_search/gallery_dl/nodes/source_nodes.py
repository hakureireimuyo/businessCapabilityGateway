"""Gallery-DL Plugin — Entry node (no inputs, produces GalleryTask)."""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.image_search.gallery_dl.artifact_types import GalleryTask


def _new_task(urls: list[str]) -> dict:
    """Create a new GalleryTask descriptor dict."""
    return {"urls": list(urls), "range": None, "filter": None}


class SearchUrlNode(Node):
    """Create a gallery-dl download task from one or more search URLs.

    This is the entry node for the gallery_dl plugin — it has no input_specs.
    URLs typically come from the Layer 3 tag→URL conversion output.
    """

    name = "search_url"
    plugin = "gallery_dl"
    description = (
        "Create a gallery-dl download task from search URLs. "
        "Typically fed from the tag_alignment URL builder output."
    )

    input_specs = {}

    output_spec = OutputSpec(
        key="task",
        artifact_type=GalleryTask,
        description="Gallery-DL task descriptor (urls populated)",
    )

    parameter_specs = {
        "urls": ParameterSpec(
            "urls", list, required=True,
            description="List of search URLs from tag_alignment URL builder",
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        urls = params["urls"]
        data = _new_task(urls)

        return Artifact(
            key=self.output_spec.key,
            type=GalleryTask,
            data=data,
            produced_by=self.name,
            metadata={"url_count": len(urls)},
        )
