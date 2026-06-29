"""
Stage 4.5 — Gap Enhancement Agent.

Uses Claude to add visible AI reasoning on top of the deterministic
gap detection layer. Two things Claude adds that rules cannot:

  1. ai_analysis   — narrative explanation of WHY a gap matters
                     (e.g. "The 13-minute discrepancy could indicate the
                     witness reported time of observation vs. time of
                     entry, or clock desynchronisation — either undermines
                     the timeline in cross-examination.")

  2. ai_recommendation — specific copilot next action, naming the
                     actual evidence item, witness, or procedure:
                     "Obtain the fingerprint analysis report for EV-001
                     from the rear window frame before the case advances
                     to legal review."

Claude only enhances HIGH and CRITICAL severity gaps (the ones that
actually matter for legal proceedings). LOW/MEDIUM gaps keep their
rule-based recommendations — this keeps latency and token cost
proportional to importance.

No-op mode: if ANTHROPIC_API_KEY is not set or the call fails, the
function returns immediately with no changes — the pipeline continues
with the rule-based gaps intact. The system degrades gracefully.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from app.contracts.gap_enhancement import GapEnhancementOutput
from app.models.case import Case
from app.models.entities import InvestigationGap
from app.models.enums import Severity

MODEL_NAME = "claude-sonnet-4-6"

# Only enhance these severities — critical path for the demo
ENHANCE_SEVERITIES = {Severity.HIGH, Severity.CRITICAL}

_SYSTEM_PROMPT = """You are the Investigation Analyst for CrimeGPT, an AI investigation copilot.

You will be given a list of investigation gaps found in a criminal case, along with the case context. For each gap I provide, you must output a JSON object with:

  "id": the exact gap id I gave you
  "ai_analysis": 2-3 sentences explaining WHY this gap matters legally or investigatively. Be specific about legal consequences, cross-examination risks, and admissibility implications.
  "ai_recommendation": 1-2 sentences giving the investigator a SPECIFIC, actionable next step — name the actual evidence item, witness, or document. Start with an active verb.

Rules:
- Be precise and specific. Name the actual evidence IDs, witness names, or procedures involved.
- For timeline contradictions: explain what could cause the discrepancy and what legal risk it creates.
- For chain-of-custody gaps: explain what the admissibility consequence is.
- For missing witnesses: explain what cross-examination risk it creates.
- Never say "it is important to..." — just say what to do and why.
- Output ONLY a JSON array of objects. No prose, no markdown, no explanation outside the JSON.
"""


def _build_gap_prompt(case: Case, gaps_to_enhance: list[InvestigationGap]) -> str:
    case_ctx = (
        f"Case: {case.title}\n"
        f"Crime type: {case.crime_type or 'unspecified'}\n"
        f"Suspects: {len(case.suspects)} | Witnesses: {len(case.witnesses)} | Evidence items: {len(case.evidence)}\n"
        f"Timeline events: {len(case.timeline)}\n"
    )

    gaps_json = json.dumps(
        [
            {
                "id": g.id,
                "severity": g.severity.value,
                "category": g.category.value,
                "description": g.description,
                "rule_based_recommendation": g.recommendation,
                "provenance": {
                    "derived_from": g.provenance.derived_from,
                    "method": g.provenance.method,
                    "confidence": g.provenance.confidence,
                },
            }
            for g in gaps_to_enhance
        ],
        indent=2,
    )

    return f"{case_ctx}\nGaps to analyse:\n{gaps_json}"


def _call_claude(case: Case, gaps_to_enhance: list[InvestigationGap]) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_gap_prompt(case, gaps_to_enhance)}],
    )

    text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    ).strip()

    # Strip markdown fences if Claude added them despite instructions
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()

    return json.loads(text)


def run(case: Case, raw_input: Optional[str]) -> GapEnhancementOutput:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return GapEnhancementOutput(
            confidence=0.0,
            enhanced_gaps=case.investigation_gaps,
            warnings=["No ANTHROPIC_API_KEY — gap enhancement skipped, using rule-based recommendations."],
        )

    gaps_to_enhance = [
        g for g in case.investigation_gaps if g.severity in ENHANCE_SEVERITIES
    ]

    if not gaps_to_enhance:
        return GapEnhancementOutput(
            confidence=1.0,
            enhanced_gaps=case.investigation_gaps,
        )

    try:
        enrichments = _call_claude(case, gaps_to_enhance)
        enrich_map = {e["id"]: e for e in enrichments if "id" in e}

        enriched: list[InvestigationGap] = []
        for gap in case.investigation_gaps:
            if gap.id in enrich_map:
                e = enrich_map[gap.id]
                enriched.append(gap.model_copy(update={
                    "ai_analysis": e.get("ai_analysis"),
                    "ai_recommendation": e.get("ai_recommendation"),
                }))
            else:
                enriched.append(gap)

        return GapEnhancementOutput(confidence=0.88, enhanced_gaps=enriched)

    except Exception as exc:
        return GapEnhancementOutput(
            confidence=0.0,
            enhanced_gaps=case.investigation_gaps,
            warnings=[f"Gap enhancement Claude call failed ({exc}) — using rule-based recommendations."],
        )
