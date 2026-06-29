"""
Investigation Engine smoke test.

Demonstrates, end-to-end, with the *real* LangGraph builder
(app.graph.builder):

  1. Streaming progress events ("Building Case", "Detecting
     Contradictions", ...) - the UI progress list.
  2. The full Stage 1-8 pipeline running on raw incident text via the
     case_builder heuristic fallback (no ANTHROPIC_API_KEY needed).
  3. The mutation log (MutationEngine) - field-level before/after per
     agent, and a rollback example.
  4. `build_report_only_graph()` - generating an additional report
     type without re-running Stages 1-7 ("generate reports anytime").

Run with:  python -m scripts.smoke_test_runtime
"""

from __future__ import annotations

from app.graph.builder import build_investigation_graph, build_report_only_graph
from app.graph.state import initial_state
from app.models import Case, ReportType
from app.runtime import MutationEngine

RAW_INPUT = (
    "A witness observed a masked individual entering the residence "
    "through a rear window at approximately 2:03 AM. CCTV footage "
    "shows the suspect near the window at 2:16 AM. Police arrived at "
    "the scene at 2:30 AM."
)

_PROGRESS_LABELS = {
    "case_builder": "Building Case",
    "timeline_builder": "Constructing Timeline",
    "evidence_intelligence": "Organizing Evidence",
    "gap_detection": "Detecting Investigation Gaps",
    "legal_intelligence": "Running Legal Analysis",
    "compliance_review": "Checking Compliance",
    "health_scoring": "Calculating Case Readiness",
    "report_generation": "Generating Reports",
}


def run_pipeline_with_progress(state) -> dict:
    """Single graph execution: stream for progress output, accumulate
    the merged final state ourselves (mirrors LangGraph's own
    reducers: 'case'/'error' = last value, list fields = concatenated)."""

    graph = build_investigation_graph()

    accumulated: dict = dict(state)
    accumulated.setdefault("agent_logs", [])
    accumulated.setdefault("mutations", [])
    accumulated.setdefault("executions", [])

    print("=== Streaming Progress ===")
    for update in graph.stream(state, stream_mode="updates"):
        for node_name, partial in update.items():
            label = _PROGRESS_LABELS.get(node_name, node_name)
            for log in partial.get("agent_logs", []):
                status_icon = "x" if log.status == "error" else "v"
                print(f"  [{status_icon}] {label}")
                if log.notes:
                    print(f"      note: {log.notes}")

            if "case" in partial:
                accumulated["case"] = partial["case"]
            if "error" in partial:
                accumulated["error"] = partial["error"]
            for list_field in ("agent_logs", "mutations", "executions"):
                accumulated[list_field] = accumulated.get(list_field, []) + partial.get(list_field, [])

    return accumulated


def main() -> None:
    case = Case(title="Untitled Case")
    state = initial_state(case, raw_input=RAW_INPUT)

    result = run_pipeline_with_progress(state)
    case = result["case"]

    if result.get("error"):
        print(f"\nPipeline stopped with error: {result['error']}")
        return

    print("\n=== Case Readiness ===")
    print(f"Case Readiness: {case.health.overall}%")
    print(
        f"  completeness={case.health.completeness}  "
        f"evidence_integrity={case.health.evidence_integrity}  "
        f"legal_readiness={case.health.legal_readiness}  "
        f"documentation_quality={case.health.documentation_quality}"
    )

    print("\n=== Investigation Gaps ===")
    for g in case.investigation_gaps:
        print(f"  [{g.severity.value.upper()}] ({g.category.value}) {g.description}")
        print(f"      derived_from={g.provenance.derived_from} via {g.provenance.method}")
        print(f"      -> {g.recommendation}")

    print("\n=== Agent Executions (audit trail) ===")
    for ex in result["executions"]:
        status = "ok" if ex.success else f"ERROR: {ex.error}"
        print(
            f"  {ex.agent_name:<22} {ex.duration_ms:>5}ms  "
            f"conf={ex.confidence:.2f}  model={ex.model}  [{status}]"
        )

    print(f"\n=== Mutation Log ({len(result['mutations'])} mutations) ===")
    for m in result["mutations"]:
        print(f"  {m.field:<22} <- {m.source_agent} ({m.stage.value})")

    # ------------------------------------------------------------
    # Rollback demo: undo, then redo, the gap_detection mutation to
    # investigation_gaps. Proves the rollback mechanism without
    # disturbing the rest of the demo.
    # ------------------------------------------------------------
    print("\n=== Rollback Demo ===")
    gap_mutation = next(m for m in result["mutations"] if m.field == "investigation_gaps")
    before_count = len(case.investigation_gaps)
    case = MutationEngine.rollback(case, gap_mutation)
    print(f"Before rollback: {before_count} investigation gaps")
    print(
        f"After rollback:  {len(case.investigation_gaps)} investigation gaps "
        f"(mutation review_status={gap_mutation.review_status})"
    )

    # Redo: rollback restores `before`, so a second rollback with
    # before/after swapped restores the gaps for the rest of the demo.
    gap_mutation.before, gap_mutation.after = gap_mutation.after, gap_mutation.before
    case = MutationEngine.rollback(case, gap_mutation)
    print(f"After redo:      {len(case.investigation_gaps)} investigation gaps")

    print("\n=== Generated Reports ===")
    for r in case.reports:
        print(f"--- {r.type.value} (v{r.version}) ---")
        print(r.content)
        print()

    # ------------------------------------------------------------
    # "Generate reports anytime": run report-only graph for a new
    # report type, without re-running Stages 1-7.
    # ------------------------------------------------------------
    print("=== Generate Reports Anytime (report-only graph) ===")
    reports_before = len(case.reports)
    report_graph = build_report_only_graph()
    report_state = initial_state(
        case, requested_report_types=[ReportType.EXECUTIVE_INTELLIGENCE_REPORT]
    )
    report_result = report_graph.invoke(report_state)
    new_case: Case = report_result["case"]

    print(f"Total reports now: {len(new_case.reports)} (was {reports_before})")
    newest = new_case.reports[-1]
    print(f"--- {newest.type.value} (v{newest.version}) ---")
    print(newest.content)


if __name__ == "__main__":
    main()
