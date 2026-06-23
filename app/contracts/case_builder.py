"""
Stage 1 - Case Builder.

Converts raw, messy input (pasted text, uploaded documents) into the
first structured pass of the Case Object: people, evidence, and an
initial timeline.
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import Evidence, Suspect, TimelineEvent, Victim, Witness
from app.models.enums import WorkflowStage

READS: tuple[str, ...] = ("raw_input",)

WRITES: tuple[str, ...] = (
    "title",
    "crime_type",
    "summary",
    "victims",
    "suspects",
    "witnesses",
    "evidence",
    "timeline",
    "raw_documents",
)


class CaseBuilderOutput(AgentOutput):
    agent_name = "case_builder"
    stage = WorkflowStage.CASE_BUILDER

    title: str
    crime_type: str | None = None
    extracted_summary: str

    victims: list[Victim] = Field(default_factory=list)
    suspects: list[Suspect] = Field(default_factory=list)
    witnesses: list[Witness] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:
        case.title = self.title
        case.crime_type = self.crime_type
        case.summary = self.extracted_summary

        case.victims = self.victims
        case.suspects = self.suspects
        case.witnesses = self.witnesses
        case.evidence = self.evidence
        case.timeline = self.timeline_events

        self.mark_complete(case, next_stage=WorkflowStage.TIMELINE_BUILDER)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=CaseBuilderOutput.agent_name,
    stage=CaseBuilderOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=CaseBuilderOutput,
    description=(
        "Converts raw incident text/documents into the first structured "
        "pass of victims, suspects, witnesses, evidence, and timeline."
    ),
)
