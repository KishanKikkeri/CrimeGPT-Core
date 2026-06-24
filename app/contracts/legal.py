"""
Stage 5 - Legal Intelligence.

Runs *after* the facts are structured (crime_type, evidence, timeline)
- mirroring a real investigation where legal grounding follows fact
gathering. Retrieves relevant statutes/precedents/procedural
requirements from the curated legal knowledge base (RAG).
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import LegalAnalysis, Provenance
from app.models.enums import WorkflowStage

READS: tuple[str, ...] = ("crime_type", "evidence", "timeline")

WRITES: tuple[str, ...] = ("legal_analysis",)


class LegalOutput(AgentOutput):
    agent_name = "legal_intelligence"
    stage = WorkflowStage.LEGAL_INTELLIGENCE

    statutes: list[str] = Field(default_factory=list)
    precedents: list[str] = Field(default_factory=list)
    procedural_requirements: list[str] = Field(default_factory=list)

    # Which retrieved source documents (from the legal knowledge base)
    # grounded this analysis - feeds Provenance.derived_from.
    source_documents: list[str] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:
        case.legal_analysis = LegalAnalysis(
            statutes=self.statutes,
            precedents=self.precedents,
            procedural_requirements=self.procedural_requirements,
            confidence=self.confidence,
            provenance=Provenance(
                derived_from=self.source_documents,
                method="rag_retrieval",
                confidence=self.confidence,
            ),
        )

        self.mark_complete(case, next_stage=WorkflowStage.COMPLIANCE_REVIEW)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=LegalOutput.agent_name,
    stage=LegalOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=LegalOutput,
    description=(
        "Retrieves relevant statutes, precedents, and procedural "
        "requirements grounded in the case's crime_type, evidence, "
        "and timeline, citing source documents from the legal "
        "knowledge base."
    ),
)
