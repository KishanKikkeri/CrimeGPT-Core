"""
Completeness: % of core case sections that are populated.

Deliberately simple and enumerable, so it can be shown to a judge as
a checklist, not a black box.
"""

from __future__ import annotations

from app.models.case import Case

CHECKS: dict[str, "callable"] = {
    "summary": lambda case: bool(case.summary),
    "crime_type": lambda case: bool(case.crime_type),
    "people_identified": lambda case: bool(case.victims or case.suspects),
    "witnesses": lambda case: bool(case.witnesses),
    "evidence": lambda case: bool(case.evidence),
    "timeline": lambda case: bool(case.timeline),
}


def compute(case: Case) -> int:
    results = {name: check(case) for name, check in CHECKS.items()}
    return round(100 * sum(results.values()) / len(results))


def breakdown(case: Case) -> dict[str, bool]:
    """Per-check pass/fail, for the explainability UI."""
    return {name: check(case) for name, check in CHECKS.items()}
