"""
ORM model for the cases table.

One row = one Case. The entire Case Object is stored as JSON in
`case_json`. We index on `status` for filtering and `created_at`
for sorting — that's all we need for the hackathon.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CaseRow(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="Untitled Case")
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)

    # The entire Case pydantic model serialised as JSON. SQLAlchemy uses
    # Text here (works for both SQLite and Postgres). For Postgres you'd
    # want JSONB with GIN index — swap Text -> JSON after the hackathon.
    case_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
