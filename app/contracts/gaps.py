"""
Stage 4 - Investigation Gap Detection.

The flagship feature: reads the *entire* Case (timeline, evidence,
witnesses, suspects) and surfaces missing evidence, contradictions,
procedural gaps, documentation gaps, and legal gaps - each with a
`Provenance` explaining exactly which case objects triggered it.

Severity counts are exposed as computed properties (derived from
`investigation_gaps`) rather than separately-reported fields, so they
can never drift out of sync with the actual gap list - consistent
with "Case Health Score is rule-based, not separately invented".
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import InvestigationGap
from app.models.enums import Severity, WorkflowStage

READS: tuple[str, ...] = (
    "victims",
    "suspects",
    "witnesses",
    "evidence",
    "timeline",
)

WRITES: tuple[str, ...] = ("investigation_gaps",)


class GapDetectionOutput(AgentOutput):
    agent_name = "gap_detection"
    stage = WorkflowStage.GAP_DETECTION

    investigation_gaps: list[InvestigationGap] = Field(default_factory=list)

    @property
    def critical_gaps(self) -> int:
        return sum(1 for g in self.investigation_gaps if g.severity == Severity.CRITICAL)

    @property
    def high_gaps(self) -> int:
        return sum(1 for g in self.investigation_gaps if g.severity == Severity.HIGH)

    @property
    def medium_gaps(self) -> int:
        return sum(1 for g in self.investigation_gaps if g.severity == Severity.MEDIUM)

    @property
    def low_gaps(self) -> int:
        return sum(1 for g in self.investigation_gaps if g.severity == Severity.LOW)

    def apply(self, case: Case) -> Case:
        case.investigation_gaps = self.investigation_gaps

        self.mark_complete(case, next_stage=WorkflowStage.LEGAL_INTELLIGENCE)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=GapDetectionOutput.agent_name,
    stage=GapDetectionOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=GapDetectionOutput,
    description=(
        "Reads the entire case and produces InvestigationGap objects "
        "(missing evidence, contradictions, procedure, documentation, "
        "legal) each with provenance pointing to the triggering "
        "evidence/timeline/witness records."
    ),
)
