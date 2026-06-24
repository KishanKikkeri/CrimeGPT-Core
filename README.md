# CrimeGPT — AI Investigation Copilot

> Transform messy investigation documents into a structured, legally-grounded case file in under 90 seconds.

CrimeGPT is an AI investigation copilot for law enforcement and legal professionals. It converts unstructured officer notes, witness statements, and evidence logs into a complete, auditable investigation workspace — finding contradictions, flagging missing evidence, checking compliance, and generating court-ready reports.

---

## The Problem

Investigators spend enormous time manually reviewing unstructured documents:

- Officer notes written in shorthand
- Witness statements with inconsistent timelines
- Evidence logs with missing chain-of-custody records
- Legal requirements scattered across procedure manuals

A single case may involve dozens of documents. Critical gaps — a 13-minute discrepancy between a witness statement and CCTV footage, a missing custody chain on key evidence — are easy to miss under time pressure.

## The Solution

CrimeGPT is not a chatbot. It is an **investigation workspace** that:

1. **Extracts** — Claude reads raw documents and produces a fully structured case object
2. **Detects** — deterministic rules find contradictions, custody gaps, missing witnesses, and procedural violations
3. **Reasons** — Claude narrates why each gap matters legally and recommends specific next actions
4. **Scores** — a transparent, weighted formula produces a Case Readiness percentage
5. **Reports** — generates FIR summaries, investigation reports, court briefs, and executive intelligence briefs

---

## Key Features

### AI Case Extraction
Upload 4 messy documents → Claude extracts 1 victim, 2 witnesses, 4 evidence items, and 7 timeline events with timestamped events and confidence scores.

### Investigation Gap Detection
Seven gap categories, each with deterministic detectors and full provenance:
- Timeline contradiction (timestamp cross-referencing)
- Chain of custody (custody log completeness)
- Missing evidence (suspect–evidence linkage)
- Missing witness contact
- Procedural violation
- Legal deficiency (requirement cross-checking)
- Documentation gap

### AI Gap Analysis (Claude)
For every HIGH/CRITICAL gap, Claude adds:
- **AI Analysis** — 2-3 sentences on legal/investigative consequence
- **AI Recommendation** — specific, actionable next step naming the actual evidence item or witness

### Case Readiness Score
Transparent, weighted formula shown to judges without apology:
```
Readiness = completeness × 35%
           + evidence_integrity × 25%
           + legal_readiness × 20%
           + documentation_quality × 20%
```

### Full Provenance / Explainability
Every finding traces back to the source:
```
Finding: 13-minute timestamp discrepancy
Derived from: [E1, E3]
Method: rule:timestamp_diff
Confidence: 94%
```

### Auditable Mutation Log
Every change to the case is recorded as a `CaseMutation` with before/after snapshots, supporting rollback and human review.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude Sonnet (`claude-sonnet-4-6`) via Anthropic API |
| Orchestration | LangGraph (`StateGraph`) |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL (JSONB) / SQLite (dev) via SQLAlchemy |
| Schema | Pydantic v2 |
| Frontend | React 18 + Tailwind CSS |
| Testing | pytest (27 intelligence tests) |
| Deployment | Railway / Render (backend) · Vercel (frontend) |

---

## Architecture Overview

```
Raw Documents (PDF / TXT / paste)
         │
         ▼
 ┌───────────────┐
 │  Case Builder  │ ← Claude Sonnet (Stage 1)
 │  Agent         │   structured tool-use extraction
 └───────┬───────┘
         │ Case Object created
         ▼
 ┌──────────────────────────────────────────┐
 │           LangGraph Pipeline             │
 │                                          │
 │  Timeline Builder  →  Evidence Intel     │
 │  (rule-based)          (rule-based)      │
 │          │                    │          │
 │          ▼                    ▼          │
 │     Gap Detection  →  Gap Enhancement   │
 │     (rule-based)      (Claude Sonnet)   │
 │          │                    │          │
 │          ▼                    ▼          │
 │  Legal Intelligence → Compliance Review  │
 │  (rule-based RAG)    (rule-based)       │
 │          │                    │          │
 │          ▼                    ▼          │
 │   Health Scoring   →  Report Generation │
 │   (deterministic)    (Claude/templates) │
 └──────────────────┬───────────────────────┘
                    │
                    ▼
            Case Object
         (single source of truth)
                    │
         ┌──────────┴──────────┐
         │                     │
    FastAPI                PostgreSQL
    REST API               (JSONB store)
         │
    React Dashboard
```

---

## Project Structure

```
crimegpt-backend/
├── app/
│   ├── models/          # Case Object, entities, enums (Pydantic)
│   ├── contracts/       # Agent contracts (input/output schemas + apply())
│   ├── agents/          # One agent function per pipeline stage
│   ├── graph/           # LangGraph StateGraph builder + GraphState
│   ├── runtime/         # MutationEngine, AgentExecutor, CaseMutation
│   ├── scoring/         # Deterministic health scoring (4 modules)
│   ├── api/             # FastAPI routes (cases, analysis, reports, gaps)
│   └── db/              # SQLAlchemy models + CRUD
├── data/
│   └── burglary/        # Flagship demo case corpus + case_factory.py
├── tests/
│   └── intelligence/    # 27 intelligence tests (pytest)
├── scripts/
│   ├── demo_burglary.py # 90-second live demo script
│   └── smoke_test_*.py  # Pipeline smoke tests
└── docs/                # Full documentation suite
```

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export ANTHROPIC_API_KEY=sk-ant-...      # Required for Claude features
export DATABASE_URL=sqlite:///./crimegpt.db  # Default: SQLite

# 3. Start the API server
uvicorn app.main:app --reload

# 4. Run the demo
python -m scripts.demo_burglary

# 5. Run intelligence tests
pytest tests/intelligence/ -v
```

API docs available at `http://localhost:8000/docs`

---

## Intelligence Tests

```
27 passed in 0.06s

tests/intelligence/test_burglary_case.py
  TestPipelineHealth      (4 tests)  ✓
  TestTimeline            (4 tests)  ✓
  TestGapDetection        (9 tests)  ✓  ← flagship
  TestHealthScoring       (4 tests)  ✓
  TestLegalAnalysis       (3 tests)  ✓
  TestReports             (3 tests)  ✓
```

---

## Documentation

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Case Object, LangGraph, Mutation Engine |
| [AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | Two-layer AI design — why not just ChatGPT |
| [AGENT_SPECIFICATIONS.md](docs/AGENT_SPECIFICATIONS.md) | One spec per pipeline stage |
| [EXPLAINABILITY.md](docs/EXPLAINABILITY.md) | Provenance system deep dive |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | All REST endpoints |
| [TESTING.md](docs/TESTING.md) | Intelligence test suite documentation |
| [DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | Exact 90-second presentation script |
| [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Full technical deep dive |
| [DEVELOPMENT_JOURNEY.md](docs/DEVELOPMENT_JOURNEY.md) | Day-by-day build log |
| [ROADMAP.md](docs/ROADMAP.md) | Future features |
| [SECURITY.md](docs/SECURITY.md) | Data handling, PII, AI limitations |


