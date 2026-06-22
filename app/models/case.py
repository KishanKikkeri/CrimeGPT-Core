"""
The Case Object - the single source of truth for CrimeGPT.

Architecture Principle #1: Agents do not talk to each other.
Agents read from and write to this object only.

Architecture Principle #2: Past the structuring stages, agents
output structured data into these fields - never prose. Only
Report.content (see entities.py) contains free text.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import CasePriority, CaseStatus, WorkflowStage
from app.models.entities import (
    CaseHealth,
    Evidence,
    InvestigationGap,
    LegalAnalysis,
    ComplianceFinding,
    Report,
    Suspect,
    TimelineEvent,
    Victim,
    Witness,
)


def _new_case_id() -> str:
    return f"CASE-{datetime.utcnow():%Y}-{uuid.uuid4().hex[:6].upper()}"


class Case(BaseModel):
    # --- Identity ------------------------------------------------------
    case_id: str = Field(default_factory=_new_case_id)
    title: str = "Untitled Case"
    status: CaseStatus = CaseStatus.CREATED
    priority: CasePriority = CasePriority.MEDIUM
    jurisdiction: Optional[str] = None
    crime_type: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # --- Narrative -------------------------------------------------------
    summary: Optional[str] = None

    # --- Raw inputs (kept for traceability / re-analysis) ---------------
    raw_documents: list[str] = Field(default_factory=list)

    # --- Core entities ----------------------------------------------------
    victims: list[Victim] = Field(default_factory=list)
    suspects: list[Suspect] = Field(default_factory=list)
    witnesses: list[Witness] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)

    # --- Analysis outputs --------------------------------------------------
    legal_analysis: Optional[LegalAnalysis] = None
    investigation_gaps: list[InvestigationGap] = Field(default_factory=list)
    compliance_findings: list[ComplianceFinding] = Field(default_factory=list)

    # --- Outputs -------------------------------------------------------
    reports: list[Report] = Field(default_factory=list)

    # --- Scoring ---------------------------------------------------------
    health: CaseHealth = Field(default_factory=CaseHealth)

    # --- Workflow tracking ------------------------------------------------
    current_stage: WorkflowStage = WorkflowStage.CASE_CREATED
    completed_stages: list[WorkflowStage] = Field(default_factory=list)

    # -----------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------
    def touch(self) -> None:
        """Call after any mutation so updated_at stays accurate."""
        self.updated_at = datetime.utcnow()

    def mark_stage_complete(self, stage: WorkflowStage) -> None:
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)
        self.touch()

    class Config:
        # Allows population by field name when partial updates come
        # back from agents as dicts.
        validate_assignment = True
