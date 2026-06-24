"""
Stage 7 - Case Health Scoring.

Unlike the other stages, this is **rule-based, not LLM-based** (per
the architecture decision: "Not using AI"). The actual scoring rules
live in `app.scoring` (one module per sub-score, each with a
`breakdown()` for explainability) - this contract just wraps that
package so it fits the same pipeline shape as every other stage.

`confidence` is always 1.0 since the scores are deterministic.
"""

from __future__ import annotations

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import CaseHealth
from app.models.enums import WorkflowStage
from app.scoring import compute_all

READS: tuple[str, ...] = ("*",)  # entire case, rule-based

WRITES: tuple[str, ...] = ("health",)


class HealthScoringOutput(AgentOutput):
    agent_name = "health_scoring"
    stage = WorkflowStage.HEALTH_SCORING

    health: CaseHealth

    @classmethod
    def compute(cls, case: Case) -> "HealthScoringOutput":
        return cls(confidence=1.0, health=compute_all(case))

    def apply(self, case: Case) -> Case:
        case.health = self.health

        self.mark_complete(case, next_stage=WorkflowStage.REPORT_GENERATION)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=HealthScoringOutput.agent_name,
    stage=HealthScoringOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=HealthScoringOutput,
    description=(
        "Deterministic, rule-based scoring of completeness, evidence "
        "integrity, legal readiness, and documentation quality "
        "(see app.scoring for the formulas). Not LLM-based - call "
        "HealthScoringOutput.compute(case)."
    ),
)
