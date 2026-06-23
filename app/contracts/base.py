"""
Shared base classes for the Agent Contract Layer.

Every agent in the pipeline:

1. Receives the current `Case` (read-only - it should not mutate it
   directly).
2. Returns an `AgentOutput` subclass instance - a structured,
   schema-validated result. Never raw prose, never a free-form dict.
3. That output's `.apply(case)` method is the *only* sanctioned way
   the Case Object gets mutated. This keeps "how does an agent update
   the Case Object?" answerable in one place per agent.

This file also defines `AgentExecution` - the runtime metadata record
(duration, token usage, model, success) that powers the audit trail /
"How did your system arrive at this?" explainability view.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, Field

from app.models.case import Case
from app.models.enums import WorkflowStage


class AgentRunLog(BaseModel):
    """
    One audit-trail entry, appended to GraphState.agent_logs.

    Lightweight per-stage record shown directly in the UI (the
    "AI is currently working on..." / "✓ Building Case" progress
    list). Distinct from `AgentExecution`, which carries
    perf/cost metadata for ops/debugging.

    Lives here (not in app.graph.state) so that app.runtime.executor
    and app.graph.state can both import it without a circular
    dependency between the runtime and graph packages.
    """

    agent: str
    stage: WorkflowStage
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: Literal["success", "error", "skipped"] = "success"
    notes: Optional[str] = None


class AgentOutput(BaseModel):
    """
    Base class for every agent's structured output.

    Subclasses must:
      - set `agent_name` and `stage` as ClassVars
      - implement `apply(case)`, mutating only the fields listed in
        their contract's `WRITES` tuple, then returning the case
      - declare `confidence` (overall confidence for this run) and
        `warnings` (non-fatal issues worth surfacing in the UI)
    """

    agent_name: ClassVar[str]
    stage: ClassVar[WorkflowStage]

    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)

    def apply(self, case: Case) -> Case:  # pragma: no cover - overridden
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply(case)"
        )

    def mark_complete(self, case: Case, next_stage: Optional[WorkflowStage] = None) -> None:
        """Helper for subclasses: record stage completion + advance pointer."""
        case.mark_stage_complete(self.stage)
        if next_stage is not None:
            case.current_stage = next_stage


class AgentExecution(BaseModel):
    """
    Runtime metadata for a single agent run. Distinct from
    `AgentRunLog` (app.graph.state) in that this captures *performance
    and cost* data (tokens, duration, model) for ops/debugging,
    while AgentRunLog is the lightweight per-stage audit entry that
    flows through graph state and is shown in the UI.

    A typical flow: the agent wrapper times the call, builds an
    AgentExecution, persists it (e.g. to a `agent_executions` table),
    and also appends a corresponding AgentRunLog to graph state.
    """

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    agent_name: str
    case_id: str

    started_at: datetime
    finished_at: datetime

    duration_ms: int

    confidence: float = Field(ge=0.0, le=1.0)
    success: bool

    tokens_used: Optional[int] = None
    model: str

    error: Optional[str] = None

    @classmethod
    def from_timing(
        cls,
        *,
        agent_name: str,
        case_id: str,
        started_at: datetime,
        finished_at: datetime,
        confidence: float,
        success: bool,
        model: str,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None,
    ) -> "AgentExecution":
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        return cls(
            agent_name=agent_name,
            case_id=case_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            confidence=confidence,
            success=success,
            tokens_used=tokens_used,
            model=model,
            error=error,
        )


class AgentContract(BaseModel):
    """
    Declarative description of an agent's read/write surface,
    used for documentation, validation, and to auto-generate the
    "Agent Contracts" table.
    """

    agent_name: str
    stage: WorkflowStage
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    output_model: type[AgentOutput]
    description: str
