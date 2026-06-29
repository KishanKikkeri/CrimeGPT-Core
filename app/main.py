"""
CrimeGPT FastAPI Application.

Start with:
    uvicorn app.main:app --reload

Interactive docs:
    http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cases, analysis, investigation
from app.db.database import create_tables

app = FastAPI(
    title="CrimeGPT API",
    description="AI Investigation Copilot — Documentation, Legal Research, Report Generation",
    version="0.1.0",
)

# Allow the React frontend (dev server on :3000 or :5173) to call the API.
# Lock this down to specific origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(analysis.router)
app.include_router(investigation.router)


@app.on_event("startup")
def startup():
    create_tables()

    # Seed the demo burglary case so the UI has data immediately
    # without needing to run the demo script first.
    if os.environ.get("SEED_DEMO", "true").lower() == "true":
        _seed_demo_case()


def _seed_demo_case() -> None:
    """
    Seeds the flagship burglary demo case so the UI loads with
    real investigation data on first start.

    Skipped if a case with the same title already exists.
    """
    from sqlalchemy.orm import Session
    from app.db.database import SessionLocal
    from app.db.models import CaseRow
    from app.db.crud import upsert_case
    from app.graph.builder import build_analysis_graph
    from app.graph.state import initial_state
    from app.models.enums import WorkflowStage
    from data.burglary.case_factory import build_burglary_case

    db: Session = SessionLocal()
    try:
        existing = db.query(CaseRow).filter(
            CaseRow.title == "Residential Burglary — 14 Maple Street, Greenfields"
        ).first()
        if existing:
            return

        case = build_burglary_case()
        case.mark_stage_complete(WorkflowStage.CASE_BUILDER)
        case.current_stage = WorkflowStage.TIMELINE_BUILDER

        state = initial_state(case)
        graph = build_analysis_graph(start_from=WorkflowStage.TIMELINE_BUILDER)
        result = graph.invoke(state)

        if not result.get("error"):
            upsert_case(db, result["case"])
    except Exception as exc:
        print(f"[WARN] Demo seed failed (non-fatal): {exc}")
    finally:
        db.close()


@app.get("/", tags=["meta"])
def root():
    return {
        "product": "CrimeGPT",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
