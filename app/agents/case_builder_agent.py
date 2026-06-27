"""
Stage 1 — Case Builder Agent.

The most visible AI feature in CrimeGPT: takes messy, unstructured
officer notes, witness statements, and evidence logs and converts them
into a fully-structured Case Object.

Claude path (when ANTHROPIC_API_KEY is set):
  - Structured output via tool use (guaranteed JSON schema)
  - Handles multi-document input (documents concatenated with separators)
  - Extracts: title, crime_type, summary, victims, suspects, witnesses,
    evidence items, timeline events
  - Never invents details not present in the text; uses warnings instead

Heuristic fallback (when no API key or Claude call fails):
  - Regex-based extraction good enough to exercise the rest of the pipeline
  - Clearly labelled as fallback in warnings so the demo can flag it

Demo value: the judge sees "4 messy documents" → "1 victim, 2 witnesses,
3 evidence items, 7 timeline events" and immediately understands the AI value.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Optional

from app.contracts.case_builder import CaseBuilderOutput
from app.models.case import Case
from app.models.entities import Evidence, Suspect, TimelineEvent, Victim, Witness
from app.models.enums import EvidenceType, SuspectStatus

MODEL_NAME = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """\
You are the Case Builder for CrimeGPT, an AI investigation copilot for law enforcement. 
Your job is to extract structured case information from raw, messy investigation documents.

The user will provide one or more documents separated by "=== DOCUMENT: <name> ===" headers.

Instructions:
- Extract ONLY what is explicitly stated or strongly implied by the documents.
- NEVER invent names, times, locations, or facts not present in the text.
- If a field is unclear or absent, omit it or add a note to `warnings`.
- Use short stable IDs: V1/V2 for victims, S1/S2 for suspects, W1/W2 for witnesses, EV-001/EV-002 for evidence, E1/E2 for timeline events.
- Timeline events: assign timestamps ONLY where explicitly stated; set confidence based on source reliability (CCTV=0.95, signed statement=0.85, informal report=0.6).
- For `crime_type` use lowercase single word: burglary, theft, assault, fraud, etc.
- `extracted_summary` should be 2-4 neutral factual sentences describing what happened.
- Set top-level `confidence` to your overall extraction confidence (0.0-1.0).
- Add any ambiguities, missing information, or assumptions to `warnings`.
"""

# -----------------------------------------------------------------------
# JSON schema for Claude's tool-use structured output
# -----------------------------------------------------------------------

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short case title, e.g. 'Residential Burglary — 14 Maple Street'"},
        "crime_type": {"type": "string", "description": "Single lowercase word: burglary, theft, assault, fraud, etc."},
        "jurisdiction": {"type": "string", "description": "Location/jurisdiction if stated"},
        "extracted_summary": {"type": "string", "description": "2-4 neutral factual sentences"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "victims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "gender": {"type": "string"},
                    "contact": {"type": "string"},
                    "injuries": {"type": "string"},
                    "statement": {"type": "string"},
                },
                "required": ["id"],
            },
        },
        "suspects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "known_aliases": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["unknown", "identified", "detained", "arrested"]},
                    "linked_evidence": {"type": "array", "items": {"type": "string"}},
                    "linked_events": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "status"],
            },
        },
        "witnesses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "contact": {"type": "string"},
                    "statement": {"type": "string"},
                },
                "required": ["id"],
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "type": {"type": "string", "enum": ["physical", "digital", "document", "cctv", "photo", "audio", "forensic", "other"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {"type": "string"},
                    "collected_by": {"type": "string"},
                    "linked_people": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["evidence_id", "title"],
            },
        },
        "timeline_events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "timestamp_str": {"type": "string", "description": "Time as stated in docs, e.g. '02:03 AM'"},
                    "description": {"type": "string"},
                    "source": {"type": "string", "description": "witness_statement_W1, evidence_EV-002, dispatch_log, etc."},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "linked_people": {"type": "array", "items": {"type": "string"}},
                    "linked_evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["event_id", "description"],
            },
        },
    },
    "required": ["title", "extracted_summary", "confidence"],
}


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse '02:03 AM', '14:30', '2:03am', etc. into datetime (today's date)."""
    if not ts:
        return None
    ts = ts.strip().upper()
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p", "%I %p"):
        try:
            t = datetime.strptime(ts, fmt)
            return datetime.utcnow().replace(
                hour=t.hour, minute=t.minute, second=0, microsecond=0
            )
        except ValueError:
            continue
    return None


def _build_from_claude_output(data: dict) -> CaseBuilderOutput:
    victims = [
        Victim(
            id=v["id"],
            name=v.get("name"),
            age=v.get("age"),
            gender=v.get("gender"),
            contact=v.get("contact"),
            injuries=v.get("injuries"),
            statement=v.get("statement"),
        )
        for v in data.get("victims", [])
    ]

    suspects = [
        Suspect(
            id=s["id"],
            name=s.get("name"),
            known_aliases=s.get("known_aliases", []),
            description=s.get("description"),
            status=SuspectStatus(s.get("status", "unknown")),
            linked_evidence=s.get("linked_evidence", []),
            linked_events=s.get("linked_events", []),
        )
        for s in data.get("suspects", [])
    ]

    witnesses = [
        Witness(
            id=w["id"],
            name=w.get("name"),
            contact=w.get("contact"),
            statement=w.get("statement"),
        )
        for w in data.get("witnesses", [])
    ]

    evidence_type_map = {e.value: e for e in EvidenceType}
    evidence = [
        Evidence(
            evidence_id=e["evidence_id"],
            type=evidence_type_map.get(e.get("type", "other"), EvidenceType.OTHER),
            title=e["title"],
            description=e.get("description"),
            source=e.get("source"),
            collected_by=e.get("collected_by"),
            linked_people=e.get("linked_people", []),
        )
        for e in data.get("evidence", [])
    ]

    timeline_events = [
        TimelineEvent(
            event_id=ev["event_id"],
            timestamp=_parse_timestamp(ev.get("timestamp_str")),
            description=ev["description"],
            source=ev.get("source"),
            confidence=ev.get("confidence"),
            linked_people=ev.get("linked_people", []),
            linked_evidence=ev.get("linked_evidence", []),
        )
        for ev in data.get("timeline_events", [])
    ]

    return CaseBuilderOutput(
        confidence=float(data.get("confidence", 0.7)),
        warnings=data.get("warnings", []),
        title=data.get("title", "Untitled Case"),
        crime_type=data.get("crime_type"),
        extracted_summary=data.get("extracted_summary", ""),
        victims=victims,
        suspects=suspects,
        witnesses=witnesses,
        evidence=evidence,
        timeline_events=timeline_events,
    )


def _call_claude(raw_input: str) -> CaseBuilderOutput:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_input}],
        tools=[
            {
                "name": "submit_case_structure",
                "description": "Submit the complete structured extraction of the case.",
                "input_schema": _OUTPUT_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "submit_case_structure"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_case_structure":
            return _build_from_claude_output(block.input)

    raise RuntimeError("Claude did not return submit_case_structure tool use block")


# -----------------------------------------------------------------------
# Heuristic fallback
# -----------------------------------------------------------------------

_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b")


def _heuristic_extract(raw_input: str) -> CaseBuilderOutput:
    """
    Minimal regex-based extraction. Good enough to run the pipeline
    in CI / local dev without a Claude API key. Deliberately conservative
    — never invents data.
    """
    text = raw_input.strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if len(s.strip()) > 20]

    timeline_events: list[TimelineEvent] = []
    for i, sentence in enumerate(sentences[:15], start=1):
        m = _TIME_RE.search(sentence)
        ts = None
        confidence = 0.5
        if m:
            hour, minute, meridiem = m.groups()
            h = int(hour) % 12 + (12 if meridiem.upper() == "PM" else 0)
            try:
                ts = datetime.utcnow().replace(hour=h, minute=int(minute), second=0, microsecond=0)
                confidence = 0.65
            except ValueError:
                pass
        timeline_events.append(TimelineEvent(
            event_id=f"E{i}",
            timestamp=ts,
            description=sentence[:200],
            source="raw_text",
            confidence=confidence,
        ))

    suspects = []
    if re.search(r"\bmasked|suspect|unknown (man|woman|individual|person)\b", text, re.I):
        suspects.append(Suspect(
            id="S1",
            description="Unidentified individual (extracted by heuristic)",
            status=SuspectStatus.UNKNOWN,
        ))

    witnesses = []
    if re.search(r"\bwitness(ed)?\b", text, re.I):
        witnesses.append(Witness(id="W1", statement=text[:500]))

    evidence = []
    if re.search(r"\bcctv|camera|footage\b", text, re.I):
        evidence.append(Evidence(
            evidence_id="EV-001",
            type=EvidenceType.CCTV,
            title="CCTV footage referenced in documents",
            source="raw_text",
        ))

    return CaseBuilderOutput(
        confidence=0.35,
        title=f"Case — {uuid.uuid4().hex[:6].upper()}",
        crime_type=None,
        extracted_summary=text[:400],
        victims=[],
        suspects=suspects,
        witnesses=witnesses,
        evidence=evidence,
        timeline_events=timeline_events,
        warnings=[
            "⚠ Generated by heuristic fallback extractor (ANTHROPIC_API_KEY not set "
            "or Claude call failed). Review and supplement manually before proceeding."
        ],
    )


# -----------------------------------------------------------------------
# Public entry point
# -----------------------------------------------------------------------

def run(case: Case, raw_input: Optional[str]) -> CaseBuilderOutput:
    if not raw_input or not raw_input.strip():
        raise ValueError("case_builder requires non-empty raw_input")

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _call_claude(raw_input)
        except Exception as exc:
            pass  # fall through to heuristic

    return _heuristic_extract(raw_input)
