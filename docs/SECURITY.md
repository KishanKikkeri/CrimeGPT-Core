# Security

CrimeGPT processes sensitive law enforcement data. This document describes how the system handles data, protects privacy, and limits AI risk.

---

## Data Classification

CrimeGPT processes three categories of data:

| Category | Examples | Sensitivity |
|----------|---------|-------------|
| Case facts | Crime type, timestamps, locations | Standard |
| PII — victims/witnesses | Names, contact details, statements | High |
| PII — suspects | Descriptions, status, aliases | High |

All data is treated as sensitive by default.

---

## Data Handling

### What stays local

The Case Object (including all PII) is stored in your own database. CrimeGPT does not send case data to any third party except the Anthropic API for Claude-backed stages.

### What is sent to Anthropic

- **Stage 1 (Case Builder):** The raw input documents are sent to the Anthropic API for extraction.
- **Stage 4.5 (Gap Enhancement):** Gap descriptions and a case context summary (crime type, entity counts, gap details) are sent. Full PII is not included in the gap enhancement prompt.

### What is never sent

- Full witness statements or victim contact details are not included in the Gap Enhancement prompt
- Report content is never sent externally (all report generation is template-based)
- The database and case JSON are never sent to Anthropic

### Data retention

Anthropic's API does not retain input data beyond the request (see [Anthropic's privacy policy](https://www.anthropic.com/privacy)). No case data is stored by Anthropic.

---

## Audit Trail

Every change to a case is recorded as a `CaseMutation`:

```python
class CaseMutation(BaseModel):
    mutation_id: str
    case_id: str
    field: str          # which field changed
    before: Any         # value before
    after: Any          # value after
    source_agent: str   # which agent made the change
    stage: WorkflowStage
    timestamp: datetime
    review_status: "unreviewed" | "approved" | "rejected"
```

Every agent execution is recorded as an `AgentExecution`:

```python
class AgentExecution(BaseModel):
    agent_name: str
    case_id: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    confidence: float
    success: bool
    model: str          # "claude-sonnet-4-6" or "rule-based-v1"
    error: Optional[str]
```

Together, these provide a full audit trail: what changed, when, by which agent, and with what confidence.

---

## AI Limitations and Safeguards

### Hallucination risk

**Risk:** Claude may extract facts not present in the documents.

**Safeguard:** The Case Builder prompt explicitly instructs Claude: "NEVER invent names, times, locations, or facts not present in the text. Add ambiguities to `warnings` instead of guessing." The `warnings` field in `CaseBuilderOutput` surfaces Claude's uncertainty to the investigator.

**Safeguard:** Structured tool-use constrains Claude's output to a validated JSON schema. Free-text hallucinations that don't conform to the schema are rejected at parse time.

### Invented gap findings

**Risk:** An AI-only system might report gaps that don't exist.

**Safeguard:** Gap detection is fully deterministic. Claude does not produce gap findings — it only enriches gap findings that the rule-based detectors have already validated. If a gap is not found by a rule, Claude does not create it.

### Overconfident legal analysis

**Risk:** Claude might cite non-existent statutes.

**Safeguard:** The Legal Intelligence agent uses a curated knowledge base, not open-ended generation. Claude is not asked to generate legal citations — it retrieves from a pre-approved set.

### Inconsistent results

**Risk:** Two runs on the same documents produce different gaps.

**Safeguard:** Gap detection, health scoring, and compliance review are fully deterministic. Given identical inputs, the same gaps are detected on every run. Only the prose explanations from Claude (ai_analysis, ai_recommendation) may vary slightly between runs.

---

## PII Protection Recommendations

CrimeGPT is a development tool. Before production deployment in a law enforcement context:

1. **Access control:** Implement role-based authentication. Officers should only access cases they are assigned to.

2. **Data encryption:** Encrypt `case_json` at rest (PostgreSQL transparent data encryption or application-layer encryption for sensitive fields).

3. **Network security:** Run the API behind HTTPS only. Do not expose the API directly to the internet without authentication.

4. **API key management:** Store `ANTHROPIC_API_KEY` in a secrets manager (AWS Secrets Manager, HashiCorp Vault), not in environment variables on shared systems.

5. **Data residency:** If data residency requirements apply (state/national data sovereignty rules), review whether sending document text to the Anthropic API is permissible. Consider on-premises LLM alternatives.

6. **Retention policy:** Implement case data retention and deletion policies. The `DELETE /cases/{id}` endpoint supports this.

7. **Audit log access:** The mutation log and execution log should be accessible only to supervisors and auditors, not to all officers.

---

## Responsible AI Disclosure

CrimeGPT is a **decision-support tool**, not a decision-making system.

- Investigation gaps identified by CrimeGPT must be reviewed by a qualified investigator before acting on them.
- Case Readiness scores are informational. They do not constitute legal advice.
- AI-generated analysis (ai_analysis, ai_recommendation) represents Claude's reasoning, not a legal opinion. It should be treated as a starting point for investigation, not a conclusion.
- CrimeGPT should not be used as the sole basis for any legal decision, arrest, or prosecution.

All AI-generated content is clearly labelled in the UI with an `AI` badge. Rule-based findings are displayed separately from Claude-generated explanations.

---

## Reporting Security Issues

To report a security vulnerability, please email the maintainers directly rather than opening a public GitHub issue. Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigation

We aim to respond within 48 hours.
