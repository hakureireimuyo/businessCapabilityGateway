"""Tag Alignment Plugin — data access layer.

Defines the Tag dataclass (plain Python, detached from ORM) and
TagRepository backed by a per-site SQLite tag table.

Session management follows the project pattern: each query method opens a
fresh session, materialises results into plain dataclass instances, and
closes the session before returning.  Artifacts never carry ORM state.
"""

from dataclasses import dataclass

from .db import get_session
from .models import get_tag_model


@dataclass
class Tag:
    """Plain-Python tag — the "Product" equivalent for this plugin.

    All ORM rows are materialised into Tag instances before leaving the
    repository layer.
    """

    tag: str
    count: int
    site: str


class TagRepository:
    """Data access for tag fuzzy-matching queries.

    Each query method opens a fresh SQLAlchemy session, executes the query,
    materialises results to plain :class:`Tag` instances, and closes the
    session.

    Usage inside a Node's execute()::

        repo = TagRepository()
        candidates = repo.fuzzy_match(["twintails", "twin tails"], site="pixiv")
        # → list[Tag]  (sorted by count DESC, already deduplicated)
    """

    # ---- fuzzy match ----

    def fuzzy_match(
        self,
        aliases: list[str],
        site: str,
    ) -> list["Tag"]:
        """For each alias, query the site's tag table with ILIKE (case-insensitive
        substring match).  Results are deduplicated and sorted by count DESC.

        Returns:
            Plain ``Tag`` list, fully detached from the ORM session.
        """
        model = get_tag_model(site)

        session = get_session()
        try:
            collected: dict[str, Tag] = {}

            for alias in aliases:
                rows = (
                    session.query(model)
                    .filter(model.tag.ilike(f"%{alias}%"))
                    .all()
                )
                for row in rows:
                    tag = row.tag
                    count = row.count
                    # Deduplicate: keep the max count if same tag matched by
                    # multiple aliases.
                    if tag not in collected or count > collected[tag].count:
                        collected[tag] = Tag(tag=tag, count=count, site=site)

            # Sort by count DESC
            result = sorted(collected.values(), key=lambda t: t.count, reverse=True)
            return result
        finally:
            session.close()

    def get_top_tags(
        self,
        site: str,
        limit: int = 100,
    ) -> list["Tag"]:
        """Return the top *limit* tags by count for a site (global ranking).

        This is a utility method for browsing / debugging — not used in the
        normal Agent flow.
        """
        model = get_tag_model(site)

        session = get_session()
        try:
            rows = (
                session.query(model)
                .order_by(model.count.desc())
                .limit(limit)
                .all()
            )
            return [Tag(tag=r.tag, count=r.count, site=site) for r in rows]
        finally:
            session.close()
