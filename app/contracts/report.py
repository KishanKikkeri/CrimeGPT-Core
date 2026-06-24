"""
Stage 8 - Report Generation.

The only stage allowed to produce prose (Architecture Principle #2).
Reads the entire fully-enriched Case and renders it into one of the
report types (case summary, investigation report, court brief,
evidence summary, executive intelligence report).

Supports "Generate Reports Anytime" (Stage 9 continuous updates):
this can be invoked standalone against an already-analyzed Case
without re-running Stages 1-7.
"""

from __future__ import annotations

import uuid

from app.contracts.base import AgentContract, AgentOutput
from app.models.case import Case
from app.models.entities import Report
from app.models.enums import ReportType, WorkflowStage

READS: tuple[str, ...] = ("*",)  # entire enriched case

WRITES: tuple[str, ...] = ("reports",)


class ReportOutput(AgentOutput):
    agent_name = "report_generation"
    stage = WorkflowStage.REPORT_GENERATION

    report_type: ReportType
    content: str

    def apply(self, case: Case) -> Case:
        version = (
            sum(1 for r in case.reports if r.type == self.report_type) + 1
        )

        report = Report(
            report_id=f"RPT-{uuid.uuid4().hex[:8].upper()}",
            type=self.report_type,
            source_case=case.case_id,
            content=self.content,
            version=version,
        )
        case.reports.append(report)

        self.mark_complete(case, next_stage=WorkflowStage.DONE)
        case.touch()
        return case


CONTRACT = AgentContract(
    agent_name=ReportOutput.agent_name,
    stage=ReportOutput.stage,
    reads=READS,
    writes=WRITES,
    output_model=ReportOutput,
    description=(
        "Renders the fully-enriched case into prose for the requested "
        "report type. The only stage permitted to produce free text. "
        "Can be re-invoked standalone for 'generate reports anytime'."
    ),
)
