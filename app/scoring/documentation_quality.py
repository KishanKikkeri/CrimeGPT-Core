"""
Documentation Quality: starts at 100, deducted per open
DOCUMENTATION-category InvestigationGap, weighted by severity.
"""

from __future__ import annotations

from app.models.case import Case
from app.models.enums import GapCategory, Severity

SEVERITY_PENALTY: dict[Severity, int] = {
    Severity.CRITICAL: 30,
    Severity.HIGH: 20,
    Severity.MEDIUM: 10,
    Severity.LOW: 5,
}


def compute(case: Case) -> int:
    score = 100
    for gap in case.investigation_gaps:
        if gap.category == GapCategory.DOCUMENTATION_GAP:
            score -= SEVERITY_PENALTY.get(gap.severity, 5)
    return max(0, score)


def breakdown(case: Case) -> dict:
    deductions = [
        {
            "gap_id": g.id,
            "description": g.description,
            "severity": g.severity.value,
            "penalty": SEVERITY_PENALTY.get(g.severity, 5),
        }
        for g in case.investigation_gaps
        if g.category == GapCategory.DOCUMENTATION_GAP
    ]
    return {"base": 100, "deductions": deductions, "score": compute(case)}
