"""
Evidence Integrity: % of evidence items with a documented chain of
custody that are not flagged INADMISSIBLE.

Returns 0 (not 100) when there is no evidence at all - "no evidence"
is not "perfect evidence integrity".
"""

from __future__ import annotations

from app.models.case import Case
from app.models.enums import AdmissibilityStatus


def compute(case: Case) -> int:
    if not case.evidence:
        return 0

    ok = sum(
        1
        for e in case.evidence
        if e.chain_of_custody and e.admissibility_status != AdmissibilityStatus.INADMISSIBLE
    )
    return round(100 * ok / len(case.evidence))


def breakdown(case: Case) -> list[dict]:
    """Per-item pass/fail, for the explainability UI."""
    return [
        {
            "evidence_id": e.evidence_id,
            "has_custody_chain": bool(e.chain_of_custody),
            "admissibility_status": e.admissibility_status.value,
            "ok": bool(e.chain_of_custody)
            and e.admissibility_status != AdmissibilityStatus.INADMISSIBLE,
        }
        for e in case.evidence
    ]
