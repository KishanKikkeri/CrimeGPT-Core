"""
Analysis router.

POST /cases/{id}/analyze    Run the full investigation pipeline (Stages 1-8)
POST /cases/{id}/reanalyze  Re-run gap/legal/compliance/scoring on an
                             existing structured case (Stages 4-8)

Both run synchronously for the hackathon — good enough for a 1-20 second
demo. Wire to a task queue (Celery / ARQ) post-hackathon for production.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.crud import get_case, upsert_case
from app.db.database import get_db
from app.graph.builder import build_analysis_graph, build_investigation_graph
from app.graph.state import initial_state
from app.models.enums import ReportType, WorkflowStage

router = APIRouter(prefix="/cases", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    raw_input: str | None = None
    report_types: list[ReportType] = [ReportType.INVESTIGATION_REPORT]


@router.post("/{case_id}/analyze")
def analyze_case(case_id: str, body: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Full pipeline: Stages 1-8 (requires raw_input for Stage 1).
    Use this on a freshly created case.
    """
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    if not body.raw_input:
        raise HTTPException(
            status_code=422,
            detail="raw_input is required for full analysis (Stage 1 - Case Builder)",
        )

    state = initial_state(
        case,
        raw_input=body.raw_input,
        requested_report_types=body.report_types,
    )
    result = build_investigation_graph().invoke(state)

    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {result['error']}",
        )

    final_case = result["case"]
    upsert_case(db, final_case)

    return {
        "case_id": final_case.case_id,
        "status": final_case.status.value,
        "health": final_case.health.model_dump(),
        "health_overall": final_case.health.overall,
        "gaps_found": len(final_case.investigation_gaps),
        "reports_generated": len(final_case.reports),
        "stages_completed": [s.value for s in final_case.completed_stages],
        "mutations": len(result.get("mutations", [])),
        "executions": [
            {
                "agent": ex.agent_name,
                "duration_ms": ex.duration_ms,
                "confidence": ex.confidence,
                "success": ex.success,
                "model": ex.model,
            }
            for ex in result.get("executions", [])
        ],
    }


@router.post("/{case_id}/reanalyze")
def reanalyze_case(case_id: str, body: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Re-run Stages 4-8 on a case that already has structured entities.
    Useful when new evidence arrives — doesn't re-run Case Builder.
    """
    case = get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")

    state = initial_state(case, requested_report_types=body.report_types)
    result = build_analysis_graph(
        start_from=WorkflowStage.GAP_DETECTION
    ).invoke(state)

    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=f"Re-analysis error: {result['error']}",
        )

    final_case = result["case"]
    upsert_case(db, final_case)

    return {
        "case_id": final_case.case_id,
        "health_overall": final_case.health.overall,
        "gaps_found": len(final_case.investigation_gaps),
        "stages_run": [s.value for s in final_case.completed_stages],
    }
