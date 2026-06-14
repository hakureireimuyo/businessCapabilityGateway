"""Gallery-DL Plugin — Transform nodes (GalleryTask in → GalleryTask out)."""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.image_search.gallery_dl.artifact_types import GalleryTask


def _copy_task(data: dict) -> dict:
    """Copy GalleryTask descriptor dict (shallow copy, urls list is shared)."""
    return dict(data)


class ResultRangeNode(Node):
    """Set a positional range on the gallery-dl task (--range).

    Useful for slicing: e.g. "50-150" to download only the 50th through 150th
    results from a search.
    """

    name = "result_range"
    plugin = "gallery_dl"
    description = (
        "Limit download to a positional range. "
        'Pass "50-150" to download only results 50 through 150.'
    )

    input_specs = {
        "task": InputSpec(
            name="task",
            artifact_type=GalleryTask,
            required=True,
            description="Gallery-DL task descriptor",
        ),
    }

    output_spec = OutputSpec(
        key="task",
        artifact_type=GalleryTask,
        description="Gallery-DL task descriptor (range set)",
    )

    parameter_specs = {
        "range": ParameterSpec(
            "range", str, required=True,
            description='Positional range, e.g. "50-150" or "1-200"',
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        data = _copy_task(inputs["task"].data)
        data["range"] = params["range"]

        return Artifact(
            key=self.output_spec.key,
            type=GalleryTask,
            data=data,
            produced_by=self.name,
            metadata={"range": params["range"]},
        )


class FilterByNode(Node):
    """Apply a gallery-dl --filter expression (e.g. "score:>100")."""

    name = "filter_by"
    plugin = "gallery_dl"
    description = (
        "Filter results by a gallery-dl filter expression "
        '(e.g. "score:>100", "width:>=1920", "type=1").'
    )

    input_specs = {
        "task": InputSpec(
            name="task",
            artifact_type=GalleryTask,
            required=True,
            description="Gallery-DL task descriptor",
        ),
    }

    output_spec = OutputSpec(
        key="task",
        artifact_type=GalleryTask,
        description="Gallery-DL task descriptor (filter set)",
    )

    parameter_specs = {
        "filter": ParameterSpec(
            "filter", str, required=True,
            description='Filter expression, e.g. "score:>100" or "width:>=1920"',
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        data = _copy_task(inputs["task"].data)
        data["filter"] = params["filter"]

        return Artifact(
            key=self.output_spec.key,
            type=GalleryTask,
            data=data,
            produced_by=self.name,
            metadata={"filter": params["filter"]},
        )
