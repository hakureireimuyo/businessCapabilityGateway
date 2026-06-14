"""Gallery-DL Plugin — Download node (GalleryTask → DownloadResult).

This is the terminal node: it actually executes gallery-dl and handles
the per-URL limit allocation + deficit redistribution.
"""

import math
from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.image_search.gallery_dl.artifact_types import GalleryTask, DownloadResult
from plugins.image_search.gallery_dl.services.download_service import (
    DownloadTask,
    execute_download,
)


class DownloadNode(Node):
    """Execute gallery-dl download.

    Internally handles:
      - Total limit → per-URL evenly divided allocation
      - Deficit redistribution when a URL exhausts before its allocation
      - Merging project-level fixed config with per-request params
    """

    name = "download"
    plugin = "gallery_dl"
    description = (
        "Execute gallery-dl download. "
        "Total limit is evenly divided across URLs. "
        "If a URL exhausts, remaining quota is redistributed to other URLs."
    )

    input_specs = {
        "task": InputSpec(
            name="task",
            artifact_type=GalleryTask,
            required=True,
            description="Gallery-DL task descriptor (accumulated params)",
        ),
    }

    output_spec = OutputSpec(
        key="download_result",
        artifact_type=DownloadResult,
        description="Download execution summary: total, files, per-URL stats",
    )

    parameter_specs = {
        "limit": ParameterSpec(
            "limit", int, required=False, default=None,
            description="Total download limit evenly divided across URLs",
        ),
        "simulate": ParameterSpec(
            "simulate", bool, required=False, default=False,
            description="If true, run gallery-dl -s (dry-run, no actual download)",
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        task_data = inputs["task"].data
        task = DownloadTask(
            urls=list(task_data.get("urls", [])),
            limit=params.get("limit"),
            range=task_data.get("range"),
            filter_expr=task_data.get("filter"),
            simulate=params.get("simulate", False),
        )

        result = execute_download(task)

        return Artifact(
            key=self.output_spec.key,
            type=DownloadResult,
            data=result,
            produced_by=self.name,
            metadata={
                "total_downloaded": result.get("total_downloaded", 0),
                "total_limit": task.limit,
                "url_count": len(task.urls),
            },
        )
