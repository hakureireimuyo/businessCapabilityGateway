"""Tag Alignment Plugin — matching service.

Pure business logic layer.  Receives plain Python data structures
(not Artifact types) and returns plain dict / list.

Follows the project pattern:
  - No imports from ``core.protocol``
  - All methods are @staticmethod
  - Consumes TagRepository → returns Python built-ins
"""

from ..repository.tag_repository import TagRepository


class MatchingService:
    """Pure matching logic: alias → fuzzy search → dedup → top 3.

    This is the "market_service" equivalent for the tag_alignment plugin.
    """

    @staticmethod
    def query_candidates(
        token: str,
        aliases: list[str],
        site: str,
        repo: TagRepository | None = None,
    ) -> dict:
        """Query tag candidates for a single token.

        Args:
            token: The original semantic concept.
            aliases: Alias list for fuzzy matching.
            site: Target site identifier (e.g. "pixiv", "danbooru").
            repo: Optional TagRepository (injected for testability).

        Returns:
            {
                "token": <token>,
                "candidates": [{"tag": ..., "count": ...}, ...]   # top 3
            }
        """
        if repo is None:
            repo = TagRepository()

        tags = repo.fuzzy_match(aliases, site)

        candidates = [
            {"tag": t.tag, "count": t.count}
            for t in tags[:3]
        ]

        return {
            "token": token,
            "candidates": candidates,
        }
