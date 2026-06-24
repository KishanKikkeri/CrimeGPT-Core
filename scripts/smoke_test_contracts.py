"""
Full pipeline smoke test for the Agent Contract Layer.

Runs stub outputs for all 8 stages through `apply()`, verifies each
agent stayed within its declared read/write contract
(`validate_contract_compliance`), and prints:

  - the final Case JSON
  - the explainability view for the flagship Investigation Gap
  - the auto-generated Agent Contracts table

Run with:  python -m scripts.smoke_test_contracts
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.contracts import contracts_table_markdown, validate_contract_compliance
from app.contracts.case_builder import CONTRACT as CASE_BUILDER_CONTRACT, CaseBuilderOutput
from app.contracts.compliance import CONTRACT as COMPLIANCE_CONTRACT, ComplianceOutput
from app.contracts.evidence import CONTRACT as EVIDENCE_CONTRACT, EvidenceLink, EvidenceOutput
from app.contracts.gaps import CONTRACT as GAPS_CONTRACT, GapDetectionOutput
from app.contracts.health import CONTRACT as HEALTH_CONTRACT, HealthScoringOutput
from app.contracts.legal import CONTRACT as LEGAL_CONTRACT, LegalOutput
from app.contracts.report import CONTRACT as REPORT_CONTRACT, ReportOutput
from app.contracts.timeline import CONTRACT as TIMELINE_CONTRACT, TimelineOutput
from app.models import (
    AdmissibilityStatus,
    Case,
    ComplianceCategory,
    ComplianceFinding,
    CustodyEntry,
    Evidence,
    EvidenceType,
    GapCategory,
    InvestigationGap,
    Provenance,
    ReliabilityScore,
    ReportType,
    Severity,
    Suspect,
    SuspectStatus,
    TimelineEvent,
    Victim,
    Witness,
)


def step(case: Case, contract, output) -> Case:
    """Apply one stage and assert contract compliance."""
    before = case.model_dump()
    case = output.apply(case)
    after = case.model_dump()

    violations = validate_contract_compliance(contract, before, after)
    status = "OK" if not violations else f"VIOLATIONS: {violations}"
    print(f"[{contract.stage.value:>22}] {contract.agent_name:<22} -> {status}")

    return case


def main() -> None:
    case = Case(title="Untitled Case")
    base_time = datetime(2026, 6, 14, 1, 50, 0)

    # ------------------------------------------------------------
    # Stage 1: Case Builder
    # ------------------------------------------------------------
    case_builder_out = CaseBuilderOutput(
        confidence=0.88,
        title="Residential Burglary - Rear Window Entry",
        crime_type="burglary",
        extracted_summary=(
            "A masked individual entered a residence through a rear "
            "window at approximately 2:00 AM. A witness called "
            "emergency services shortly after."
        ),
        victims=[Victim(id="V1", name="Unknown Resident")],
        suspects=[
            Suspect(id="S1", description="Masked individual", status=SuspectStatus.UNKNOWN)
        ],
        witnesses=[
            Witness(
                id="W1",
                statement="Saw a masked person enter through the rear window at 2:03 AM",
                reliability_score=ReliabilityScore(
                    source="uncorroborated single witness", confidence=0.6
                ),
            )
        ],
        evidence=[
            Evidence(
                evidence_id="EV1",
                type=EvidenceType.CCTV,
                title="CCTV Camera 3 footage",
                source="Rear alley camera",
                collected_by="Officer Singh",
                collected_at=base_time + timedelta(minutes=30),
                chain_of_custody=[
                    CustodyEntry(
                        timestamp=base_time + timedelta(minutes=30),
                        holder="Officer Singh",
                        action="Collected footage drive",
                        location="Scene",
                    )
                ],
            )
        ],
        timeline_events=[
            TimelineEvent(
                event_id="E1",
                timestamp=base_time + timedelta(minutes=13),  # 02:03
                description="Witness reports masked individual entering via rear window",
                source="witness_statement_W1",
                confidence=0.8,
                linked_people=["W1", "S1"],
            ),
            TimelineEvent(
                event_id="E2",
                timestamp=base_time + timedelta(minutes=26),  # 02:16
                description="CCTV shows rear window forced entry",
                source="evidence_EV1",
                confidence=0.95,
                linked_evidence=["EV1"],
                linked_people=["S1"],
            ),
        ],
    )
    case = step(case, CASE_BUILDER_CONTRACT, case_builder_out)

    # ------------------------------------------------------------
    # Stage 2: Timeline Builder (passthrough + flags)
    # ------------------------------------------------------------
    timeline_out = TimelineOutput(
        confidence=0.9,
        timeline_events=case.timeline,  # kept as-is for this smoke test
        missing_timestamps=[],
    )
    case = step(case, TIMELINE_CONTRACT, timeline_out)

    # ------------------------------------------------------------
    # Stage 3: Evidence Intelligence
    # ------------------------------------------------------------
    evidence_out = EvidenceOutput(
        confidence=0.85,
        evidence_links=[
            EvidenceLink(
                evidence_id="EV1",
                linked_events=["E2"],
                linked_people=["S1"],
                admissibility_status=AdmissibilityStatus.ADMISSIBLE,
                admissibility_note="Chain of custody documented from collection.",
            )
        ],
        evidence_gaps=["Fingerprint evidence not yet collected from window frame"],
    )
    case = step(case, EVIDENCE_CONTRACT, evidence_out)

    # ------------------------------------------------------------
    # Stage 4: Gap Detection (flagship - note the Provenance)
    # ------------------------------------------------------------
    gaps_out = GapDetectionOutput(
        confidence=0.91,
        investigation_gaps=[
            InvestigationGap(
                id="G1",
                severity=Severity.HIGH,
                category=GapCategory.CONTRADICTION,
                description=(
                    "Witness statement (02:03) and CCTV footage (02:16) "
                    "disagree on entry time by 13 minutes."
                ),
                recommendation="Re-interview witness and verify timestamp accuracy.",
                provenance=Provenance(
                    derived_from=["E1", "E2"],
                    method="cross_reference",
                    confidence=0.91,
                    notes="Compared timeline event timestamps E1 vs E2.",
                ),
            ),
            InvestigationGap(
                id="G2",
                severity=Severity.MEDIUM,
                category=GapCategory.MISSING_EVIDENCE,
                description="No physical evidence placing suspect S1 at the scene.",
                recommendation="Collect and process fingerprint evidence from window frame.",
                provenance=Provenance(
                    derived_from=["S1", "EV1"],
                    method="llm_extraction",
                    confidence=0.78,
                ),
            ),
        ],
    )
    case = step(case, GAPS_CONTRACT, gaps_out)

    # ------------------------------------------------------------
    # Stage 5: Legal Intelligence
    # ------------------------------------------------------------
    legal_out = LegalOutput(
        confidence=0.86,
        statutes=["BNS Section 305 - House-breaking", "BNS Section 306 - Theft after preparation"],
        precedents=["State v. Example (illustrative)"],
        procedural_requirements=[
            "Document chain of custody for all physical evidence",
            "Record witness statements within 24 hours",
        ],
        source_documents=["bns_burglary_2023.md", "crpc_evidence_handling.md"],
    )
    case = step(case, LEGAL_CONTRACT, legal_out)

    # ------------------------------------------------------------
    # Stage 6: Compliance Review
    # ------------------------------------------------------------
    compliance_out = ComplianceOutput(
        confidence=0.9,
        findings=[
            ComplianceFinding(
                severity=Severity.MEDIUM,
                category=ComplianceCategory.DOCUMENTATION,
                finding="Witness W1 statement is not yet signed/witnessed.",
                recommendation="Obtain signed witness statement to support admissibility.",
                provenance=Provenance(
                    derived_from=["W1"],
                    method="rule:documentation_check",
                    confidence=1.0,
                ),
            )
        ],
    )
    case = step(case, COMPLIANCE_CONTRACT, compliance_out)

    # ------------------------------------------------------------
    # Stage 7: Health Scoring (rule-based, not LLM)
    # ------------------------------------------------------------
    health_out = HealthScoringOutput.compute(case)
    case = step(case, HEALTH_CONTRACT, health_out)

    # ------------------------------------------------------------
    # Stage 8: Report Generation
    # ------------------------------------------------------------
    report_out = ReportOutput(
        confidence=0.9,
        report_type=ReportType.CASE_SUMMARY,
        content=(
            f"CASE SUMMARY - {case.title}\n\n"
            f"Crime type: {case.crime_type}\n"
            f"Case health: {case.health.overall}%\n"
            f"Open investigation gaps: {len(case.investigation_gaps)}\n"
            f"Relevant statutes: {', '.join(case.legal_analysis.statutes)}\n"
        ),
    )
    case = step(case, REPORT_CONTRACT, report_out)

    # ------------------------------------------------------------
    # Output
    # ------------------------------------------------------------
    print("\n=== Final Case Health ===")
    print(case.health.model_dump(), "-> overall:", case.health.overall)

    print("\n=== Explainability: Flagship Gap ===")
    gap = case.investigation_gaps[0]
    print(f"Finding: {gap.description}")
    print(f"Severity: {gap.severity.value} | Category: {gap.category.value}")
    print(f"Derived from: {gap.provenance.derived_from} via {gap.provenance.method}")
    print(f"Confidence: {gap.provenance.confidence:.0%}")
    print(f"Recommendation: {gap.recommendation}")

    print("\n=== Generated Report ===")
    print(case.reports[0].content)

    print("\n=== Agent Contracts Table ===")
    print(contracts_table_markdown())


if __name__ == "__main__":
    main()
