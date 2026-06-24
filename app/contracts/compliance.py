"""
Stage 6 - Compliance Review.

Acts as an internal auditor over the whole case plus the legal
analysis: privacy risks, admissibility, missing rights notices,
bias-sensitive statements, unsupported legal claims.
"""

from __future__ import annotations

from pydantic import Field

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import ComplianceFinding
from app.models.enums import Severity, WorkflowStage

READS: tuple[str, ...] = ("victims", "suspects", "evidence", "legal_analysis")

WRITES: tuple[str, ...] = ("compliance_findings",)


class ComplianceOutput(AgentOutput):
    agent_name = "compliance_review"
    stage = WorkflowStage.COMPLIANCE_REVIEW

    findings: list[ComplianceFinding] = Field(default_factory=list)

    @property
    def overall_risk(self) -> Severity:
        """Highest severity present, derived (not separately reported)."""
        if not self.findings:
            return Severity.LOW
        order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
        present = {f.severity for f in self.findings}
        for level in order:
            if level in present:
                return level
        return Severity.LOW

    def apply(self, case: Case) -> Case:
        case.compliance_findings = self.findings

        self.mark_complete(case, next_stage=WorkflowStage.HEALTH_SCORING)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=ComplianceOutput.agent_name,
    stage=ComplianceOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=ComplianceOutput,
    description=(
        "Audits the case and legal analysis for privacy risks, "
        "admissibility issues, missing rights documentation, and "
        "bias-sensitive statements, each with provenance."
    ),
)
