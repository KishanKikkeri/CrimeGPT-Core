"""
CRUD operations for the cases table.

Everything serialises/deserialises through Case.model_dump_json() /
Case.model_validate_json() — the Pydantic schema is the contract,
the DB row is just storage.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import CaseRow
from app.models.case import Case


def _row_from_case(case: Case) -> dict:
    return {
        "case_id": case.case_id,
        "title": case.title,
        "status": case.status.value,
        "case_json": case.model_dump_json(),
    }


def create_case(db: Session, case: Case) -> CaseRow:
    row = CaseRow(**_row_from_case(case))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_case(db: Session, case_id: str) -> Case | None:
    row = db.query(CaseRow).filter(CaseRow.case_id == case_id).first()
    if row is None:
        return None
    return Case.model_validate_json(row.case_json)


def update_case(db: Session, case: Case) -> CaseRow | None:
    row = db.query(CaseRow).filter(CaseRow.case_id == case.case_id).first()
    if row is None:
        return None
    row.title = case.title
    row.status = case.status.value
    row.case_json = case.model_dump_json()
    db.commit()
    db.refresh(row)
    return row


def upsert_case(db: Session, case: Case) -> CaseRow:
    row = db.query(CaseRow).filter(CaseRow.case_id == case.case_id).first()
    if row is None:
        return create_case(db, case)
    row.title = case.title
    row.status = case.status.value
    row.case_json = case.model_dump_json()
    db.commit()
    db.refresh(row)
    return row


def delete_case(db: Session, case_id: str) -> bool:
    row = db.query(CaseRow).filter(CaseRow.case_id == case_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def list_cases(db: Session, skip: int = 0, limit: int = 50) -> list[dict]:
    """Returns lightweight summaries (no case_json) for the case list view."""
    rows = (
        db.query(CaseRow)
        .order_by(CaseRow.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "case_id": r.case_id,
            "title": r.title,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]
