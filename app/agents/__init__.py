"""
Agent function registry.

Maps each WorkflowStage to its `AgentFn` (Stages 1-7) - the graph
builder wires these into AgentExecutor-backed nodes via
`app.contracts.REGISTRY` for contract metadata.

Stage 8 (report_generation) is handled separately by the graph
builder since it can run for multiple `ReportType`s in one pass - see
`app.agents.report_agent.run(case, raw_input, report_type)`.
"""

from __future__ import annotations

from app.agents import (
    case_builder_agent,
    compliance_agent,
    evidence_agent,
    gap_agent,
    gap_enhancement_agent,
    health_agent,
    legal_agent,
    report_agent,
    timeline_agent,
)
from app.models.enums import WorkflowStage
from app.runtime.executor import AgentFn

AGENT_FUNCTIONS: dict[WorkflowStage, AgentFn] = {
    WorkflowStage.CASE_BUILDER: case_builder_agent.run,
    WorkflowStage.TIMELINE_BUILDER: timeline_agent.run,
    WorkflowStage.EVIDENCE_INTELLIGENCE: evidence_agent.run,
    WorkflowStage.GAP_DETECTION: gap_agent.run,
    WorkflowStage.GAP_ENHANCEMENT: gap_enhancement_agent.run,
    WorkflowStage.LEGAL_INTELLIGENCE: legal_agent.run,
    WorkflowStage.COMPLIANCE_REVIEW: compliance_agent.run,
    WorkflowStage.HEALTH_SCORING: health_agent.run,
}

__all__ = ["AGENT_FUNCTIONS", "report_agent"]
