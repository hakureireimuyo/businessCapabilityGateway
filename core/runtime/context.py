"""Runtime: ExecutionContext — transient data carrier for one graph execution"""

import uuid
from datetime import datetime, timezone
from typing import Any

from ..protocol.artifact import Artifact


class ExecutionContext:
    """Global execution context for a single graph execution.

    Carries:
      - artifacts: all Artifacts produced so far (output_key → Artifact)
      - outputs: final output data (output_key → raw data)
      - metadata: request-level info (request_id, plugin, timestamps)

    No pipeline fields — execution order is determined by dependency
    resolution in GraphExecutor, not by linear position.
    """

    def __init__(self, plugin_name: str = ""):
        self.request_id: str = uuid.uuid4().hex[:12]
        self.plugin_name: str = plugin_name
        self.artifacts: dict[str, Artifact] = {}   # output_key → Artifact
        self.outputs: dict[str, Any] = {}           # output_key → final raw data
        self.metadata: dict[str, Any] = {
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
