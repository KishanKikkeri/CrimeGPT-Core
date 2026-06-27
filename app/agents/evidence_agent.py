"""
Stage 3 agent function - Evidence Intelligence.

Rule-based v1:
  - For each evidence item, finds timeline events that already
    reference it (`TimelineEvent.linked_evidence`) and back-fills
    `linked_events` / `linked_people` on the Evidence item.
  - Sets `admissibility_status`: ADMISSIBLE if a chain-of-custody
    exists, QUESTIONABLE otherwise.
  - Surfaces a gap for any evidence item with no chain of custody,
    and any with no linked timeline events at all.
"""

from __future__ import annotations

from typing import Optional

from app.contracts.evidence import EvidenceLink, EvidenceOutput
from app.models.case import Case
from app.models.enums import AdmissibilityStatus


def run(case: Case, raw_input: Optional[str]) -> EvidenceOutput:
    links: list[EvidenceLink] = []
    gaps: list[str] = []
    admissibility_warnings: list[str] = []

    for ev in case.evidence:
        linked_events = [e.event_id for e in case.timeline if ev.evidence_id in e.linked_evidence]
        linked_people: set[str] = set(ev.linked_people)
        for e in case.timeline:
            if ev.evidence_id in e.linked_evidence:
                linked_people.update(e.linked_people)

        if ev.chain_of_custody:
            status = AdmissibilityStatus.ADMISSIBLE
            note = "Chain of custody documented."
        else:
            status = AdmissibilityStatus.QUESTIONABLE
            note = "No chain-of-custody entries recorded."
            admissibility_warnings.append(
                f"Evidence {ev.evidence_id} ('{ev.title}') has no chain-of-custody entries."
            )

        if not linked_events:
            gaps.append(
                f"Evidence {ev.evidence_id} ('{ev.title}') is not linked to any timeline event."
            )

        links.append(
            EvidenceLink(
                evidence_id=ev.evidence_id,
                linked_events=linked_events,
                linked_people=sorted(linked_people),
                admissibility_status=status,
                admissibility_note=note,
            )
        )

    return EvidenceOutput(
        confidence=0.85 if case.evidence else 0.5,
        evidence_links=links,
        evidence_gaps=gaps,
        admissibility_warnings=admissibility_warnings,
    )
