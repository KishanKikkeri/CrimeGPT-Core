# Architecture

CrimeGPT is built on four interlocking layers. Each layer has a single, clear responsibility. Together they turn raw investigation documents into a structured, legally-grounded, auditable case file.

---

## Layer 1 — The Case Object

Everything in CrimeGPT revolves around one entity: the `Case`.

```
Case
├── Identity        case_id, title, status, priority, jurisdiction, crime_type
├── People          victims[], suspects[], witnesses[]
├── Evidence        evidence[] (with chain_of_custody[])
├── Timeline        timeline[] (TimelineEvent objects)
├── Analysis        legal_analysis, investigation_gaps[], compliance_findings[]
├── Reports         reports[]
├── Scoring         health (CaseHealth)
└── Audit           current_stage, completed_stages[]
```

**Architectural principle 1: Agents do not talk to each other.** Every agent reads from the Case Object and writes back to the Case Object. There are no agent-to-agent calls, no shared memory, no message passing.

**Architectural principle 2: Past the structuring stage, agents output structured data only.** The only agent permitted to produce prose is the Report Generation agent (Stage 8). All other agents produce typed Pydantic models.

### The Case Object as source of truth

```
           ┌──────────────────────────────┐
           │         Case Object          │
           │                              │
Agent 1 ──►│  victims, suspects, evidence │◄── Agent 2
           │  timeline, gaps, legal       │
Agent 3 ──►│  compliance, health, reports │◄── Agent 4
           │                              │
           └──────────────────────────────┘
```

---

## Layer 2 — Agent Contracts

Each of the 9 pipeline stages has a formal contract:

- **Input schema** (typed Pydantic model)
- **Output schema** (typed Pydantic model with `apply(case)` method)
- **Declared read fields** — which Case fields it reads
- **Declared write fields** — which Case fields it may modify

```python
class GapDetectionOutput(AgentOutput):
    investigation_gaps: list[InvestigationGap]

    def apply(self, case: Case) -> Case:
        case.investigation_gaps = self.investigation_gaps
        self.mark_complete(case, next_stage=WorkflowStage.GAP_ENHANCEMENT)
        return case

CONTRACT = AgentContract(
    agent_name="gap_detection",
    stage=WorkflowStage.GAP_DETECTION,
    reads=("victims", "suspects", "witnesses", "evidence", "timeline"),
    writes=("investigation_gaps",),
    output_model=GapDetectionOutput,
)
```

### Contract compliance checking

`validate_contract_compliance(contract, before, after)` diffs two `case.model_dump()` snapshots and returns any fields an agent wrote to outside its declared `writes`. Runs after every stage in the smoke tests.

---

## Layer 3 — The Mutation Engine

Every change to the Case Object is recorded as a `CaseMutation`:

```python
class CaseMutation(BaseModel):
    mutation_id: str
    case_id: str
    field: str              # which Case field changed
    operation: "replace"
    before: Any             # value before the agent ran
    after: Any              # value after
    source_agent: str
    stage: WorkflowStage
    timestamp: datetime
    review_status: "unreviewed" | "approved" | "rejected"
```

`MutationEngine.apply(case, output, contract)` wraps `output.apply(case)`, diffs before/after, and produces the mutation log automatically.

`MutationEngine.rollback(case, mutation)` restores `mutation.before` — supporting undo and human review workflows.

---

## Layer 4 — The LangGraph Runtime

The pipeline is a compiled LangGraph `StateGraph` with 9 nodes and conditional edges:

```
START
  │
  ▼
case_builder ──► timeline_builder ──► evidence_intelligence
                                              │
                                              ▼
                                       gap_detection
                                              │
                                              ▼
                                      gap_enhancement  ← Claude
                                              │
                                              ▼
                                    legal_intelligence
                                              │
                                              ▼
                                     compliance_review
                                              │
                                              ▼
                                      health_scoring
                                              │
                                              ▼
                                    report_generation
                                              │
                                             END
```

Every edge is conditional: if any node sets `state["error"]`, the graph routes straight to END rather than continuing on bad/incomplete data.

### GraphState

The object passed between nodes:

```python
class GraphState(TypedDict, total=False):
    case: Case                                     # the single source of truth
    raw_input: Optional[str]                       # consumed by Stage 1 only
    requested_report_types: list[ReportType]
    agent_logs: Annotated[list[AgentRunLog], operator.add]       # append-only
    mutations: Annotated[list[CaseMutation], operator.add]       # append-only
    executions: Annotated[list[AgentExecution], operator.add]    # append-only
    error: Optional[str]
```

`operator.add` on list fields means LangGraph merges partial updates from each node by concatenation, never by overwrite.

---

## Provenance System

Every `InvestigationGap`, `ComplianceFinding`, and `LegalAnalysis` carries a `Provenance`:

```python
class Provenance(BaseModel):
    derived_from: list[str]   # IDs of the Case sub-objects that triggered this
    method: str               # "rule:timestamp_diff", "rule:custody_chain",
                              # "llm_extraction", "rag_retrieval"
    confidence: float         # 0.0–1.0
    notes: Optional[str]
```

This makes every finding traceable to its source and method. The UI can highlight exactly which evidence item or timeline event produced a given gap.

---

## Health Scoring

Case Readiness is computed by four deterministic rules modules and combined with a fixed weight formula:

```
Readiness = completeness × 0.35
           + evidence_integrity × 0.25
           + legal_readiness × 0.20
           + documentation_quality × 0.20
```

Each sub-score module also exposes a `breakdown()` function returning per-item pass/fail for the explainability panel ("why is evidence_integrity only 25%?").

---

## Entry Points

Three graph variants serve different use cases:

| Function | Stages | Use case |
|----------|--------|----------|
| `build_investigation_graph()` | 1–8 | Full pipeline from raw documents |
| `build_analysis_graph(start_from=)` | 2–8 or 4–8 | Re-analyse a pre-structured case |
| `build_report_only_graph()` | 8 only | Generate reports without re-running analysis |
