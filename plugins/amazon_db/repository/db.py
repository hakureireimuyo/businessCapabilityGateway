"""Database connection management for the amazon_db plugin.

The engine is a module-level singleton.
Sessions are created per-query and must be closed in the repository layer.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Resolve database path relative to this file's location:
#   plugins/amazon_db/repository/db.py  →  ../../..  →  project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.path.join(_PROJECT_ROOT, "database", "database.db")

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Session:
    """Create a new SQLAlchemy session.

    Caller is responsible for closing the session after use.
    """
    return SessionLocal()
