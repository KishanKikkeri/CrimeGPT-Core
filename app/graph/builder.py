"""
The real Investigation Graph.

    graph = build_investigation_graph()
    result = graph.invoke(initial_state(case, raw_input=incident_text))

Each node:
  1. Looks up its AgentFn from `app.agents.AGENT_FUNCTIONS` (or, for
     report generation, `app.agents.report_agent`).
  2. Runs it via `AgentExecutor`, which applies the result through
     `MutationEngine` (contract-validated Case mutation + audit
     records).
  3. Returns a partial GraphState update - LangGraph merges
     `agent_logs` / `mutations` / `executions` via `operator.add`.

Error handling: if a node's execution fails, `AgentExecutor` returns
`run_log.status == "error"`. The node sets `state["error"]` and a
conditional edge routes straight to END instead of continuing the
pipeline on a bad/incomplete Case.

Two graphs are exposed:

  - `build_investigation_graph()` - the full Stage 1-8 pipeline.
  - `build_report_only_graph()` - just Stage 8, for "generate reports
    anytime" against an already-analyzed Case (Stage 9 / continuous
    updates, without re-running Stages 1-7).
"""

from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.agents import AGENT_FUNCTIONS, report_agent
from app.contracts import REGISTRY
from app.graph.state import GraphState, STAGE_ORDER
from app.models.enums import WorkflowStage
from app.runtime.executor import AgentExecutor

# Model name recorded on AgentExecution per stage - lets the UI/audit
# trail show which stages are LLM-backed vs rule-based.
_STAGE_MODEL_NAMES: dict[WorkflowStage, str] = {
    WorkflowStage.CASE_BUILDER: "claude-sonnet-4-6 (heuristic fallback if no API key)",
    WorkflowStage.TIMELINE_BUILDER: "rule-based-v1",
    WorkflowStage.EVIDENCE_INTELLIGENCE: "rule-based-v1",
    WorkflowStage.GAP_DETECTION: "rule-based-v1",
    WorkflowStage.GAP_ENHANCEMENT: "claude-sonnet-4-6 (no-op if no API key)",
    WorkflowStage.LEGAL_INTELLIGENCE: "rule-based-v1 (mock knowledge base)",
    WorkflowStage.COMPLIANCE_REVIEW: "rule-based-v1",
    WorkflowStage.HEALTH_SCORING: "rule-based",
    WorkflowStage.REPORT_GENERATION: "template-v1",
}


def _node_name(stage: WorkflowStage) -> str:
    return REGISTRY[stage].agent_name


def _make_node(stage: WorkflowStage):
    """Build a LangGraph node function for a Stage 1-7 agent."""

    agent_fn = AGENT_FUNCTIONS[stage]
    executor = AgentExecutor(model_name=_STAGE_MODEL_NAMES[stage])

    def node(state: GraphState) -> dict:
        case = state["case"]
        raw_input = state.get("raw_input")

        result = executor.run(case, stage, agent_fn, raw_input=raw_input)

        update: dict = {
            "case": result.case,
            "agent_logs": [result.run_log],
            "mutations": result.mutations,
            "executions": [result.execution],
        }
        if result.run_log.status == "error":
            update["error"] = result.execution.error or f"{_node_name(stage)} failed"

        return update

    return node


def _make_report_node():
    """
    Build the Stage 8 node. Iterates over `requested_report_types`,
    running one AgentExecutor pass per type (each appends one Report
    to case.reports).
    """

    executor = AgentExecutor(model_name=_STAGE_MODEL_NAMES[WorkflowStage.REPORT_GENERATION])

    def node(state: GraphState) -> dict:
        case = state["case"]
        raw_input = state.get("raw_input")
        report_types = state.get("requested_report_types") or []

        run_logs = []
        mutations = []
        executions = []
        error = None

        for report_type in report_types:
            agent_fn = partial(report_agent.run, report_type=report_type)
            result = executor.run(case, WorkflowStage.REPORT_GENERATION, agent_fn, raw_input=raw_input)

            case = result.case
            run_logs.append(result.run_log)
            mutations.extend(result.mutations)
            executions.append(result.execution)

            if result.run_log.status == "error":
                error = result.execution.error or "report_generation failed"
                break

        update: dict = {
            "case": case,
            "agent_logs": run_logs,
            "mutations": mutations,
            "executions": executions,
        }
        if error:
            update["error"] = error

        return update

    return node


def _route_on_error(next_node: str):
    """Conditional edge: go to END if `state['error']` is set, else continue."""

    def router(state: GraphState) -> str:
        return END if state.get("error") else next_node

    return router


def build_investigation_graph():
    """
    The full Stage 1-8 pipeline:

        START -> case_builder -> timeline_builder -> evidence_intelligence
        -> gap_detection -> legal_intelligence -> compliance_review
        -> health_scoring -> report_generation -> END

    Any stage error short-circuits straight to END.
    """

    graph = StateGraph(GraphState)

    for stage in STAGE_ORDER[:-1]:  # all but report_generation
        graph.add_node(_node_name(stage), _make_node(stage))

    graph.add_node(_node_name(WorkflowStage.REPORT_GENERATION), _make_report_node())

    graph.add_edge(START, _node_name(STAGE_ORDER[0]))

    for current_stage, next_stage in zip(STAGE_ORDER, STAGE_ORDER[1:]):
        graph.add_conditional_edges(
            _node_name(current_stage),
            _route_on_error(_node_name(next_stage)),
            {_node_name(next_stage): _node_name(next_stage), END: END},
        )

    graph.add_conditional_edges(
        _node_name(STAGE_ORDER[-1]),
        _route_on_error(END),
        {END: END},
    )

    return graph.compile()


def build_analysis_graph(start_from: WorkflowStage = WorkflowStage.TIMELINE_BUILDER):
    """
    Stages 2-8 (or any subset starting from `start_from`), for Cases
    where Stage 1 (Case Builder) has already run.

    This serves two purposes:
      - Intelligence tests: case_factory pre-builds the Case, run
        Stages 2-8 against it.
      - Continuous updates (Stage 9): new evidence arrives -> re-enter
        at GAP_DETECTION without re-running case_builder or
        timeline_builder.

    Usage:
        graph = build_analysis_graph()                          # Stages 2-8
        graph = build_analysis_graph(WorkflowStage.GAP_DETECTION) # Stages 4-8
    """
    stages = STAGE_ORDER[STAGE_ORDER.index(start_from):]

    graph = StateGraph(GraphState)

    for stage in stages[:-1]:  # all but report_generation
        graph.add_node(_node_name(stage), _make_node(stage))

    graph.add_node(_node_name(WorkflowStage.REPORT_GENERATION), _make_report_node())

    graph.add_edge(START, _node_name(stages[0]))

    for current_stage, next_stage in zip(stages, stages[1:]):
        graph.add_conditional_edges(
            _node_name(current_stage),
            _route_on_error(_node_name(next_stage)),
            {_node_name(next_stage): _node_name(next_stage), END: END},
        )

    graph.add_conditional_edges(
        _node_name(stages[-1]),
        _route_on_error(END),
        {END: END},
    )

    return graph.compile()
    """
    Stage 8 only - "generate reports anytime" against an
    already-analyzed Case, without re-running Stages 1-7.

        START -> report_generation -> END
    """

    graph = StateGraph(GraphState)
    graph.add_node(_node_name(WorkflowStage.REPORT_GENERATION), _make_report_node())
    graph.add_edge(START, _node_name(WorkflowStage.REPORT_GENERATION))
    graph.add_edge(_node_name(WorkflowStage.REPORT_GENERATION), END)
    return graph.compile()


def build_report_only_graph():
    """
    Stage 8 only - "generate reports anytime" against an
    already-analyzed Case, without re-running Stages 1-7.

        START -> report_generation -> END
    """

    graph = StateGraph(GraphState)
    graph.add_node(_node_name(WorkflowStage.REPORT_GENERATION), _make_report_node())
    graph.add_edge(START, _node_name(WorkflowStage.REPORT_GENERATION))
    graph.add_edge(_node_name(WorkflowStage.REPORT_GENERATION), END)
    return graph.compile()
