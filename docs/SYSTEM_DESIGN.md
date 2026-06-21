# System Design

A deep technical reference for every major engineering decision in CrimeGPT.

---

## Design Principles

**1. Data model first.** The Case Object was designed completely before any agent code was written. This meant every downstream decision — LangGraph state, API routes, agent contracts, frontend components — could be derived from the schema rather than negotiated.

**2. Agents do not talk to each other.** All inter-agent communication happens through the Case Object. No agent calls another agent. No shared state beyond the Case. This makes the system dramatically simpler to debug, test, and extend.

**3. Detection before LLM.** Gap detection, health scoring, and compliance review are deterministic. Claude is layered on top for human-readable explanation and recommendation, not for producing the findings themselves.

**4. Prose is a last step.** Only the Report Generation agent (Stage 8) produces free text. All other agents produce typed, validated Pydantic models. This makes the system easier to test and dramatically reduces hallucination risk.

**5. Fail loudly, degrade gracefully.** Each agent catches its own exceptions via `AgentExecutor` and records the error without crashing the pipeline. Claude integrations fall back to rule-based alternatives.

---

## The Case Object

The `Case` Pydantic model (`app/models/case.py`) is the single source of truth. All agents read from it; all agents write back to it. The database stores it as a single JSON document.

```python
class Case(BaseModel):
    # Identity
    case_id: str            # auto-generated: "CASE-2026-A4F91B"
    title: str
    status: CaseStatus
    priority: CasePriority
    jurisdiction: Optional[str]
    crime_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Narrative
    summary: Optional[str]
    raw_documents: list[str]

    # Entities
    victims: list[Victim]
    suspects: list[Suspect]
    witnesses: list[Witness]
    evidence: list[Evidence]
    timeline: list[TimelineEvent]

    # Analysis
    legal_analysis: Optional[LegalAnalysis]
    investigation_gaps: list[InvestigationGap]
    compliance_findings: list[ComplianceFinding]

    # Output
    reports: list[Report]

    # Scoring
    health: CaseHealth

    # Workflow tracking
    current_stage: WorkflowStage
    completed_stages: list[WorkflowStage]
```

---

## The Evidence Object

`Evidence` is one of the most important sub-objects. It models the chain of custody as a list of `CustodyEntry` objects:

```python
class Evidence(BaseModel):
    evidence_id: str
    type: EvidenceType          # physical/digital/cctv/photo/forensic/other
    title: str
    description: Optional[str]
    source: Optional[str]
    collected_by: Optional[str]
    collected_at: Optional[datetime]
    chain_of_custody: list[CustodyEntry]   # empty = gap detected
    linked_people: list[str]               # IDs of victims/suspects/witnesses
    linked_events: list[str]               # IDs of timeline events
    admissibility_status: AdmissibilityStatus

class CustodyEntry(BaseModel):
    timestamp: datetime
    holder: str
    action: str
    location: Optional[str]
```

An empty `chain_of_custody` list triggers:
- A `CHAIN_OF_CUSTODY` gap in Stage 4
- A `LEGAL_DEFICIENCY` gap in Stage 4 (if legal requirements include custody documentation)
- An `admissibility` finding in Stage 6
- A penalty to `evidence_integrity` in Stage 7

---

## The TimelineEvent Object

The timeline is the most important structural object for reasoning. Everything eventually becomes an event.

```python
class TimelineEvent(BaseModel):
    event_id: str
    timestamp: Optional[datetime]    # None = undated event
    description: str
    source: Optional[str]            # "witness_statement_W1", "evidence_EV-002", etc.
    confidence: Optional[float]      # 0.0–1.0
    linked_people: list[str]         # IDs of people involved
    linked_evidence: list[str]       # IDs of evidence items referenced
```

The `linked_people` field is what enables contradiction detection: if two events share a linked person and their timestamps differ by more than 5 minutes, a `TIMELINE_CONTRADICTION` gap is created.

---

## The Provenance System

```python
class Provenance(BaseModel):
    derived_from: list[str]   # entity IDs (event IDs, evidence IDs, witness IDs)
    method: str               # detection mechanism tag
    confidence: float         # 0.0–1.0
    notes: Optional[str]
```

Provenance is required on:
- `InvestigationGap` (every gap must explain itself)
- `ComplianceFinding` (every finding must cite its source)
- `LegalAnalysis` (cites which source documents from the knowledge base)

It is optional on:
- `ReliabilityScore` (within `Witness`) — carries a required `source` string explaining the basis

---

## The Mutation Engine

`MutationEngine` (`app/runtime/engine.py`) is the single place the Case Object changes:

```python
@classmethod
def apply(cls, case, output, contract) -> tuple[Case, list[CaseMutation]]:
    before = case.model_dump(mode="json")
    case = output.apply(case)              # the agent's apply() method
    after = case.model_dump(mode="json")

    # Contract compliance check (non-blocking — records violations as warnings)
    violations = validate_contract_compliance(contract, before, after)
    if violations:
        output.warnings.append(f"Wrote to undeclared fields: {violations}")

    # Derive mutations from the diff
    changed = diff_top_level_fields(before, after)
    mutations = [CaseMutation(field=f, before=before[f], after=after[f], ...) for f in changed]

    return case, mutations

@classmethod
def rollback(cls, case, mutation) -> Case:
    setattr(case, mutation.field, mutation.before)
    mutation.review_status = "rejected"
    return case
```

---

## LangGraph State

`GraphState` (`app/graph/state.py`) is a `TypedDict` with three append-only list fields using `operator.add` as the LangGraph reducer:

```python
class GraphState(TypedDict, total=False):
    case: Case
    raw_input: Optional[str]
    requested_report_types: list[ReportType]
    agent_logs: Annotated[list[AgentRunLog], operator.add]    # UI progress
    mutations: Annotated[list[CaseMutation], operator.add]    # audit trail
    executions: Annotated[list[AgentExecution], operator.add] # ops/perf
    error: Optional[str]
```

`operator.add` means each node's partial update is *concatenated* with the running state, not overwritten. A node that processes multiple report types can return a list of `AgentRunLog` and `CaseMutation` entries that get merged cleanly.

---

## Database Design

Single table, JSONB strategy:

```sql
CREATE TABLE cases (
    id          VARCHAR(36) PRIMARY KEY,
    case_id     VARCHAR(64) UNIQUE NOT NULL,
    title       TEXT NOT NULL DEFAULT 'Untitled Case',
    status      VARCHAR(32) NOT NULL DEFAULT 'created',
    case_json   TEXT NOT NULL,     -- Postgres: JSONB; SQLite: TEXT
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The entire `Case` Pydantic model is serialised via `model_dump_json()` and stored in `case_json`. Deserialisation uses `Case.model_validate_json()`.

**Why JSONB instead of normalised tables?**

The Case Object is a deep, nested structure with optional fields at every level. Normalising it would produce 15+ tables with complex joins for every API call. JSONB gives us:
- Atomic reads/writes (no join required to get the full case)
- No schema migration risk during the hackathon
- Direct query capability with PostgreSQL's `@>` and `->` operators if needed later
- Easy to normalise post-hackathon if specific query patterns emerge

---

## API Layer

FastAPI with dependency injection for the database session:

```python
@router.post("/{case_id}/analyze")
def analyze_case(case_id: str, body: AnalyzeRequest, db: Session = Depends(get_db)):
    case = get_case(db, case_id)
    state = initial_state(case, raw_input=body.raw_input)
    result = build_investigation_graph().invoke(state)
    upsert_case(db, result["case"])
    return {...}
```

The API layer has no business logic. It delegates to the graph builder and the CRUD layer. This keeps routes thin and testable.

---

## Health Scoring

Four independent scoring modules in `app/scoring/`:

```
completeness.py        — checks presence of 6 core Case fields
evidence_integrity.py  — checks custody chain completeness per evidence item
legal_readiness.py     — 100 minus penalties for high/critical compliance findings
documentation_quality.py — 100 minus penalties for DOCUMENTATION_GAP gaps
```

Each module exposes two functions:
- `compute(case: Case) -> int` — the score (0–100)
- `breakdown(case: Case) -> dict | list` — per-item pass/fail for the API's `/health` endpoint

The weighted formula lives in `app/scoring/weights.py` and is imported by both `CaseHealth.overall` (the model property) and `app/scoring/__init__.py` (the `compute_overall()` helper).

---

## Continuous Updates (Stage 9)

`build_analysis_graph(start_from=WorkflowStage.GAP_DETECTION)` creates a partial pipeline that enters at Stage 4, re-running gap detection, AI enrichment, legal analysis, compliance, scoring, and reports — without re-running document extraction (Stage 1) or timeline/evidence organisation (Stages 2–3).

This is the production-ready "new evidence added" flow:

```
New fingerprint report uploaded
     ↓
Case updated (EV-001 gets forensic analysis result)
     ↓
build_analysis_graph(start_from=GAP_DETECTION).invoke(state)
     ↓
Gaps recalculated (G-ME-FORENSIC no longer fires)
     ↓
Case health updated (evidence_integrity improves)
     ↓
New report generated
```
