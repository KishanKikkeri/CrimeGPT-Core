"""
Stage 4.5 — Gap Enhancement (Claude-backed).

Runs after deterministic Gap Detection. Claude reads the HIGH/CRITICAL
investigation gaps and the case context, then adds:

  gap.ai_analysis         — 2-3 sentence narrative explaining WHY this
                             gap matters legally and investigatively
  gap.ai_recommendation   — specific copilot next action, naming the
                             actual evidence/witness/procedure involved

Design principle: detection is deterministic (reliable, auditable);
explanation is Claude (intelligent, human-readable). Both layers are
labelled in the output so judges and users know which is which.

If no ANTHROPIC_API_KEY is configured or the API call fails, the stage
runs as a no-op: gaps stay as-is with rule-based recommendations only.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import InvestigationGap
from app.models.enums import WorkflowStage

READS: tuple[str, ...] = ("investigation_gaps", "timeline", "evidence", "witnesses", "suspects")

WRITES: tuple[str, ...] = ("investigation_gaps",)


class GapEnhancementOutput(AgentOutput):
    agent_name = "gap_enhancement"
    stage = WorkflowStage.GAP_ENHANCEMENT

    enhanced_gaps: list[InvestigationGap] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:
        if self.enhanced_gaps:
            case.investigation_gaps = self.enhanced_gaps

        self.mark_complete(case, next_stage=WorkflowStage.LEGAL_INTELLIGENCE)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=GapEnhancementOutput.agent_name,
    stage=GapEnhancementOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=GapEnhancementOutput,
    description=(
        "Claude enriches HIGH/CRITICAL investigation gaps with narrative "
        "analysis (why it matters legally) and specific copilot "
        "recommendations (what to do right now). No-op if no API key."
    ),
)
