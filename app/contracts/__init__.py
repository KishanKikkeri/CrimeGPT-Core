"""
Agent Contract Layer - registry and helpers.

This is the answer to "How does an agent update the Case Object?":

    output = SomeAgentOutput(...)        # validated structured result
    case = output.apply(case)            # the ONLY sanctioned mutation path

And the answer to "How do we know an agent didn't overstep its
contract?":

    before = case.model_dump()
    case = output.apply(case)
    after = case.model_dump()
    changed = diff_top_level_fields(before, after)
    assert set(changed) <= set(CONTRACT.writes)
"""

from __future__ import annotations

from app.contracts.base import AgentContract, AgentExecution, AgentOutput, AgentRunLog
from app.contracts import (
    case_builder,
    compliance,
    evidence,
    gap_enhancement,
    gaps,
    health,
    legal,
    report,
    timeline,
)
from app.models.enums import WorkflowStage

# Ordered list = the pipeline order = the LangGraph edge order.
ORDERED_CONTRACTS: list[AgentContract] = [
    case_builder.CONTRACT,
    timeline.CONTRACT,
    evidence.CONTRACT,
    gaps.CONTRACT,
    gap_enhancement.CONTRACT,
    legal.CONTRACT,
    compliance.CONTRACT,
    health.CONTRACT,
    report.CONTRACT,
]

REGISTRY: dict[WorkflowStage, AgentContract] = {c.stage: c for c in ORDERED_CONTRACTS}


def diff_top_level_fields(before: dict, after: dict) -> list[str]:
    """
    Returns the names of top-level Case fields that differ between
    two `case.model_dump()` snapshots. Used to verify an agent only
    touched the fields declared in its contract's `writes`.
    """
    changed: list[str] = []
    for key in after:
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def validate_contract_compliance(
    contract: AgentContract, before: dict, after: dict
) -> list[str]:
    """
    Returns a list of field names the agent wrote to that were NOT
    declared in its contract. Empty list = compliant. A `writes`
    value of ("*",) (e.g. health scoring, report generation) means
    "whole-case write access" and always passes.
    """
    if contract.writes == ("*",):
        return []

    changed = set(diff_top_level_fields(before, after))
    # updated_at / current_stage / completed_stages change on every
    # apply() via touch()/mark_complete() - always allowed.
    changed -= {"updated_at", "current_stage", "completed_stages"}

    allowed = set(contract.writes)
    return sorted(changed - allowed)


def contracts_table_markdown() -> str:
    """Auto-generates the Agent Contracts markdown table for the README."""
    lines = [
        "| Stage | Agent | Reads | Writes |",
        "|---|---|---|---|",
    ]
    for i, c in enumerate(ORDERED_CONTRACTS, start=1):
        reads = ", ".join(c.reads)
        writes = ", ".join(c.writes)
        lines.append(f"| {i}. {c.description.split('.')[0]} | `{c.agent_name}` | {reads} | {writes} |")
    return "\n".join(lines)


__all__ = [
    "AgentContract",
    "AgentExecution",
    "AgentOutput",
    "AgentRunLog",
    "ORDERED_CONTRACTS",
    "REGISTRY",
    "diff_top_level_fields",
    "validate_contract_compliance",
    "contracts_table_markdown",
    "case_builder",
    "timeline",
    "evidence",
    "gaps",
    "legal",
    "compliance",
    "health",
    "report",
]
