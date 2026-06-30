"""
Deterministic, rule-based Case Health scoring.

    from app.scoring import compute_all, compute_overall

    health = compute_all(case)          # -> CaseHealth
    overall = compute_overall(health)   # -> int (weighted)

Every sub-score has a matching `breakdown(case)` function in its
module for the explainability UI ("why is legal_readiness only 70%?").
"""

from __future__ import annotations

from app.models.case import Case
from app.models.entities import CaseHealth
from app.scoring import (
    completeness,
    documentation_quality,
    evidence_integrity,
    legal_readiness,
)
from app.scoring.weights import HEALTH_WEIGHTS


def compute_all(case: Case) -> CaseHealth:
    return CaseHealth(
        completeness=completeness.compute(case),
        evidence_integrity=evidence_integrity.compute(case),
        legal_readiness=legal_readiness.compute(case),
        documentation_quality=documentation_quality.compute(case),
    )


def compute_overall(health: CaseHealth) -> int:
    """
    Weighted overall score. This is the single number shown on the
    Case dashboard, and the formula behind it is exactly:

        completeness * 0.35
        + evidence_integrity * 0.25
        + legal_readiness * 0.20
        + documentation_quality * 0.20
    """
    weighted = sum(
        getattr(health, field) * weight for field, weight in HEALTH_WEIGHTS.items()
    )
    return round(weighted)


def explain(case: Case) -> dict:
    """Full breakdown of every sub-score, for an explainability panel."""
    health = compute_all(case)
    return {
        "overall": compute_overall(health),
        "weights": HEALTH_WEIGHTS,
        "completeness": completeness.breakdown(case),
        "evidence_integrity": evidence_integrity.breakdown(case),
        "legal_readiness": legal_readiness.breakdown(case),
        "documentation_quality": documentation_quality.breakdown(case),
    }


__all__ = [
    "compute_all",
    "compute_overall",
    "explain",
    "HEALTH_WEIGHTS",
    "completeness",
    "evidence_integrity",
    "legal_readiness",
    "documentation_quality",
]
