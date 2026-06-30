"""
Legal Readiness: starts at 100 once legal_analysis exists with at
least one statute, then deducted for unresolved HIGH/CRITICAL
compliance findings (an analysis that's legally grounded but has
serious open compliance issues isn't "ready").
"""

from __future__ import annotations

from app.models.case import Case
from app.models.enums import Severity

SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.CRITICAL: 30,
    Severity.HIGH: 20,
    Severity.MEDIUM: 10,
    Severity.LOW: 5,
}


def compute(case: Case) -> int:
    if case.legal_analysis is None or not case.legal_analysis.statutes:
        return 0

    score = 100
    for finding in case.compliance_findings:
        if finding.severity in (Severity.HIGH, Severity.CRITICAL):
            score -= SEVERITY_PENALTY[finding.severity]

    return max(0, score)


def breakdown(case: Case) -> dict:
    """Explainability: starting score + each deduction applied."""
    if case.legal_analysis is None or not case.legal_analysis.statutes:
        return {"base": 0, "reason": "no legal analysis / no statutes found", "deductions": []}

    deductions = [
        {
            "finding": f.finding,
            "severity": f.severity.value,
            "penalty": SEVERITY_PENALTY[f.severity],
        }
        for f in case.compliance_findings
        if f.severity in (Severity.HIGH, Severity.CRITICAL)
    ]
    return {"base": 100, "deductions": deductions, "score": compute(case)}
