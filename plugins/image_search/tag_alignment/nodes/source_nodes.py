"""Tag Alignment Plugin — data-fetching node (no inputs, produces TagCandidateSet)"""

from typing import Any

from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec
from core.runtime.context import ExecutionContext
from plugins.image_search.tag_alignment.artifact_types import TagCandidateSet
from plugins.image_search.tag_alignment.services.matching_service import MatchingService


class TagQueryNode(Node):
    """Query tag candidates by token + aliases, return top 3 by count.

    This is the entry node for the tag_alignment plugin — it has no
    input_specs and can be used as a graph entry point.
    """

    name = "tag_query"
    plugin = "tag_alignment"
    description = (
        "Query tag candidates by token and aliases via fuzzy string matching. "
        "Returns top 3 matching tags ordered by count DESC."
    )

    input_specs = {}

    output_spec = OutputSpec(
        key="tag_candidates",
        artifact_type=TagCandidateSet,
        description="Top 3 matching tags with counts, sorted by count DESC",
    )

    parameter_specs = {
        "token": ParameterSpec(
            "token", str, required=True,
            description="Original semantic token (e.g. '双马尾')",
        ),
        "aliases": ParameterSpec(
            "aliases", list, required=True,
            description="Alias list for fuzzy matching (e.g. ['twintails', 'twin tails'])",
        ),
        "site": ParameterSpec(
            "site", str, required=True,
            description="Target site identifier (e.g. 'pixiv', 'danbooru')",
        ),
    }

    def execute(
        self,
        inputs: dict[str, Artifact],
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> Artifact:
        token = params["token"]
        aliases = params["aliases"]
        site = params["site"]

        service = MatchingService()
        result = service.query_candidates(token=token, aliases=aliases, site=site)

        return Artifact(
            key=self.output_spec.key,
            type=TagCandidateSet,
            data=result,
            produced_by=self.name,
            metadata={"token": token, "site": site},
        )
