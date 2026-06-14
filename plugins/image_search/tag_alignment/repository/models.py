"""SQLAlchemy ORM model for tag tables.

Design:
  - TagBase is abstract — not mapped to any table.
  - Each site gets a concrete subclass created on demand via get_tag_model(site).
  - Table naming: {site}_tags  (e.g. pixiv_tags, danbooru_tags)
  - Schema: tag TEXT PRIMARY KEY, count INTEGER
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TagBase(Base):
    """Abstract base for per-site tag tables.  Not mapped directly."""

    __abstract__ = True

    tag: Mapped[str] = mapped_column(String(500), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, index=True)

    def __repr__(self):
        return f"Tag(tag={self.tag!r}, count={self.count})"


# ---- cached per-site model classes ----

_site_models: dict[str, type[TagBase]] = {}


def get_tag_model(site: str) -> type[TagBase]:
    """Return the ORM model class for *site*'s tag table.

    The class is created on first access and cached; subsequent calls for
    the same site return the identical class.  The table is registered with
    ``Base.metadata`` so ``Base.metadata.create_all()`` will create it.
    """
    if site in _site_models:
        return _site_models[site]

    table_name = f"{site}_tags"
    cls = type(
        f"Tag_{site}",
        (TagBase,),
        {"__tablename__": table_name},
    )
    _site_models[site] = cls
    return cls
