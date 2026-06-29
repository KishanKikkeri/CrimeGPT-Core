"""
Stage 6 agent function - Compliance Review.

Rule-based v1 - acts as an internal auditor over the case + legal
analysis:

  1. ADMISSIBILITY: any evidence not marked ADMISSIBLE.
  2. DOCUMENTATION: any witness with a statement but no reliability
     assessment.
  3. RIGHTS: any DETAINED/ARRESTED suspect - flagged as a reminder to
     document that rights notices were given (we have no dedicated
     field for this yet; this is a placeholder check).

A later Claude-backed version can add semantic checks (bias-sensitive
language, unsupported claims in `summary` vs `legal_analysis`) on top
of these - both contribute to the same `compliance_findings` list.
"""

from __future__ import annotations

from typing import Optional

from app.contracts.compliance import ComplianceOutput
from app.models.case import Case
from app.models.entities import ComplianceFinding, Provenance
from app.models.enums import AdmissibilityStatus, ComplianceCategory, Severity, SuspectStatus


def run(case: Case, raw_input: Optional[str]) -> ComplianceOutput:
    findings: list[ComplianceFinding] = []

    for ev in case.evidence:
        if ev.admissibility_status != AdmissibilityStatus.ADMISSIBLE:
            findings.append(
                ComplianceFinding(
                    severity=Severity.HIGH,
                    category=ComplianceCategory.ADMISSIBILITY,
                    finding=(
                        f"Evidence {ev.evidence_id} ('{ev.title}') is not currently "
                        f"admissible (status: {ev.admissibility_status.value})."
                    ),
                    recommendation="Resolve admissibility concerns before citing this evidence in any report.",
                    provenance=Provenance(
                        derived_from=[ev.evidence_id],
                        method="rule:admissibility_status",
                        confidence=0.95,
                    ),
                )
            )

    for w in case.witnesses:
        if w.statement and w.reliability_score is None:
            findings.append(
                ComplianceFinding(
                    severity=Severity.MEDIUM,
                    category=ComplianceCategory.DOCUMENTATION,
                    finding=f"Witness {w.id} has a recorded statement but no reliability assessment.",
                    recommendation="Record a reliability assessment (source + confidence) for this witness.",
                    provenance=Provenance(
                        derived_from=[w.id],
                        method="rule:missing_reliability_score",
                        confidence=0.8,
                    ),
                )
            )

    for s in case.suspects:
        if s.status in (SuspectStatus.DETAINED, SuspectStatus.ARRESTED):
            findings.append(
                ComplianceFinding(
                    severity=Severity.HIGH,
                    category=ComplianceCategory.RIGHTS,
                    finding=(
                        f"Suspect {s.id} is marked '{s.status.value}' - ensure rights "
                        f"notices were documented at time of {s.status.value}."
                    ),
                    recommendation="Attach documentation confirming rights were read and understood.",
                    provenance=Provenance(
                        derived_from=[s.id],
                        method="rule:suspect_status_rights_check",
                        confidence=0.6,
                    ),
                )
            )

    return ComplianceOutput(confidence=0.85, findings=findings)
