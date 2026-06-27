"""
Stage 7 agent function - Health Scoring.

Thin wrapper - all the actual logic lives in `app.scoring` /
`app.contracts.health`. Kept as a function here purely so the graph
builder can treat every stage uniformly (AgentFn signature).
"""

from __future__ import annotations

from typing import Optional

from app.contracts.health import HealthScoringOutput
from app.models.case import Case


def run(case: Case, raw_input: Optional[str]) -> HealthScoringOutput:
    return HealthScoringOutput.compute(case)
