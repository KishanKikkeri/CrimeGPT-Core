"""
Stage 2 agent function - Timeline Builder.

Rule-based v1: keeps the existing timeline (sorted chronologically
where timestamps exist, undated events last in their original order)
and flags any event with no timestamp via `missing_timestamps`.

Swap this for a Claude-backed agent later that can *derive* new
events by cross-referencing evidence/witness statements - the
contract (TimelineOutput) doesn't change either way.
"""

from __future__ import annotations

from typing import Optional

from app.contracts.timeline import TimelineOutput
from app.models.case import Case


def run(case: Case, raw_input: Optional[str]) -> TimelineOutput:
    dated = [e for e in case.timeline if e.timestamp is not None]
    undated = [e for e in case.timeline if e.timestamp is None]

    dated.sort(key=lambda e: e.timestamp)

    missing_timestamps = [
        f"Event {e.event_id} ('{e.description[:60]}') has no timestamp"
        for e in undated
    ]

    return TimelineOutput(
        confidence=0.9 if not missing_timestamps else 0.7,
        timeline_events=dated + undated,
        missing_timestamps=missing_timestamps,
    )
