# Testing

CrimeGPT has 27 intelligence tests that verify the system produces good investigations — not just that the pipeline runs.

---

## Running the Tests

```bash
pytest tests/intelligence/ -v
```

Expected output:
```
tests/intelligence/test_burglary_case.py
  PASSED TestPipelineHealth::test_pipeline_completes_without_error
  PASSED TestPipelineHealth::test_all_eight_stages_completed
  PASSED TestPipelineHealth::test_mutation_log_covers_all_key_fields
  PASSED TestPipelineHealth::test_all_agents_succeeded
  PASSED TestTimeline::test_minimum_timeline_events
  PASSED TestTimeline::test_timeline_is_chronological
  PASSED TestTimeline::test_key_events_present
  PASSED TestTimeline::test_contradiction_timestamps_are_present
  PASSED TestGapDetection::test_minimum_total_gaps
  PASSED TestGapDetection::test_minimum_high_severity_gaps
  PASSED TestGapDetection::test_timeline_contradiction_detected
  PASSED TestGapDetection::test_chain_of_custody_gaps_detected
  PASSED TestGapDetection::test_missing_witness_contact_detected
  PASSED TestGapDetection::test_missing_forensic_analysis_detected
  PASSED TestGapDetection::test_all_gaps_have_provenance
  PASSED TestGapDetection::test_all_gaps_have_recommendations
  PASSED TestGapDetection::test_required_gaps_from_corpus
  PASSED TestHealthScoring::test_health_score_in_expected_range
  PASSED TestHealthScoring::test_evidence_integrity_penalized_for_missing_custody
  PASSED TestHealthScoring::test_completeness_is_high
  PASSED TestHealthScoring::test_health_sub_scores_are_valid
  PASSED TestLegalAnalysis::test_legal_analysis_produced
  PASSED TestLegalAnalysis::test_minimum_statutes_found
  PASSED TestLegalAnalysis::test_legal_analysis_has_provenance
  PASSED TestReports::test_at_least_one_report_generated
  PASSED TestReports::test_report_mentions_key_findings
  PASSED TestReports::test_report_not_just_boilerplate

27 passed in 0.06s
```

No API key required. All 27 tests are deterministic.

---

## Test Architecture

### The Flagship Test Case

`data/burglary/case_factory.py` builds the pre-structured Maple Street burglary case:

- **7 timeline events** with timestamps (including the 13-minute contradiction)
- **4 evidence items** (3 with no chain of custody)
- **2 witnesses** (1 anonymous with no contact)
- **1 suspect** (linked to no physical evidence)

These problems are deliberate. The tests verify CrimeGPT finds them.

### Ground Truth Files

`data/burglary/expected_gaps.json` defines what the system must detect:

```json
{
  "required_gaps": [
    {
      "id_prefix": "G-TC",
      "category": "timeline_contradiction",
      "severity": "high",
      "description_contains": ["2:03", "2:16"],
      "rationale": "Witness says 02:03, CCTV shows 02:16 — 13-minute gap"
    },
    {
      "id_prefix": "G-COC-EV-001",
      "category": "chain_of_custody",
      "severity": "high",
      "rationale": "Fingerprint samples have no custody chain"
    },
    ...
  ],
  "minimum_gaps_total": 5,
  "minimum_high_severity": 2,
  "target_health_score_range": [55, 80]
}
```

Tests load this file and verify each required gap is present.

### Test Infrastructure

```python
# conftest.py — session-scoped fixtures (pipeline runs once per test session)

@pytest.fixture(scope="session")
def burglary_case() -> Case:
    return build_burglary_case()  # Stage 1 already done by factory

@pytest.fixture(scope="session")
def burglary_result(burglary_case) -> dict:
    # Runs Stages 2–8 via build_analysis_graph()
    state = initial_state(burglary_case)
    graph = build_analysis_graph(start_from=WorkflowStage.TIMELINE_BUILDER)
    return graph.invoke(state)

@pytest.fixture(scope="session")
def final_case(burglary_result) -> Case:
    return burglary_result["case"]
```

The pipeline runs once for the entire test session — fast and consistent.

---

## Test Classes

### TestPipelineHealth (4 tests)

Verifies the pipeline ran without errors:
- Pipeline completed without `state["error"]`
- All 8 stages appear in `case.completed_stages`
- Key fields (`investigation_gaps`, `legal_analysis`, `health`, `reports`) appear in the mutation log
- All agent executions have `success=True`

### TestTimeline (4 tests)

Verifies timeline construction:
- At least 4 events extracted
- Events are in chronological order
- Key event descriptions present (02:03 witness, 02:16 CCTV, 02:08 call, 02:31 arrival)
- Both contradiction timestamps (02:03 and 02:16) are in the timeline

### TestGapDetection (9 tests) — the flagship

These are the most important tests. They verify CrimeGPT finds specific, named problems:

| Test | What it checks |
|------|---------------|
| `test_minimum_total_gaps` | At least 5 gaps found |
| `test_minimum_high_severity_gaps` | At least 2 HIGH/CRITICAL gaps |
| `test_timeline_contradiction_detected` | A `TIMELINE_CONTRADICTION` gap exists |
| `test_chain_of_custody_gaps_detected` | At least 2 `CHAIN_OF_CUSTODY` gaps (EV-001, EV-003) |
| `test_missing_witness_contact_detected` | A `MISSING_WITNESS` gap for anonymous W2 |
| `test_missing_forensic_analysis_detected` | A `MISSING_EVIDENCE` gap mentioning "forensic" |
| `test_all_gaps_have_provenance` | Every gap has a non-null Provenance with method and confidence |
| `test_all_gaps_have_recommendations` | Every gap has a recommendation > 10 chars |
| `test_required_gaps_from_corpus` | Each entry in `expected_gaps.json` is found |

### TestHealthScoring (4 tests)

Verifies the deterministic scoring:
- Overall score in range [55, 80] for this case
- Evidence integrity penalised below 60% (3/4 items have no custody chain)
- Completeness ≥ 80% (all core fields populated)
- All sub-scores in [0, 100] range

### TestLegalAnalysis (3 tests)

- Legal analysis object is present
- At least 1 statute found
- Legal analysis has provenance

### TestReports (3 tests)

- At least 1 report generated
- Reports mention key findings ("gap", "chain", "witness", "evidence")
- Report content includes the case title (not boilerplate)

---

## Adding Test Cases

To add a new test scenario:

1. Create `data/{crime_type}/case_factory.py` with a pre-structured `Case`
2. Create `data/{crime_type}/expected_gaps.json` with ground truth
3. Create `tests/intelligence/test_{crime_type}_case.py` following the burglary test pattern
4. Add fixtures to `tests/intelligence/conftest.py`

---

## Smoke Tests

Beyond intelligence tests, three smoke tests verify system integration:

```bash
python -m scripts.smoke_test_graph       # minimal 2-node LangGraph
python -m scripts.smoke_test_contracts   # full 8-stage contract pipeline
python -m scripts.smoke_test_runtime     # complete pipeline with mutation log
```

These run the full pipeline against a constructed case and verify the output shape.
