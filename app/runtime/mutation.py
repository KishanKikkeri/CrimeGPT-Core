"""
CaseMutation - the recorded unit of change to a Case.

Design note (pragmatic adaptation of the "agents never modify the
case directly" principle):

The CTO brief suggests agents *return* mutations instead of calling
`apply()`. We keep `AgentOutput.apply(case)` as-is (it's already
schema-validated and contract-checked - rewriting all 8 contracts to
emit field-level mutation primitives would be a large rewrite for
limited extra safety this week).

Instead, `MutationEngine` wraps `apply()`: it snapshots the Case
before and after, and turns every *changed top-level field* into a
`CaseMutation` record automatically. This gives us the properties the
brief actually cares about:

  - Every change is auditable (mutation log, per field, per agent)
  - Rollback is possible (`MutationEngine.rollback`, restores `before`)
  - Human review is possible (a mutation can be marked
    approved/rejected; rejection -> rollback)

...without requiring every agent to hand-construct mutation primitives.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import WorkflowStage


class CaseMutation(BaseModel):
    mutation_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    case_id: str

    field: str
    operation: Literal["replace"] = "replace"

    before: Any
    after: Any

    source_agent: str
    stage: WorkflowStage

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Free-text reason, e.g. "Event extracted from witness statement".
    reason: Optional[str] = None

    # Human review (Stage 9 - continuous updates / approval workflow).
    review_status: Literal["unreviewed", "approved", "rejected"] = "unreviewed"
