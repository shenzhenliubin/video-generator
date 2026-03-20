"""
Database Storage - SQLAlchemy Setup

Database models and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class Database:
    """Database connection manager."""

    def __init__(self, url: str) -> None:
        self.engine = create_engine(url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
