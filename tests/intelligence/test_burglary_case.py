"""
Intelligence tests — Burglary Case (14 Maple Street)

These tests verify that CrimeGPT produces *good investigations*,
not just that the pipeline runs. Each test maps to a specific
real-world investigative quality standard.

Run with:  pytest tests/intelligence/ -v
"""

from __future__ import annotations

import pytest

from app.models.case import Case
from app.models.enums import GapCategory, Severity


# -----------------------------------------------------------------------
# Pipeline health
# -----------------------------------------------------------------------

class TestPipelineHealth:

    def test_pipeline_completes_without_error(self, burglary_result):
        assert burglary_result.get("error") is None, (
            f"Pipeline failed: {burglary_result.get('error')}"
        )

    def test_all_eight_stages_completed(self, final_case):
        from app.models.enums import WorkflowStage
        expected = [
            WorkflowStage.CASE_BUILDER,
            WorkflowStage.TIMELINE_BUILDER,
            WorkflowStage.EVIDENCE_INTELLIGENCE,
            WorkflowStage.GAP_DETECTION,
            WorkflowStage.LEGAL_INTELLIGENCE,
            WorkflowStage.COMPLIANCE_REVIEW,
            WorkflowStage.HEALTH_SCORING,
            WorkflowStage.REPORT_GENERATION,
        ]
        missing = [s for s in expected if s not in final_case.completed_stages]
        assert not missing, f"Stages not completed: {[s.value for s in missing]}"

    def test_mutation_log_covers_all_key_fields(self, burglary_result):
        mutated = {m.field for m in burglary_result["mutations"]}
        required = {"investigation_gaps", "legal_analysis", "compliance_findings", "health", "reports"}
        missing = required - mutated
        assert not missing, f"Expected mutation log to include: {missing}"

    def test_all_agents_succeeded(self, burglary_result):
        failures = [ex for ex in burglary_result["executions"] if not ex.success]
        assert not failures, (
            f"{len(failures)} agent(s) failed: "
            + ", ".join(f"{ex.agent_name}: {ex.error}" for ex in failures)
        )


# -----------------------------------------------------------------------
# Timeline
# -----------------------------------------------------------------------

class TestTimeline:

    def test_minimum_timeline_events(self, final_case, expected_timeline):
        minimum = expected_timeline["minimum_events"]
        assert len(final_case.timeline) >= minimum, (
            f"Expected at least {minimum} timeline events, "
            f"got {len(final_case.timeline)}"
        )

    def test_timeline_is_chronological(self, final_case):
        dated = [e for e in final_case.timeline if e.timestamp is not None]
        timestamps = [e.timestamp for e in dated]
        assert timestamps == sorted(timestamps), (
            "Timeline events are not in chronological order"
        )

    def test_key_events_present(self, final_case, expected_timeline):
        timeline_text = " ".join(
            (e.description or "").lower() for e in final_case.timeline
        )
        for expected_event in expected_timeline["required_events"]:
            keywords = expected_event["description_contains"]
            # At least one keyword from each required event must match
            found = any(kw.lower() in timeline_text for kw in keywords)
            assert found, (
                f"Required timeline event not found. "
                f"Expected keywords: {keywords}. "
                f"Rationale: {expected_event['rationale']}"
            )

    def test_contradiction_timestamps_are_present(self, final_case):
        """The flagship 13-minute contradiction must be detectable."""
        from app.models.enums import GapCategory
        timestamps = [e.timestamp for e in final_case.timeline if e.timestamp]
        # Both 02:03 and 02:16 events must exist
        hours_minutes = [(t.hour, t.minute) for t in timestamps]
        assert (2, 3) in hours_minutes, "02:03 AM witness event not in timeline"
        assert (2, 16) in hours_minutes, "02:16 AM CCTV event not in timeline"


# -----------------------------------------------------------------------
# Gap Detection (the flagship feature)
# -----------------------------------------------------------------------

class TestGapDetection:

    def test_minimum_total_gaps(self, final_case, expected_gaps):
        minimum = expected_gaps["minimum_gaps_total"]
        found = len(final_case.investigation_gaps)
        assert found >= minimum, (
            f"Expected at least {minimum} investigation gaps, found {found}. "
            f"This means the Gap Detection agent is missing real issues."
        )

    def test_minimum_high_severity_gaps(self, final_case, expected_gaps):
        minimum = expected_gaps["minimum_high_severity"]
        high = sum(
            1 for g in final_case.investigation_gaps
            if g.severity in (Severity.HIGH, Severity.CRITICAL)
        )
        assert high >= minimum, (
            f"Expected at least {minimum} HIGH/CRITICAL gaps, found {high}"
        )

    def test_timeline_contradiction_detected(self, final_case):
        """
        The 13-minute discrepancy between W1 (02:03) and CCTV (02:16)
        for the same suspect S1 MUST be detected.
        """
        contradiction_gaps = [
            g for g in final_case.investigation_gaps
            if g.category == GapCategory.TIMELINE_CONTRADICTION
        ]
        assert contradiction_gaps, (
            "No TIMELINE_CONTRADICTION gap detected. "
            "The 13-minute discrepancy between witness (02:03) and "
            "CCTV (02:16) must be surfaced."
        )

    def test_chain_of_custody_gaps_detected(self, final_case):
        """
        EV-001 (fingerprints) and EV-003 (bag) have no custody chain.
        Both MUST produce CHAIN_OF_CUSTODY gaps.
        """
        coc_gaps = [
            g for g in final_case.investigation_gaps
            if g.category == GapCategory.CHAIN_OF_CUSTODY
        ]
        assert len(coc_gaps) >= 2, (
            f"Expected at least 2 CHAIN_OF_CUSTODY gaps "
            f"(EV-001 fingerprints, EV-003 bag), found {len(coc_gaps)}"
        )

    def test_missing_witness_contact_detected(self, final_case):
        """
        W2 is anonymous — no contact details. MUST produce a
        MISSING_WITNESS gap.
        """
        witness_gaps = [
            g for g in final_case.investigation_gaps
            if g.category == GapCategory.MISSING_WITNESS
        ]
        assert witness_gaps, (
            "No MISSING_WITNESS gap detected for anonymous witness W2."
        )

    def test_missing_forensic_analysis_detected(self, final_case):
        """
        Fingerprints were collected but never analyzed. MUST produce
        a MISSING_EVIDENCE gap for missing forensic analysis.
        """
        forensic_gaps = [
            g for g in final_case.investigation_gaps
            if g.category == GapCategory.MISSING_EVIDENCE
            and "forensic" in g.description.lower()
        ]
        assert forensic_gaps, (
            "No MISSING_EVIDENCE gap for missing forensic analysis. "
            "Fingerprints were collected but no analysis was conducted."
        )

    def test_all_gaps_have_provenance(self, final_case):
        """Every gap must explain itself."""
        for gap in final_case.investigation_gaps:
            assert gap.provenance is not None, (
                f"Gap {gap.id} has no provenance"
            )
            assert gap.provenance.method, (
                f"Gap {gap.id} provenance has no method"
            )
            assert 0.0 <= gap.provenance.confidence <= 1.0, (
                f"Gap {gap.id} provenance confidence out of range"
            )

    def test_all_gaps_have_recommendations(self, final_case):
        """Every gap must tell the investigator what to do next."""
        for gap in final_case.investigation_gaps:
            assert gap.recommendation and len(gap.recommendation) > 10, (
                f"Gap {gap.id} has no meaningful recommendation"
            )

    def test_required_gaps_from_corpus(self, final_case, expected_gaps):
        """Each entry in expected_gaps.json must be found."""
        all_gap_descriptions = " ".join(
            (g.description or "").lower() + " " + g.category.value
            for g in final_case.investigation_gaps
        )
        all_gap_categories = {g.category.value for g in final_case.investigation_gaps}

        for required in expected_gaps["required_gaps"]:
            category = required["category"]
            keywords = required["description_contains"]

            assert category in all_gap_categories or any(
                kw.lower() in all_gap_descriptions for kw in keywords
            ), (
                f"Required gap not found — category: {category}, "
                f"keywords: {keywords}. "
                f"Rationale: {required['rationale']}"
            )


# -----------------------------------------------------------------------
# Health Scoring
# -----------------------------------------------------------------------

class TestHealthScoring:

    def test_health_score_in_expected_range(self, final_case, expected_gaps):
        low, high = expected_gaps["target_health_score_range"]
        score = final_case.health.overall
        assert low <= score <= high, (
            f"Case health {score}% is outside expected range "
            f"[{low}%, {high}%]. "
            "Either the scoring formula or the test case data needs review."
        )

    def test_evidence_integrity_penalized_for_missing_custody(self, final_case):
        """
        Three of four evidence items have no custody chain.
        Evidence integrity should be well below 100%.
        """
        assert final_case.health.evidence_integrity < 60, (
            f"Evidence integrity is {final_case.health.evidence_integrity}% "
            "but 3/4 evidence items have no chain of custody."
        )

    def test_completeness_is_high(self, final_case):
        """
        The case factory provides all core fields so completeness
        should be near-perfect.
        """
        assert final_case.health.completeness >= 80, (
            f"Completeness is only {final_case.health.completeness}% — "
            "check that core fields are populated in the test case."
        )

    def test_health_sub_scores_are_valid(self, final_case):
        h = final_case.health
        for field, value in [
            ("completeness", h.completeness),
            ("evidence_integrity", h.evidence_integrity),
            ("legal_readiness", h.legal_readiness),
            ("documentation_quality", h.documentation_quality),
        ]:
            assert 0 <= value <= 100, (
                f"health.{field} = {value} is out of [0, 100] range"
            )


# -----------------------------------------------------------------------
# Legal Analysis
# -----------------------------------------------------------------------

class TestLegalAnalysis:

    def test_legal_analysis_produced(self, final_case):
        assert final_case.legal_analysis is not None, (
            "No legal_analysis on the final case"
        )

    def test_minimum_statutes_found(self, final_case, expected_gaps):
        minimum = expected_gaps["required_legal_statutes_min"]
        found = len(final_case.legal_analysis.statutes) if final_case.legal_analysis else 0
        assert found >= minimum, (
            f"Expected at least {minimum} statute(s), found {found}"
        )

    def test_legal_analysis_has_provenance(self, final_case):
        if final_case.legal_analysis:
            assert final_case.legal_analysis.provenance is not None


# -----------------------------------------------------------------------
# Reports
# -----------------------------------------------------------------------

class TestReports:

    def test_at_least_one_report_generated(self, final_case):
        assert final_case.reports, "No reports generated"

    def test_report_mentions_key_findings(self, final_case):
        all_content = " ".join(r.content.lower() for r in final_case.reports)
        for keyword in ["gap", "chain", "witness", "evidence"]:
            assert keyword in all_content, (
                f"Reports don't mention '{keyword}' — "
                f"key finding likely missing from report"
            )

    def test_report_not_just_boilerplate(self, final_case):
        """Report content must reference the actual case title."""
        title_words = final_case.title.lower().split()[:3]
        all_content = " ".join(r.content.lower() for r in final_case.reports)
        found = any(w in all_content for w in title_words)
        assert found, "Report doesn't reference the case title — possible boilerplate output"
