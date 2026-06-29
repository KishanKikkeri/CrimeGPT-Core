# API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

All endpoints return JSON. All timestamps are ISO 8601 UTC.

---

## Cases

### Create a case

```http
POST /cases
Content-Type: application/json

{
  "title": "Residential Burglary — 14 Maple Street",
  "raw_input": null,
  "jurisdiction": "Greenfields, Karnataka",
  "crime_type": "burglary"
}
```

Creates a new case. Stores it immediately so the UI can show it while analysis runs.

**Response 201:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "title": "Residential Burglary — 14 Maple Street",
  "status": "created",
  "created_at": "2026-06-14T03:30:00Z",
  "_raw_input": null
}
```

---

### List all cases

```http
GET /cases?skip=0&limit=50
```

Returns lightweight summaries (no full case JSON) for the case list view.

**Response 200:**
```json
[
  {
    "case_id": "CASE-2026-A4F91B",
    "title": "Residential Burglary — 14 Maple Street",
    "status": "report_generated",
    "created_at": "2026-06-14T03:30:00Z",
    "updated_at": "2026-06-14T03:32:15Z"
  }
]
```

---

### Get a case

```http
GET /cases/{case_id}
```

Returns the full Case Object as JSON.

**Response 200:** Full `Case` model (see `app/models/case.py` for schema)

**Response 404:** `{"detail": "Case 'CASE-2026-A4F91B' not found"}`

---

### Delete a case

```http
DELETE /cases/{case_id}
```

**Response 204:** No content

---

## Analysis

### Run full analysis (Stages 1–8)

```http
POST /cases/{case_id}/analyze
Content-Type: application/json

{
  "raw_input": "=== DOCUMENT: incident.txt ===\nOfficer Notes...\n\n=== DOCUMENT: witness_1.txt ===\nWitness Statement...",
  "report_types": ["investigation_report"]
}
```

Runs the complete pipeline: Claude extraction → timeline → evidence → gaps → AI enrichment → legal → compliance → scoring → report.

`raw_input` is required. For multiple documents, concatenate with `=== DOCUMENT: <name> ===` separators.

`report_types` options: `case_summary`, `investigation_report`, `court_brief`, `evidence_summary`, `executive_intelligence_report`

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "status": "report_generated",
  "health": {
    "completeness": 100,
    "evidence_integrity": 25,
    "legal_readiness": 40,
    "documentation_quality": 85
  },
  "health_overall": 66,
  "gaps_found": 13,
  "reports_generated": 1,
  "stages_completed": ["case_builder", "timeline_builder", "evidence_intelligence",
                        "gap_detection", "gap_enhancement", "legal_intelligence",
                        "compliance_review", "health_scoring", "report_generation"],
  "mutations": 9,
  "executions": [
    {
      "agent": "case_builder",
      "duration_ms": 1842,
      "confidence": 0.88,
      "success": true,
      "model": "claude-sonnet-4-6"
    },
    ...
  ]
}
```

---

### Re-analyse from gap detection (Stages 4–8)

```http
POST /cases/{case_id}/reanalyze
Content-Type: application/json

{
  "report_types": ["investigation_report", "court_brief"]
}
```

Re-runs Stages 4–8 on an already-structured case. Use when new evidence arrives and you want updated gaps/compliance/scoring without re-running the document extraction.

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "health_overall": 72,
  "gaps_found": 10,
  "stages_run": ["gap_detection", "gap_enhancement", "legal_intelligence",
                  "compliance_review", "health_scoring", "report_generation"]
}
```

---

## Timeline

### Get the case timeline

```http
GET /cases/{case_id}/timeline
```

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "total": 7,
  "events": [
    {
      "event_id": "E1",
      "timestamp": "2026-06-14T02:03:00Z",
      "description": "Witness W1 observes masked individual entering through rear kitchen window",
      "source": "witness_statement_W1",
      "confidence": 0.8,
      "linked_people": ["W1", "S1"],
      "linked_evidence": []
    },
    ...
  ]
}
```

---

## Investigation Gaps

### Get all gaps

```http
GET /cases/{case_id}/gaps
GET /cases/{case_id}/gaps?severity=high
GET /cases/{case_id}/gaps?category=timeline_contradiction
```

Optional query params: `severity` (critical/high/medium/low), `category` (timeline_contradiction/chain_of_custody/missing_evidence/missing_witness/procedural_violation/legal_deficiency/documentation_gap)

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "total": 13,
  "by_severity": {"critical": 0, "high": 5, "medium": 4, "low": 4},
  "gaps": [
    {
      "id": "G-TC-E1-E3",
      "severity": "high",
      "category": "timeline_contradiction",
      "description": "Events E1 and E3 both involve S1 but differ in time by 13 minutes...",
      "recommendation": "Re-verify both timestamps...",
      "provenance": {
        "derived_from": ["E1", "E3"],
        "method": "rule:timestamp_diff",
        "confidence": 0.94,
        "notes": "Source A: witness_statement_W1 | Source B: evidence_EV-002 | Δt = 13 min"
      }
    },
    ...
  ]
}
```

---

## Case Health

### Get health score and breakdown

```http
GET /cases/{case_id}/health
```

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "overall": 66,
  "sub_scores": {
    "completeness": 100,
    "evidence_integrity": 25,
    "legal_readiness": 40,
    "documentation_quality": 85
  },
  "weights": {
    "completeness": 0.35,
    "evidence_integrity": 0.25,
    "legal_readiness": 0.20,
    "documentation_quality": 0.20
  },
  "breakdown": {
    "completeness": {"summary": true, "crime_type": true, ...},
    "evidence_integrity": [
      {"evidence_id": "EV-001", "has_custody_chain": false, "ok": false},
      ...
    ],
    ...
  }
}
```

---

## Reports

### List reports for a case

```http
GET /cases/{case_id}/reports
```

**Response 200:**
```json
{
  "case_id": "CASE-2026-A4F91B",
  "reports": [
    {
      "report_id": "RPT-A1B2C3D4",
      "type": "investigation_report",
      "version": 1,
      "generated_at": "2026-06-14T03:32:10Z"
    }
  ]
}
```

---

### Generate a new report (on demand)

```http
POST /cases/{case_id}/reports
Content-Type: application/json

{
  "report_type": "executive_intelligence_report"
}
```

Generates without re-running the full pipeline. Available anytime after analysis.

**Response 201:**
```json
{
  "report_id": "RPT-E5F6G7H8",
  "type": "executive_intelligence_report",
  "version": 1,
  "content": "EXECUTIVE INTELLIGENCE REPORT — Residential Burglary..."
}
```

---

### Get a specific report

```http
GET /cases/{case_id}/reports/{report_id}
```

**Response 200:**
```json
{
  "report_id": "RPT-A1B2C3D4",
  "type": "investigation_report",
  "version": 1,
  "generated_at": "2026-06-14T03:32:10Z",
  "content": "INVESTIGATION REPORT — Residential Burglary..."
}
```

---

## Health Check

```http
GET /health
```

**Response 200:**
```json
{"status": "ok"}
```

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 404 | Case or report not found |
| 422 | Validation error (e.g. missing `raw_input` for `/analyze`) |
| 500 | Pipeline error (check `detail` field for stage and error) |
