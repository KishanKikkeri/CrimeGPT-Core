"""
AgentExecutor - runs one pipeline stage end-to-end:

    Run Agent -> Validate Output -> Apply via MutationEngine
    -> Record AgentExecution + AgentRunLog

This is the "Agent Runtime" piece of the Investigation Engine. Each
LangGraph node (app/graph/builder.py) is a thin wrapper that calls
`AgentExecutor.run(...)` and folds the `StageResult` into GraphState.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from pydantic import BaseModel, ConfigDict

from app.contracts import REGISTRY
from app.contracts.base import AgentExecution, AgentOutput, AgentRunLog
from app.models.case import Case
from app.models.enums import WorkflowStage
from app.runtime.engine import MutationEngine
from app.runtime.mutation import CaseMutation

# An agent function takes the current (read-only) case and any raw
# input for this run, and returns a validated AgentOutput. It must
# NOT mutate `case` directly.
AgentFn = Callable[[Case, Optional[str]], AgentOutput]


class StageResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    case: Case
    mutations: list[CaseMutation] = []
    execution: AgentExecution
    run_log: AgentRunLog
    output: Optional[AgentOutput] = None


class AgentExecutor:
    """
    `model_name` is recorded on every AgentExecution for cost/perf
    tracking. Rule-based stages (health scoring) should pass something
    like "rule-based" instead of a model name.
    """

    def __init__(self, model_name: str = "unspecified"):
        self.model_name = model_name

    def run(
        self,
        case: Case,
        stage: WorkflowStage,
        agent_fn: AgentFn,
        raw_input: Optional[str] = None,
    ) -> StageResult:
        contract = REGISTRY[stage]
        started_at = datetime.utcnow()

        try:
            output = agent_fn(case, raw_input)
            case, mutations = MutationEngine.apply(case, output, contract)
            finished_at = datetime.utcnow()

            execution = AgentExecution.from_timing(
                agent_name=contract.agent_name,
                case_id=case.case_id,
                started_at=started_at,
                finished_at=finished_at,
                confidence=output.confidence,
                success=True,
                model=self.model_name,
            )
            run_log = AgentRunLog(
                agent=contract.agent_name,
                stage=stage,
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                notes="; ".join(output.warnings) if output.warnings else None,
            )

            return StageResult(
                case=case,
                mutations=mutations,
                execution=execution,
                run_log=run_log,
                output=output,
            )

        except Exception as exc:  # noqa: BLE001 - we want to record any failure
            finished_at = datetime.utcnow()

            execution = AgentExecution.from_timing(
                agent_name=contract.agent_name,
                case_id=case.case_id,
                started_at=started_at,
                finished_at=finished_at,
                confidence=0.0,
                success=False,
                model=self.model_name,
                error=str(exc),
            )
            run_log = AgentRunLog(
                agent=contract.agent_name,
                stage=stage,
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                notes=str(exc),
            )

            return StageResult(
                case=case,
                mutations=[],
                execution=execution,
                run_log=run_log,
                output=None,
            )
