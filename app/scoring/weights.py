"""
Weights for the overall Case Health score.

These are the numbers a judge can be shown directly:

    overall = completeness * 0.35
            + evidence_integrity * 0.25
            + legal_readiness * 0.20
            + documentation_quality * 0.20

Kept in their own zero-dependency module so both `app.models.entities`
(CaseHealth.overall) and `app.contracts.health` can import them without
any risk of circular imports.
"""

HEALTH_WEIGHTS: dict[str, float] = {
    "completeness": 0.35,
    "evidence_integrity": 0.25,
    "legal_readiness": 0.20,
    "documentation_quality": 0.20,
}

assert abs(sum(HEALTH_WEIGHTS.values()) - 1.0) < 1e-9, "HEALTH_WEIGHTS must sum to 1.0"
