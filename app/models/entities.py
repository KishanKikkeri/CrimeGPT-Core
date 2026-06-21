"""
Entity models that compose the Case Object.

Design rules baked into this file (per the architecture decisions):

1. Agents never invent confidence/reliability numbers out of thin air.
   Every score is paired with a `source` field explaining where it
   came from (a document, a rule, a cross-reference) so the system
   stays auditable and legally defensible.

2. These are pure data containers. No business logic lives here -
   that belongs in services / agents that read and write them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    AdmissibilityStatus,
    ComplianceCategory,
    EvidenceType,
    GapCategory,
    ReportType,
    Severity,
    SuspectStatus,
)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Victim(BaseModel):
    id: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    injuries: Optional[str] = None
    statement: Optional[str] = None


class Suspect(BaseModel):
    id: str
    name: Optional[str] = None
    known_aliases: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    status: SuspectStatus = SuspectStatus.UNKNOWN

    linked_evidence: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)


class ReliabilityScore(BaseModel):
    """
    Never AI-invented in isolation. `source` must point to *why* this
    score exists (e.g. "corroborated by CCTV Camera 3", "no corroboration
    found"). `confidence` is the model's confidence in that assessment.
    """

    source: str
    confidence: float = Field(ge=0.0, le=1.0)


class Witness(BaseModel):
    id: str
    name: Optional[str] = None
    contact: Optional[str] = None
    reliability_score: Optional[ReliabilityScore] = None
    statement: Optional[str] = None


# ---------------------------------------------------------------------------
# Evidence & Chain of Custody
# ---------------------------------------------------------------------------

class CustodyEntry(BaseModel):
    timestamp: datetime
    holder: str
    action: str
    location: Optional[str] = None


class Evidence(BaseModel):
    evidence_id: str
    type: EvidenceType = EvidenceType.OTHER
    title: str
    description: Optional[str] = None

    source: Optional[str] = None
    collected_by: Optional[str] = None
    collected_at: Optional[datetime] = None

    chain_of_custody: list[CustodyEntry] = Field(default_factory=list)

    linked_people: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)

    admissibility_status: AdmissibilityStatus = AdmissibilityStatus.PENDING


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    """
    The most important object in the system. Everything else
    (gap detection, contradictions, legal grounding) reasons over
    this list.
    """

    event_id: str
    timestamp: Optional[datetime] = None
    description: str

    source: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    linked_people: list[str] = Field(default_factory=list)
    linked_evidence: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Provenance / Explainability
# ---------------------------------------------------------------------------

class Provenance(BaseModel):
    """
    Attaches "why does the system believe this" to a finding.

    `derived_from` holds IDs of the Case sub-objects that produced this
    finding - e.g. ["W1", "EV3"] (witness W1 + evidence item EV3), or
    ["E2", "E5"] (two timeline events that contradict each other).

    `method` is a short machine-readable tag describing *how* the
    finding was produced, e.g. "cross_reference", "rule:custody_chain",
    "llm_extraction". This is what lets the UI render:

        Contradiction found.
        Source A: Witness Statement #2
        Source B: CCTV Camera #3
        Confidence: 91%

    instead of an unexplained "AI says there is a contradiction."
    """

    derived_from: list[str] = Field(default_factory=list)
    method: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Legal Analysis
# ---------------------------------------------------------------------------

class LegalAnalysis(BaseModel):
    statutes: list[str] = Field(default_factory=list)
    precedents: list[str] = Field(default_factory=list)
    procedural_requirements: list[str] = Field(default_factory=list)

    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # What facts of the case (crime_type, specific timeline events,
    # evidence types) the statute/precedent selection was grounded in.
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# Investigation Gaps (flagship feature)
# ---------------------------------------------------------------------------

class InvestigationGap(BaseModel):
    id: str
    severity: Severity
    category: GapCategory

    description: str
    recommendation: str

    # Every gap must explain itself: which case objects triggered it, and how.
    provenance: Provenance

    # Claude-generated enrichment (populated by GAP_ENHANCEMENT stage).
    # None until that stage runs — detection never depends on Claude.
    ai_analysis: Optional[str] = None       # narrative: why this matters legally
    ai_recommendation: Optional[str] = None # specific copilot next action


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

class ComplianceFinding(BaseModel):
    severity: Severity
    category: ComplianceCategory
    finding: str
    recommendation: str

    provenance: Provenance


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class Report(BaseModel):
    report_id: str
    type: ReportType

    generated_at: datetime = Field(default_factory=datetime.utcnow)

    source_case: str  # case_id this report was generated from
    content: str  # rendered markdown/text - the only place prose lives

    version: int = 1


# ---------------------------------------------------------------------------
# Case Health (rule-based, not AI-scored)
# ---------------------------------------------------------------------------

class CaseHealth(BaseModel):
    """
    All four sub-scores are computed via deterministic rules
    (see app.services.health_scoring), never by asking an LLM
    "how healthy is this case from 0-100?".
    """

    completeness: int = Field(ge=0, le=100, default=0)
    evidence_integrity: int = Field(ge=0, le=100, default=0)
    legal_readiness: int = Field(ge=0, le=100, default=0)
    documentation_quality: int = Field(ge=0, le=100, default=0)

    @property
    def overall(self) -> int:
        """
        Weighted score - see app.scoring.weights.HEALTH_WEIGHTS for the
        exact formula (completeness*0.35 + evidence_integrity*0.25 +
        legal_readiness*0.20 + documentation_quality*0.20). Imported
        locally to avoid a module-load-time circular import with
        app.scoring (which itself operates on Case/CaseHealth).
        """
        from app.scoring.weights import HEALTH_WEIGHTS

        weighted = (
            self.completeness * HEALTH_WEIGHTS["completeness"]
            + self.evidence_integrity * HEALTH_WEIGHTS["evidence_integrity"]
            + self.legal_readiness * HEALTH_WEIGHTS["legal_readiness"]
            + self.documentation_quality * HEALTH_WEIGHTS["documentation_quality"]
        )
        return round(weighted)
