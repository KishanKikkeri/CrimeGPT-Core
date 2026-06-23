"""
Stage 3 - Evidence Intelligence.

Not forensic analysis - evidence *organization*. Links evidence items
to the people/events they support, flags admissibility concerns, and
surfaces gaps (e.g. "photo evidence lacks a timestamp") for Stage 4
(Gap Detection) to formalize.

Note: the original sketch had `linked_evidence: dict`. We use a typed
`EvidenceLink` list instead so `apply()` can validate evidence_ids
against `case.evidence` and the output stays schema-checked.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.enums import AdmissibilityStatus, WorkflowStage

READS: tuple[str, ...] = ("evidence", "timeline")

WRITES: tuple[str, ...] = ("evidence",)  # specifically: linking + admissibility fields


class EvidenceLink(BaseModel):
    evidence_id: str
    linked_people: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)
    admissibility_status: AdmissibilityStatus | None = None
    admissibility_note: str | None = None


class EvidenceOutput(AgentOutput):
    agent_name = "evidence_intelligence"
    stage = WorkflowStage.EVIDENCE_INTELLIGENCE

    evidence_links: list[EvidenceLink] = Field(default_factory=list)

    # e.g. "CCTV supports witness statement", "Fingerprint evidence
    # unlinked", "Photo evidence lacks timestamp"
    evidence_gaps: list[str] = Field(default_factory=list)
    admissibility_warnings: list[str] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:
        by_id = {e.evidence_id: e for e in case.evidence}

        for link in self.evidence_links:
            ev = by_id.get(link.evidence_id)
            if ev is None:
                self.warnings.append(
                    f"evidence_intelligence referenced unknown evidence_id "
                    f"'{link.evidence_id}' - skipped"
                )
                continue

            if link.linked_people:
                ev.linked_people = link.linked_people
            if link.linked_events:
                ev.linked_events = link.linked_events
            if link.admissibility_status is not None:
                ev.admissibility_status = link.admissibility_status

        self.warnings.extend(self.evidence_gaps)
        self.warnings.extend(self.admissibility_warnings)

        self.mark_complete(case, next_stage=WorkflowStage.GAP_DETECTION)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=EvidenceOutput.agent_name,
    stage=EvidenceOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=EvidenceOutput,
    description=(
        "Links evidence items to people/events, flags admissibility "
        "concerns, and surfaces organizational gaps for Gap Detection."
    ),
)
