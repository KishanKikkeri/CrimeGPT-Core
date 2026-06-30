"""
Builds the pre-structured burglary Case Object for intelligence tests
and the demo runner.

The Case Builder Agent (Stage 1) is responsible for extracting this
from raw text. This factory constructs the same Case *directly* — with
the deliberate contradictions, chain-of-custody gaps, and missing
witness contact data baked in — so intelligence tests can run Stages
2-8 without requiring an ANTHROPIC_API_KEY or waiting for Stage 1.

This is also how the 90-second demo is guaranteed to produce the
right "wow" moments regardless of environment.
"""

from __future__ import annotations

from datetime import datetime

from app.models.case import Case
from app.models.entities import (
    CustodyEntry,
    Evidence,
    ReliabilityScore,
    Suspect,
    TimelineEvent,
    Victim,
    Witness,
)
from app.models.enums import (
    AdmissibilityStatus,
    CasePriority,
    EvidenceType,
    SuspectStatus,
)

_BASE = datetime(2026, 6, 14, 0, 0, 0)


def _t(hour: int, minute: int) -> datetime:
    return _BASE.replace(hour=hour, minute=minute)


def build_burglary_case() -> Case:
    """
    Returns the Maple Street burglary Case with Stage 1 already complete.
    Ready for Stages 2-8 (timeline builder through report generation).
    """
    case = Case(
        title="Residential Burglary — 14 Maple Street, Greenfields",
        crime_type="burglary",
        priority=CasePriority.HIGH,
        jurisdiction="Greenfields, Karnataka",
        summary=(
            "A residential burglary occurred at 14 Maple Street during the "
            "early hours of June 14 2026. An unidentified masked individual "
            "forced entry through the rear kitchen window while the occupant "
            "was away. A laptop and bag were reported stolen. Police arrived "
            "at 02:31 AM. CCTV evidence and fingerprint samples were "
            "collected, though chain-of-custody documentation is incomplete."
        ),
    )

    # ----- Victims -----
    case.victims = [
        Victim(
            id="V1",
            name="Rajesh Iyer",
            contact="Travelling — Hyderabad (unreachable at time of incident)",
            injuries="None",
        )
    ]

    # ----- Suspects -----
    # Unknown masked individual — no name, no evidence linked yet
    case.suspects = [
        Suspect(
            id="S1",
            description="Masked individual, dark clothing, medium build, appeared male",
            status=SuspectStatus.UNKNOWN,
        )
    ]

    # ----- Witnesses -----
    case.witnesses = [
        Witness(
            id="W1",
            name="Kavitha Patel",
            contact="12 Maple Street, Greenfields",
            statement=(
                "Observed a masked individual entering through the rear "
                "kitchen window at approximately 02:03 AM. Called emergency "
                "services at approximately 02:08 AM. Signed statement recorded."
            ),
            reliability_score=ReliabilityScore(
                source="single witness; good vantage but poor lighting",
                confidence=0.65,
            ),
        ),
        Witness(
            id="W2",
            name=None,          # DELIBERATE: anonymous
            contact=None,       # DELIBERATE: no contact — MISSING_WITNESS gap
            statement=(
                "Anonymous passerby. Observed a dark sedan idling near "
                "the rear alley at approximately 02:25 AM. Someone appeared "
                "to be carrying a large dark item toward the car. Vehicle "
                "drove away without headlights northbound on Cypress Lane."
            ),
            reliability_score=None,  # DELIBERATE: unverified
        ),
    ]

    # ----- Evidence -----
    case.evidence = [
        Evidence(
            evidence_id="EV-001",
            type=EvidenceType.FORENSIC,
            title="Fingerprint smudges — kitchen window frame (exterior)",
            description=None,     # DELIBERATE: no description recorded
            source="Scene collection, 14 Maple Street",
            collected_by="Constable Arjun Mehta",
            collected_at=_t(2, 45),
            chain_of_custody=[],  # DELIBERATE: no custody chain — GAP
            linked_people=["S1"],
            admissibility_status=AdmissibilityStatus.QUESTIONABLE,
        ),
        Evidence(
            evidence_id="EV-002",
            type=EvidenceType.CCTV,
            title="CCTV drive — 16 Maple Street, Camera 3 (rear alley)",
            description=(
                "Footage shows individual in dark clothing near rear window "
                "of 14 Maple Street at 02:16 AM. Camera timestamp verified "
                "against station clock."
            ),
            source="16 Maple Street (owner D. Krishnamurthy)",
            collected_by="Constable Arjun Mehta",
            collected_at=_t(3, 15),
            chain_of_custody=[
                CustodyEntry(
                    timestamp=_t(3, 15),
                    holder="Constable Arjun Mehta",
                    action="Collected from owner D. Krishnamurthy",
                    location="16 Maple Street",
                ),
                CustodyEntry(
                    timestamp=_t(4, 10),
                    holder="Constable Arjun Mehta",
                    action="Transferred to station evidence locker",
                    location="Greenfields Police Station",
                ),
            ],
            linked_people=["S1"],
            linked_events=["E2"],  # CCTV event
            admissibility_status=AdmissibilityStatus.ADMISSIBLE,
        ),
        Evidence(
            evidence_id="EV-003",
            type=EvidenceType.PHYSICAL,
            title="Recovered bag — dark brown leather, found near alley dumpster",
            description=None,     # DELIBERATE: no description
            source="Rear alley, ~40m from 14 Maple Street",
            collected_by="Constable Priya Nair",
            collected_at=None,    # DELIBERATE: time not recorded
            chain_of_custody=[],  # DELIBERATE: no custody chain — GAP
            linked_people=[],
            admissibility_status=AdmissibilityStatus.QUESTIONABLE,
        ),
        Evidence(
            evidence_id="EV-004",
            type=EvidenceType.PHOTO,
            title="Scene photographs (14 photos) — entry point and recovered bag",
            description=(
                "14 photographs: forced window, glass fragments on floor, "
                "exterior sill, alley view, recovered bag."
            ),
            source="Constable Mehta personal phone — to be transferred",
            collected_by="Constable Arjun Mehta",
            collected_at=None,    # DELIBERATE: camera clock unverified
            chain_of_custody=[],  # DELIBERATE: no custody chain
            linked_people=[],
            admissibility_status=AdmissibilityStatus.QUESTIONABLE,
        ),
    ]

    # ----- Timeline -----
    # Deliberate contradiction baked in:
    #   E1 (witness): 02:03 AM — suspect entering window
    #   E2 (CCTV):   02:16 AM — suspect at window
    # Both events link to S1. Gap detector will find the 13-minute
    # contradiction automatically.
    case.timeline = [
        TimelineEvent(
            event_id="E1",
            timestamp=_t(2, 3),
            description="Witness W1 (Mrs. Patel) observes masked individual entering through rear kitchen window",
            source="witness_statement_W1",
            confidence=0.8,
            linked_people=["W1", "S1"],
            linked_evidence=[],
        ),
        TimelineEvent(
            event_id="E2",
            timestamp=_t(2, 8),
            description="Witness W1 calls emergency services",
            source="witness_statement_W1",
            confidence=0.9,
            linked_people=["W1"],
            linked_evidence=[],
        ),
        TimelineEvent(
            event_id="E3",
            timestamp=_t(2, 16),
            description="CCTV Camera 3 shows masked individual in dark clothing at rear window of 14 Maple Street",
            source="evidence_EV-002",
            confidence=0.95,
            linked_people=["S1"],
            linked_evidence=["EV-002"],
        ),
        TimelineEvent(
            event_id="E4",
            timestamp=_t(2, 25),
            description="Anonymous witness (W2) observes dark sedan near alley with individual carrying large dark item",
            source="witness_statement_W2",
            confidence=0.55,
            linked_people=["W2", "S1"],
            linked_evidence=[],
        ),
        TimelineEvent(
            event_id="E5",
            timestamp=_t(2, 31),
            description="Officers Mehta and Nair arrive at 14 Maple Street",
            source="dispatch_log",
            confidence=0.98,
            linked_people=[],
            linked_evidence=[],
        ),
        TimelineEvent(
            event_id="E6",
            timestamp=_t(2, 45),
            description="Fingerprint samples collected from forced kitchen window frame exterior",
            source="incident_report",
            confidence=0.9,
            linked_people=[],
            linked_evidence=["EV-001"],
        ),
        TimelineEvent(
            event_id="E7",
            timestamp=_t(3, 15),
            description="CCTV drive collected from property owner D. Krishnamurthy at 16 Maple Street",
            source="incident_report",
            confidence=0.95,
            linked_people=[],
            linked_evidence=["EV-002"],
        ),
    ]

    return case
