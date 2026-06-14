"""Database connection management for the tag_alignment plugin.

Engine is a module-level singleton.
Sessions are created per-query and must be closed in the repository layer.

Database file: plugins/image_search/data/tags.db
Each site gets its own table: {site}_tags (tag TEXT PK, count INT)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Resolve database path relative to this file's location:
#   plugins/image_search/tag_alignment/repository/db.py
#   → plugins/image_search/tag_alignment/
#   → plugins/image_search/
#   → data/tags.db
_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(_PLUGIN_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "tags.db")

# Ensure the data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

_engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Session:
    """Create a new SQLAlchemy session.

    Caller is responsible for closing the session after use.
    """
    return SessionLocal()


def get_engine():
    """Return the module-level engine (used for table creation)."""
    return _engine
