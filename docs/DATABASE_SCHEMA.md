# Database Schema

CrimeGPT uses a single-table JSONB strategy for the hackathon. The entire Case Object is stored as a JSON document in one row.

---

## Cases Table

```sql
CREATE TABLE cases (
    id          VARCHAR(36)  PRIMARY KEY,
    case_id     VARCHAR(64)  UNIQUE NOT NULL,
    title       TEXT         NOT NULL DEFAULT 'Untitled Case',
    status      VARCHAR(32)  NOT NULL DEFAULT 'created',
    case_json   TEXT         NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_case_id ON cases(case_id);
CREATE INDEX idx_cases_status  ON cases(status);
```

### Column details

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(36) | UUID primary key (internal DB key) |
| `case_id` | VARCHAR(64) | Application-level ID (e.g. `CASE-2026-A4F91B`) |
| `title` | TEXT | Case title, duplicated from `case_json` for list queries |
| `status` | TEXT | Case lifecycle status, duplicated for filtering |
| `case_json` | TEXT | Complete `Case` Pydantic model as JSON (JSONB on Postgres) |
| `created_at` | TIMESTAMP | First creation time |
| `updated_at` | TIMESTAMP | Last update time |

`title` and `status` are duplicated from the JSON document to support lightweight list queries (`GET /cases`) without parsing every row's `case_json`.

---

## Why a Single Table

**Hackathon rule:** optimise for velocity, not purity.

The Case Object is a deeply nested structure:

```
Case
├── victims[]        (each with optional contact, injuries, statement)
├── suspects[]       (each with aliases, linked_evidence[], linked_events[])
├── witnesses[]      (each with reliability_score)
├── evidence[]       (each with chain_of_custody[])
├── timeline[]       (each with linked_people[], linked_evidence[])
├── legal_analysis   (with statutes[], precedents[], provenance)
├── investigation_gaps[] (each with provenance, ai_analysis, ai_recommendation)
├── compliance_findings[]
├── reports[]        (with full content text)
└── health           (four sub-scores)
```

Normalising this would produce 15+ tables. Every API read would require 15+ joins. Every write would require 15+ inserts/updates in a transaction. For a hackathon, the cost is not worth the benefit.

**The JSONB approach gives us:**

- Atomic reads/writes — the entire case in one query
- Zero schema migration risk during the hackathon
- Direct querying when needed (`case_json->>'crime_type' = 'burglary'` on Postgres)
- Easy path to normalisation post-hackathon for specific performance needs

---

## The Case JSON Document

The `case_json` field stores the exact output of `case.model_dump_json()`. Deserialisation uses `Case.model_validate_json(row.case_json)`.

Example (abbreviated):

```json
{
  "case_id": "CASE-2026-A4F91B",
  "title": "Residential Burglary — 14 Maple Street, Greenfields",
  "status": "report_generated",
  "priority": "high",
  "jurisdiction": "Greenfields, Karnataka",
  "crime_type": "burglary",
  "created_at": "2026-06-14T03:30:00",
  "updated_at": "2026-06-14T03:32:15",
  "summary": "A masked individual forced entry...",
  "raw_documents": ["Officer Notes...", "Witness Statement..."],
  "victims": [{"id": "V1", "name": "Rajesh Iyer", ...}],
  "suspects": [{"id": "S1", "description": "Masked individual...", "status": "unknown", ...}],
  "witnesses": [
    {"id": "W1", "name": "Kavitha Patel", "contact": "12 Maple Street", ...},
    {"id": "W2", "name": null, "contact": null, ...}
  ],
  "evidence": [
    {
      "evidence_id": "EV-001",
      "type": "forensic",
      "title": "Fingerprint smudges — kitchen window frame",
      "chain_of_custody": [],
      "admissibility_status": "questionable",
      ...
    },
    ...
  ],
  "timeline": [
    {"event_id": "E1", "timestamp": "2026-06-14T02:03:00", "confidence": 0.8, ...},
    ...
  ],
  "investigation_gaps": [
    {
      "id": "G-TC-E1-E3",
      "severity": "high",
      "category": "timeline_contradiction",
      "description": "Events E1 and E3...",
      "recommendation": "Re-verify both timestamps...",
      "ai_analysis": "This discrepancy is legally significant...",
      "ai_recommendation": "Obtain the CCTV device technical log...",
      "provenance": {"derived_from": ["E1", "E3"], "method": "rule:timestamp_diff", "confidence": 0.94}
    },
    ...
  ],
  "legal_analysis": {
    "statutes": ["BNS Section 305...", "BNS Section 306..."],
    "confidence": 0.85,
    "provenance": {"derived_from": ["bns_burglary_2023.md"], "method": "rag_retrieval", "confidence": 0.85}
  },
  "health": {"completeness": 100, "evidence_integrity": 25, "legal_readiness": 40, "documentation_quality": 85},
  "reports": [{"report_id": "RPT-A1B2C3D4", "type": "investigation_report", "content": "..."}],
  "current_stage": "done",
  "completed_stages": ["case_builder", "timeline_builder", ...]
}
```

---

## Environment Configuration

```bash
# Development (default — SQLite, zero config)
# DATABASE_URL not set → uses sqlite:///./crimegpt.db

# PostgreSQL (production)
export DATABASE_URL="postgresql://user:password@localhost:5432/crimegpt"
```

---

## PostgreSQL Upgrade (post-hackathon)

Change `case_json` from `TEXT` to `JSONB`:

```sql
ALTER TABLE cases ALTER COLUMN case_json TYPE JSONB USING case_json::jsonb;

-- Enable GIN index for full-document search
CREATE INDEX idx_cases_json ON cases USING gin(case_json);

-- Example queries after upgrade
SELECT * FROM cases WHERE case_json->>'crime_type' = 'burglary';
SELECT * FROM cases WHERE case_json @> '{"status": "report_generated"}';
SELECT * FROM cases WHERE (case_json->'health'->>'overall')::int > 80;
```
