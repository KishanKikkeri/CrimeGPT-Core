"""
Shared fixtures for intelligence tests.

`burglary_result` runs the full Stage 2-8 pipeline (Stage 1 already
done by the case_factory) on the flagship burglary case and caches
the result for the duration of the test session.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.graph.builder import build_investigation_graph
from app.graph.state import initial_state
from app.models.case import Case


DATA_DIR = Path(__file__).parent.parent.parent / "data" / "burglary"


@pytest.fixture(scope="session")
def burglary_case() -> Case:
    from data.burglary.case_factory import build_burglary_case
    return build_burglary_case()


@pytest.fixture(scope="session")
def burglary_result(burglary_case) -> dict:
    """
    Runs Stages 2-8 on the pre-structured burglary case.
    Stage 1 (Case Builder) is already done by the case_factory —
    we enter at Stage 2 (Timeline Builder) via build_analysis_graph().
    """
    from app.graph.builder import build_analysis_graph
    from app.models.enums import WorkflowStage

    # Mark Stage 1 as complete so completed_stages reflects reality
    burglary_case.mark_stage_complete(WorkflowStage.CASE_BUILDER)
    burglary_case.current_stage = WorkflowStage.TIMELINE_BUILDER

    state = initial_state(burglary_case)
    graph = build_analysis_graph(start_from=WorkflowStage.TIMELINE_BUILDER)
    return graph.invoke(state)


@pytest.fixture(scope="session")
def final_case(burglary_result) -> Case:
    return burglary_result["case"]


@pytest.fixture(scope="session")
def expected_gaps() -> dict:
    return json.loads((DATA_DIR / "expected_gaps.json").read_text())


@pytest.fixture(scope="session")
def expected_timeline() -> dict:
    return json.loads((DATA_DIR / "expected_timeline.json").read_text())
