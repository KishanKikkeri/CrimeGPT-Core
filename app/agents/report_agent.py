"""
Stage 8 agent function - Report Generation.

Rule-based v1: template rendering from the fully-enriched Case. This
is the *only* stage that produces prose (Architecture Principle #2) -
everything it writes comes directly from already-structured,
already-validated fields, so there's nothing left for it to "invent".

Unlike the other stages, this agent function takes an extra
`report_type` argument (bound via functools.partial in the graph
builder, since one pipeline run can request multiple report types -
"Generate Reports Anytime").

A later Claude-backed version can replace these templates with
LLM-rendered prose for a more natural read - the contract
(ReportOutput: report_type + content) doesn't change.
"""

from __future__ import annotations

from typing import Optional

from app.contracts.report import ReportOutput
from app.models.case import Case
from app.models.enums import ReportType


def _case_summary(case: Case) -> str:
    lines = [
        f"CASE SUMMARY - {case.title}",
        f"Case ID: {case.case_id}",
        f"Crime type: {case.crime_type or 'unspecified'}",
        f"Status: {case.status.value}",
        "",
        case.summary or "(no summary available)",
        "",
        f"Case Health: {case.health.overall}% "
        f"(completeness {case.health.completeness}%, "
        f"evidence integrity {case.health.evidence_integrity}%, "
        f"legal readiness {case.health.legal_readiness}%, "
        f"documentation quality {case.health.documentation_quality}%)",
        "",
        f"Victims: {len(case.victims)} | Suspects: {len(case.suspects)} | "
        f"Witnesses: {len(case.witnesses)} | Evidence: {len(case.evidence)} | "
        f"Timeline events: {len(case.timeline)}",
        f"Open investigation gaps: {len(case.investigation_gaps)} "
        f"({sum(1 for g in case.investigation_gaps if g.severity.value in ('high', 'critical'))} high/critical)",
    ]
    return "\n".join(lines)


def _investigation_report(case: Case) -> str:
    lines = [f"INVESTIGATION REPORT - {case.title}", f"Case ID: {case.case_id}", ""]

    lines.append("PEOPLE")
    for v in case.victims:
        lines.append(f"  Victim {v.id}: {v.name or 'unnamed'}")
    for s in case.suspects:
        lines.append(f"  Suspect {s.id}: {s.description or 'undescribed'} (status: {s.status.value})")
    for w in case.witnesses:
        rel = f", reliability {w.reliability_score.confidence:.0%}" if w.reliability_score else ""
        lines.append(f"  Witness {w.id}{rel}: {(w.statement or '')[:120]}")
    lines.append("")

    lines.append("TIMELINE")
    for e in case.timeline:
        ts = e.timestamp.strftime("%H:%M") if e.timestamp else "??:??"
        lines.append(f"  [{ts}] {e.event_id}: {e.description}")
    lines.append("")

    lines.append("EVIDENCE")
    for ev in case.evidence:
        lines.append(f"  {ev.evidence_id} ({ev.type.value}): {ev.title} - admissibility: {ev.admissibility_status.value}")
    lines.append("")

    lines.append("INVESTIGATION GAPS")
    for g in case.investigation_gaps:
        lines.append(f"  [{g.severity.value.upper()}] {g.category.value}: {g.description}")
        lines.append(f"    -> {g.recommendation}")
    lines.append("")

    if case.legal_analysis:
        lines.append("LEGAL ANALYSIS")
        for statute in case.legal_analysis.statutes:
            lines.append(f"  - {statute}")
        for req in case.legal_analysis.procedural_requirements:
            lines.append(f"  Procedural requirement: {req}")
        lines.append("")

    lines.append("COMPLIANCE FINDINGS")
    for f in case.compliance_findings:
        lines.append(f"  [{f.severity.value.upper()}] {f.category.value}: {f.finding}")
        lines.append(f"    -> {f.recommendation}")

    return "\n".join(lines)


def _court_brief(case: Case) -> str:
    lines = [f"COURT BRIEF - {case.title}", f"Case ID: {case.case_id}", ""]

    lines.append("SUMMARY OF FACTS")
    lines.append(case.summary or "(no summary available)")
    lines.append("")

    lines.append("ADMISSIBLE EVIDENCE")
    admissible = [e for e in case.evidence if e.admissibility_status.value == "admissible"]
    if not admissible:
        lines.append("  (none currently marked admissible)")
    for ev in admissible:
        lines.append(f"  {ev.evidence_id}: {ev.title}")
    lines.append("")

    lines.append("APPLICABLE LAW")
    if case.legal_analysis:
        for statute in case.legal_analysis.statutes:
            lines.append(f"  - {statute}")
        for prec in case.legal_analysis.precedents:
            lines.append(f"  Precedent: {prec}")
    else:
        lines.append("  (no legal analysis available)")
    lines.append("")

    lines.append("OUTSTANDING COMPLIANCE ISSUES")
    open_findings = [f for f in case.compliance_findings if f.severity.value in ("high", "critical")]
    if not open_findings:
        lines.append("  (none)")
    for f in open_findings:
        lines.append(f"  [{f.severity.value.upper()}] {f.finding}")

    return "\n".join(lines)


def _evidence_summary(case: Case) -> str:
    lines = [f"EVIDENCE SUMMARY - {case.title}", ""]
    for ev in case.evidence:
        lines.append(f"{ev.evidence_id}: {ev.title} ({ev.type.value})")
        lines.append(f"  Source: {ev.source or 'unknown'}")
        lines.append(f"  Admissibility: {ev.admissibility_status.value}")
        lines.append(f"  Chain of custody entries: {len(ev.chain_of_custody)}")
        lines.append(f"  Linked people: {', '.join(ev.linked_people) or 'none'}")
        lines.append(f"  Linked timeline events: {', '.join(ev.linked_events) or 'none'}")
        lines.append("")
    return "\n".join(lines)


def _executive_intelligence_report(case: Case) -> str:
    critical_gaps = [g for g in case.investigation_gaps if g.severity.value in ("high", "critical")]
    lines = [
        f"EXECUTIVE INTELLIGENCE REPORT - {case.title}",
        f"Case Readiness: {case.health.overall}%",
        "",
        "CRITICAL ISSUES",
    ]
    if not critical_gaps:
        lines.append("  (none identified)")
    for g in critical_gaps:
        lines.append(f"  - {g.description}")

    lines.append("")
    lines.append("RECOMMENDED NEXT STEPS")
    if not case.investigation_gaps:
        lines.append("  - No open gaps. Case is ready for legal review.")
    for g in case.investigation_gaps:
        lines.append(f"  - {g.recommendation}")

    return "\n".join(lines)


_TEMPLATES = {
    ReportType.CASE_SUMMARY: _case_summary,
    ReportType.INVESTIGATION_REPORT: _investigation_report,
    ReportType.COURT_BRIEF: _court_brief,
    ReportType.EVIDENCE_SUMMARY: _evidence_summary,
    ReportType.EXECUTIVE_INTELLIGENCE_REPORT: _executive_intelligence_report,
}


def run(case: Case, raw_input: Optional[str], report_type: ReportType) -> ReportOutput:
    template = _TEMPLATES[report_type]
    return ReportOutput(confidence=0.95, report_type=report_type, content=template(case))
