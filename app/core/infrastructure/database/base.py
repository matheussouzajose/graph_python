"""Declarative base shared by every ORM model.

Every table (SQLAlchemy model) in the project must inherit from `Base`.
Alembic reads `Base.metadata` to know which tables should exist, so a
model only shows up in migrations if its module is imported (see
`migrations/env.py`).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
