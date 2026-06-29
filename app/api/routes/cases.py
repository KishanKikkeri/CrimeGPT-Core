"""
Cases router.

POST /cases        Create a new case from raw incident text
GET  /cases        List all cases (summaries)
GET  /cases/{id}   Get the full Case Object
DELETE /cases/{id} Delete a case
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.crud import create_case, delete_case, get_case, list_cases
from app.db.database import get_db
from app.models.case import Case

router = APIRouter(prefix="/cases", tags=["cases"])


class CreateCaseRequest(BaseModel):
    title: str = "Untitled Case"
    raw_input: str | None = None
    jurisdiction: str | None = None
    crime_type: str | None = None


@router.post("", status_code=201)
def create_new_case(body: CreateCaseRequest, db: Session = Depends(get_db)):
    """
    Create a new Case. Stores it immediately so the UI can show it
    while analysis runs asynchronously (POST /cases/{id}/analyze).
    """
    case = Case(
        title=body.title,
        jurisdiction=body.jurisdiction,
        crime_type=body.crime_type,
    )
    row = create_case(db, case)
    return {
        "case_id": case.case_id,
        "title": case.title,
        "status": case.status.value,
        "created_at": row.created_at.isoformat(),
        "_raw_input": body.raw_input,  # passed to /analyze
    }


@router.get("")
def get_all_cases(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return list_cases(db, skip=skip, limit=limit)


@router.get("/{case_id}")
def get_one_case(case_id: str, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")
    return case.model_dump(mode="json")


@router.delete("/{case_id}", status_code=204)
def remove_case(case_id: str, db: Session = Depends(get_db)):
    if not delete_case(db, case_id):
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")
