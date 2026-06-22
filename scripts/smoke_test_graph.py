"""
Smoke test: proves the Case Object + GraphState schema actually works
end-to-end with LangGraph using a couple of stub nodes.

Run with:  python -m scripts.smoke_test_graph
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.models import (
    Case,
    Suspect,
    SuspectStatus,
    TimelineEvent,
    Victim,
    WorkflowStage,
    Witness,
)
from app.graph.state import AgentRunLog, GraphState, initial_state


# ---------------------------------------------------------------------
# Stub nodes - each represents one agent. Real implementations will
# call Claude with a structured-output prompt instead of hardcoding
# values, but the *shape* of input/output is identical.
# ---------------------------------------------------------------------

def case_builder_node(state: GraphState) -> dict:
    case = state["case"]
    raw = state.get("raw_input") or ""

    # Pretend the LLM extracted these from `raw`.
    case.title = "Residential Burglary - Rear Window Entry"
    case.crime_type = "burglary"
    case.victims.append(Victim(id="V1", name="Unknown Resident"))
    case.suspects.append(
        Suspect(id="S1", description="Masked individual", status=SuspectStatus.UNKNOWN)
    )
    case.witnesses.append(Witness(id="W1", statement="Saw a masked person at the rear window"))
    case.timeline.append(
        TimelineEvent(
            event_id="E1",
            description="Witness observed suspect entering through rear window",
            source="witness_statement",
            confidence=0.8,
        )
    )
    case.raw_documents.append(raw)
    case.status = case.status  # unchanged here, set by orchestrator if needed
    case.mark_stage_complete(WorkflowStage.CASE_BUILDER)
    case.current_stage = WorkflowStage.TIMELINE_BUILDER

    return {
        "case": case,
        "agent_logs": [
            AgentRunLog(
                agent="case_builder",
                stage=WorkflowStage.CASE_BUILDER,
                notes="Extracted 1 victim, 1 suspect, 1 witness, 1 timeline event",
            )
        ],
    }


def timeline_builder_node(state: GraphState) -> dict:
    case = state["case"]

    case.timeline.append(
        TimelineEvent(
            event_id="E2",
            description="Patrol unit arrived on scene",
            source="dispatch_log",
            confidence=0.95,
        )
    )
    case.mark_stage_complete(WorkflowStage.TIMELINE_BUILDER)
    case.current_stage = WorkflowStage.DONE  # short pipeline for this smoke test

    return {
        "case": case,
        "agent_logs": [
            AgentRunLog(
                agent="timeline_builder",
                stage=WorkflowStage.TIMELINE_BUILDER,
                notes="Added 1 timeline event from dispatch log",
            )
        ],
    }


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("case_builder", case_builder_node)
    graph.add_node("timeline_builder", timeline_builder_node)

    graph.add_edge(START, "case_builder")
    graph.add_edge("case_builder", "timeline_builder")
    graph.add_edge("timeline_builder", END)

    return graph.compile()


def main():
    case = Case(title="Untitled Case")
    state = initial_state(
        case,
        raw_input=(
            "A witness observed a masked individual entering the residence "
            "through a rear window at approximately 2:03 AM."
        ),
    )

    app_graph = build_graph()
    result = app_graph.invoke(state)

    final_case: Case = result["case"]

    print("=== Final Case ===")
    print(final_case.model_dump_json(indent=2))

    print("\n=== Agent Logs ===")
    for log in result["agent_logs"]:
        print(f"- [{log.stage.value}] {log.agent}: {log.notes}")


if __name__ == "__main__":
    main()
