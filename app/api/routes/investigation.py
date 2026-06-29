"""
Focused read routers: reports, timeline, gaps, health.

GET /cases/{id}/timeline
GET /cases/{id}/gaps
GET /cases/{id}/health
GET /cases/{id}/reports
POST /cases/{id}/reports  (generate-on-demand)
GET /cases/{id}/reports/{report_id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.crud import get_case, upsert_case
from app.db.database import get_db
from app.graph.builder import build_report_only_graph
from app.graph.state import initial_state
from app.models.enums import ReportType
from app.scoring import explain

router = APIRouter(prefix="/cases", tags=["investigation"])


# ── Timeline ─────────────────────────────────────────────────────────

@router.get("/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    return {
        "case_id": case_id,
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "description": e.description,
                "source": e.source,
                "confidence": e.confidence,
                "linked_people": e.linked_people,
                "linked_evidence": e.linked_evidence,
            }
            for e in case.timeline
        ],
        "total": len(case.timeline),
    }


# ── Gaps ──────────────────────────────────────────────────────────────

@router.get("/{case_id}/gaps")
def get_gaps(
    case_id: str,
    severity: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    gaps = case.investigation_gaps
    if severity:
        gaps = [g for g in gaps if g.severity.value == severity.lower()]
    if category:
        gaps = [g for g in gaps if g.category.value == category.lower()]

    return {
        "case_id": case_id,
        "total": len(gaps),
        "by_severity": {
            "critical": sum(1 for g in case.investigation_gaps if g.severity.value == "critical"),
            "high": sum(1 for g in case.investigation_gaps if g.severity.value == "high"),
            "medium": sum(1 for g in case.investigation_gaps if g.severity.value == "medium"),
            "low": sum(1 for g in case.investigation_gaps if g.severity.value == "low"),
        },
        "gaps": [
            {
                "id": g.id,
                "severity": g.severity.value,
                "category": g.category.value,
                "description": g.description,
                "recommendation": g.recommendation,
                "provenance": {
                    "derived_from": g.provenance.derived_from,
                    "method": g.provenance.method,
                    "confidence": g.provenance.confidence,
                    "notes": g.provenance.notes,
                },
            }
            for g in gaps
        ],
    }


# ── Health ────────────────────────────────────────────────────────────

@router.get("/{case_id}/health")
def get_health(case_id: str, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    return {
        "case_id": case_id,
        "overall": case.health.overall,
        "sub_scores": case.health.model_dump(),
        "weights": {
            "completeness": 0.35,
            "evidence_integrity": 0.25,
            "legal_readiness": 0.20,
            "documentation_quality": 0.20,
        },
        "breakdown": explain(case),
    }


# ── Reports ───────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    report_type: ReportType = ReportType.INVESTIGATION_REPORT


@router.get("/{case_id}/reports")
def list_reports(case_id: str, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    return {
        "case_id": case_id,
        "reports": [
            {
                "report_id": r.report_id,
                "type": r.type.value,
                "version": r.version,
                "generated_at": r.generated_at.isoformat(),
            }
            for r in case.reports
        ],
    }


@router.post("/{case_id}/reports", status_code=201)
def generate_report(
    case_id: str, body: GenerateReportRequest, db: Session = Depends(get_db)
):
    """Generate a new report on demand without re-running the full pipeline."""
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    state = initial_state(case, requested_report_types=[body.report_type])
    result = build_report_only_graph().invoke(state)

    final_case = result["case"]
    upsert_case(db, final_case)

    newest = final_case.reports[-1]
    return {
        "report_id": newest.report_id,
        "type": newest.type.value,
        "version": newest.version,
        "content": newest.content,
    }


@router.get("/{case_id}/reports/{report_id}")
def get_report(case_id: str, report_id: str, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(404, f"Case {case_id!r} not found")

    report = next((r for r in case.reports if r.report_id == report_id), None)
    if report is None:
        raise HTTPException(404, f"Report {report_id!r} not found")

    return {
        "report_id": report.report_id,
        "type": report.type.value,
        "version": report.version,
        "generated_at": report.generated_at.isoformat(),
        "content": report.content,
    }
