# Agent Specifications

CrimeGPT has 9 pipeline stages, each implemented as a standalone agent function. Every agent follows the same contract pattern: it receives the current Case Object (read-only), returns a typed `AgentOutput` subclass, and its `apply(case)` method is the only sanctioned way the Case Object changes.

---

## Stage 1 — Case Builder

**File:** `app/agents/case_builder_agent.py`
**Backed by:** Claude Sonnet (`claude-sonnet-4-6`) · heuristic fallback if no API key

**Purpose:** Convert raw, unstructured investigation documents into the first structured pass of the Case Object.

**Reads:** `raw_input` (transient — not a Case field)

**Writes:**
- `title`
- `crime_type`
- `summary`
- `victims[]`
- `suspects[]`
- `witnesses[]`
- `evidence[]`
- `timeline[]`
- `raw_documents[]`

**Output model:**
```python
class CaseBuilderOutput(AgentOutput):
    title: str
    crime_type: str | None
    extracted_summary: str
    victims: list[Victim]
    suspects: list[Suspect]
    witnesses: list[Witness]
    evidence: list[Evidence]
    timeline_events: list[TimelineEvent]
    confidence: float
    warnings: list[str]
```

**Claude method:** Structured tool-use (`submit_case_structure`). Claude is constrained to the JSON schema and cannot return free text.

**Key prompt constraints:** "Extract ONLY what is explicitly stated. NEVER invent names, times, or facts not present in the text. Add ambiguities to `warnings` instead of guessing."

---

## Stage 2 — Timeline Builder

**File:** `app/agents/timeline_agent.py`
**Backed by:** Deterministic rules

**Purpose:** Sort the timeline chronologically and flag events with no timestamp.

**Reads:** `evidence`, `witnesses`, `timeline`

**Writes:** `timeline` (refined/sorted)

**Output model:**
```python
class TimelineOutput(AgentOutput):
    timeline_events: list[TimelineEvent]
    missing_timestamps: list[str]
    confidence: float
```

**Logic:**
1. Split events into `dated` (timestamp present) and `undated` (no timestamp)
2. Sort `dated` chronologically
3. Append `undated` at the end in original order
4. Add one warning per undated event to `missing_timestamps`

---

## Stage 3 — Evidence Intelligence

**File:** `app/agents/evidence_agent.py`
**Backed by:** Deterministic rules

**Purpose:** Link evidence items to the people and timeline events that reference them. Set admissibility status.

**Reads:** `evidence`, `timeline`

**Writes:** `evidence` (linking fields, admissibility status)

**Output model:**
```python
class EvidenceOutput(AgentOutput):
    evidence_links: list[EvidenceLink]
    evidence_gaps: list[str]
    admissibility_warnings: list[str]
    confidence: float
```

**Logic:**
- For each evidence item, scan timeline events for cross-references
- If `chain_of_custody` is empty → set `QUESTIONABLE`; add admissibility warning
- If no timeline events link to this evidence item → add evidence gap

---

## Stage 4 — Gap Detection

**File:** `app/agents/gap_agent.py`
**Backed by:** Deterministic rules (7 detector functions)

**Purpose:** Find every investigative gap in the case with full provenance. This is the flagship feature.

**Reads:** `victims`, `suspects`, `witnesses`, `evidence`, `timeline`

**Writes:** `investigation_gaps[]`

**Output model:**
```python
class GapDetectionOutput(AgentOutput):
    investigation_gaps: list[InvestigationGap]
    confidence: float
```

**Seven gap detectors:**

| Detector | Trigger | Default severity |
|----------|---------|-----------------|
| `_timeline_contradictions` | Two events share a linked person but timestamps differ > 5 min | HIGH (≥10 min) / MEDIUM |
| `_chain_of_custody_gaps` | Evidence item has zero custody entries | HIGH |
| `_missing_evidence_gaps` | Suspect has no linked evidence; physical evidence has no analysis report | MEDIUM |
| `_missing_witness_gaps` | Witness has no contact information | MEDIUM |
| `_procedural_violations` | Detained/arrested suspect without rights documentation; no first-responder arrival in timeline | HIGH / MEDIUM |
| `_legal_deficiencies` | Legal requirements from `legal_analysis` are not met by case data | HIGH / MEDIUM |
| `_documentation_gaps` | Missing reliability score, evidence description, or case summary | LOW |

Every gap carries a `Provenance` object: `derived_from` (IDs of triggering entities), `method` (detector name), `confidence`.

---

## Stage 4.5 — Gap Enhancement

**File:** `app/agents/gap_enhancement_agent.py`
**Backed by:** Claude Sonnet · no-op if no API key

**Purpose:** Add AI-generated narrative analysis and specific recommendations to HIGH/CRITICAL gaps.

**Reads:** `investigation_gaps`, `timeline`, `evidence`, `witnesses`, `suspects`

**Writes:** `investigation_gaps` (adds `ai_analysis`, `ai_recommendation` fields)

**Output model:**
```python
class GapEnhancementOutput(AgentOutput):
    enhanced_gaps: list[InvestigationGap]
    confidence: float
```

**What Claude adds:**

```
ai_analysis:
  "This discrepancy is legally significant because cross-examination
  will exploit any inconsistency between witness and CCTV testimony.
  The 13-minute gap could indicate the witness reported the time they
  noticed the suspect rather than the time of actual entry..."

ai_recommendation:
  "Obtain the CCTV device technical log to verify Camera 3's clock
  synchronisation status, and re-interview Mrs. Patel to determine
  whether 02:03 was when she first noticed the suspect or when she
  believes entry occurred."
```

Only HIGH and CRITICAL gaps are sent to Claude. MEDIUM/LOW gaps keep their rule-based recommendations, keeping token cost proportional to importance.

---

## Stage 5 — Legal Intelligence

**File:** `app/agents/legal_agent.py`
**Backed by:** Deterministic rule-based knowledge base (stub for RAG)

**Purpose:** Retrieve applicable statutes, precedents, and procedural requirements from the legal knowledge base.

**Reads:** `crime_type`, `evidence`, `timeline`

**Writes:** `legal_analysis`

**Output model:**
```python
class LegalOutput(AgentOutput):
    statutes: list[str]
    precedents: list[str]
    procedural_requirements: list[str]
    source_documents: list[str]
    confidence: float
```

**Current implementation:** In-memory knowledge base keyed by `crime_type` (burglary, theft, assault, fraud). Production upgrade: swap knowledge base lookups for vector search over curated BNS/BNSS/IPC legal corpus.

**Note:** Legal runs *after* facts are structured — mirroring a real investigation where legal grounding follows evidence analysis.

---

## Stage 6 — Compliance Review

**File:** `app/agents/compliance_agent.py`
**Backed by:** Deterministic rules

**Purpose:** Audit the case for admissibility, documentation, and rights compliance.

**Reads:** `victims`, `suspects`, `evidence`, `legal_analysis`

**Writes:** `compliance_findings[]`

**Output model:**
```python
class ComplianceOutput(AgentOutput):
    findings: list[ComplianceFinding]
    confidence: float
```

**Checks:**
- Evidence not marked ADMISSIBLE → HIGH admissibility finding
- Witness with statement but no reliability assessment → MEDIUM documentation finding
- Detained/arrested suspect → HIGH rights-notice reminder

---

## Stage 7 — Health Scoring

**File:** `app/agents/health_agent.py` → delegates to `app/scoring/`
**Backed by:** Deterministic formula (not LLM)

**Purpose:** Compute a transparent, weighted case readiness score.

**Reads:** Entire case (all fields)

**Writes:** `health`

**Output model:**
```python
class HealthScoringOutput(AgentOutput):
    health: CaseHealth
    confidence: float = 1.0  # always 1.0 — deterministic
```

**Formula:**
```
overall = completeness × 0.35
        + evidence_integrity × 0.25
        + legal_readiness × 0.20
        + documentation_quality × 0.20
```

Each sub-score has a dedicated module with both `compute(case)` (int) and `breakdown(case)` (per-item pass/fail) for the explainability panel.

---

## Stage 8 — Report Generation

**File:** `app/agents/report_agent.py`
**Backed by:** Template rendering (the only stage permitted to produce prose)

**Purpose:** Render the fully-enriched Case Object into one or more reports.

**Reads:** Entire case

**Writes:** `reports[]` (appends)

**Output model:**
```python
class ReportOutput(AgentOutput):
    report_type: ReportType
    content: str  # the only prose output in the entire pipeline
    confidence: float
```

**Report types:**
- `case_summary` — brief overview with key metrics
- `investigation_report` — full structured report (people, timeline, evidence, gaps, legal)
- `court_brief` — admissible evidence + applicable law + open compliance issues
- `evidence_summary` — evidence-focused with custody chain status
- `executive_intelligence_report` — one-page overview with readiness and critical next steps

**Architecture note:** This stage can run standalone via `build_report_only_graph()` without re-running Stages 1-7 — "Generate Reports Anytime" for continuous updates.
