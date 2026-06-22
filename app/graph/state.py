"""
LangGraph state schema.

This is the object that flows through every node in the graph
(START -> Case Builder -> Timeline Builder -> Evidence Intelligence ->
Gap Detection -> Legal Intelligence -> Compliance Review ->
Health Scoring -> Report Generation -> END).

Design notes:

- `case` is the persisted Case Object (see app.models.case.Case).
  Every node reads `state["case"]` and returns an updated `case`.
  Nothing should mutate sibling agents' outputs directly - a node
  only writes to the fields it owns (see the "agent contracts" table
  in the README).

- `raw_input` holds *new* material for this run only (freshly
  uploaded documents / pasted text). It is NOT persisted on the
  Case - the Case Builder agent consumes it and folds the results
  into `case.raw_documents` + structured fields.

- `agent_logs` is an append-only audit trail (the "AgentRun" concept
  from the original architecture doc). Each node appends one entry.
  Using Annotated + operator.add gives LangGraph automatic list
  merging across parallel branches if we ever parallelize stages.

- `requested_report_types` lets the caller ask for specific report
  types (Stage 8) without re-running the whole pipeline - supports
  the "Generate Reports Anytime" requirement.

- `error` is a short-circuit signal: if any node sets this, the
  graph can route straight to END (or to a recovery node) instead
  of continuing the pipeline on bad data.
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from app.models.case import Case
from app.models.enums import ReportType, WorkflowStage
from app.contracts.base import AgentExecution, AgentRunLog
from app.runtime.mutation import CaseMutation


class GraphState(TypedDict, total=False):
    """
    The state object passed between LangGraph nodes.

    `total=False` so nodes can return partial updates (LangGraph
    merges them into the running state).
    """

    # The single source of truth - read and (partially) rewritten
    # by almost every node.
    case: Case

    # Transient input for this run only. Cleared/consumed by the
    # Case Builder node.
    raw_input: Optional[str]

    # Which report types Stage 8 should produce. Defaults to
    # ["investigation_report"] if empty - set in the entry node.
    requested_report_types: list[ReportType]

    # Append-only audit trail. operator.add concatenates lists
    # returned by each node instead of overwriting.
    agent_logs: Annotated[list[AgentRunLog], operator.add]

    # Append-only mutation log (MutationEngine output) - field-level
    # before/after for every substantive Case change.
    mutations: Annotated[list[CaseMutation], operator.add]

    # Append-only runtime/perf metadata (duration, tokens, model) per
    # agent run.
    executions: Annotated[list[AgentExecution], operator.add]

    # Short-circuit signal. If set, the router sends the graph to END.
    error: Optional[str]


def initial_state(
    case: Case,
    raw_input: Optional[str] = None,
    requested_report_types: Optional[list[ReportType]] = None,
) -> GraphState:
    """
    Convenience constructor for kicking off a graph run, e.g.

        state = initial_state(case, raw_input=incident_text)
        result = graph.invoke(state)
    """

    return GraphState(
        case=case,
        raw_input=raw_input,
        requested_report_types=requested_report_types
        or [ReportType.INVESTIGATION_REPORT],
        agent_logs=[],
        mutations=[],
        executions=[],
        error=None,
    )


# -----------------------------------------------------------------------
# Stage -> node name mapping, used by the graph builder and the UI to
# show "AI is currently working on: ..." progress indicators.
# -----------------------------------------------------------------------
STAGE_NODE_NAMES: dict[WorkflowStage, str] = {
    WorkflowStage.CASE_BUILDER: "case_builder",
    WorkflowStage.TIMELINE_BUILDER: "timeline_builder",
    WorkflowStage.EVIDENCE_INTELLIGENCE: "evidence_intelligence",
    WorkflowStage.GAP_DETECTION: "gap_detection",
    WorkflowStage.LEGAL_INTELLIGENCE: "legal_intelligence",
    WorkflowStage.COMPLIANCE_REVIEW: "compliance_review",
    WorkflowStage.HEALTH_SCORING: "health_scoring",
    WorkflowStage.REPORT_GENERATION: "report_generation",
}

# Linear order of the pipeline (Stage 9 "continuous updates" will later
# allow re-entering at GAP_DETECTION instead of CASE_BUILDER).
STAGE_ORDER: list[WorkflowStage] = [
    WorkflowStage.CASE_BUILDER,
    WorkflowStage.TIMELINE_BUILDER,
    WorkflowStage.EVIDENCE_INTELLIGENCE,
    WorkflowStage.GAP_DETECTION,
    WorkflowStage.GAP_ENHANCEMENT,
    WorkflowStage.LEGAL_INTELLIGENCE,
    WorkflowStage.COMPLIANCE_REVIEW,
    WorkflowStage.HEALTH_SCORING,
    WorkflowStage.REPORT_GENERATION,
]
