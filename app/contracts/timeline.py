"""
Stage 2 - Timeline Builder.

Reads the Case's evidence, witnesses, and existing timeline, and
produces the refined/expanded timeline - the backbone object that
every later stage (gap detection, legal grounding) reasons over.

The agent receives the current timeline and is expected to return the
*complete* updated timeline (existing events it kept + any new events
it derived), not just a delta. This keeps `apply()` a simple replace
and avoids dedupe ambiguity.
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import TimelineEvent
from app.models.enums import WorkflowStage

READS: tuple[str, ...] = ("evidence", "witnesses", "timeline")

WRITES: tuple[str, ...] = ("timeline",)


class TimelineOutput(AgentOutput):
    agent_name = "timeline_builder"
    stage = WorkflowStage.TIMELINE_BUILDER

    timeline_events: list[TimelineEvent] = Field(default_factory=list)

    # Human-readable flags like "Event E3 has no timestamp - estimated
    # from witness statement order". Surfaced as warnings; Gap Detection
    # may later turn persistent ones into formal InvestigationGaps.
    missing_timestamps: list[str] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:
        case.timeline = self.timeline_events
        self.warnings.extend(self.missing_timestamps)

        self.mark_complete(case, next_stage=WorkflowStage.EVIDENCE_INTELLIGENCE)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=TimelineOutput.agent_name,
    stage=TimelineOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=TimelineOutput,
    description=(
        "Reads evidence/witnesses/existing timeline and returns the "
        "complete refined timeline, flagging events with missing "
        "or estimated timestamps."
    ),
)
