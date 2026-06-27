"""
Database setup.

Hackathon strategy: store the entire Case Object as JSONB in a single
`cases` table. This directly exploits the Pydantic schema we already
designed — no normalization, no foreign keys, no impedance mismatch.
Normalize post-hackathon if needed.

Supports both PostgreSQL (production) and SQLite (local dev / CI)
via the DATABASE_URL environment variable:

    PostgreSQL: postgresql://user:pass@localhost/crimegpt
    SQLite:     sqlite:///./crimegpt.db   (default if env var not set)
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./crimegpt.db")

# PostgreSQL needs psycopg2; SQLite is built-in.
# For SQLite we need check_same_thread=False for FastAPI's threading model.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session, always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables. Called once at startup."""
    Base.metadata.create_all(bind=engine)
