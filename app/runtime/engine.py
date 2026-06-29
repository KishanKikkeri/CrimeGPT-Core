"""
MutationEngine - the single place the Case actually changes.

    case, mutations = MutationEngine.apply(case, output, contract)

    # later, e.g. after human review rejects a finding:
    case = MutationEngine.rollback(case, mutation)
"""

from __future__ import annotations

from app.contracts.base import AgentContract, AgentOutput
from app.contracts import diff_top_level_fields, validate_contract_compliance
from app.models.case import Case
from app.runtime.mutation import CaseMutation

# Fields that change on essentially every apply() via touch() /
# mark_stage_complete() - bookkeeping, not "findings", so we don't
# create a CaseMutation record for them (keeps the mutation log
# focused on substantive changes).
_BOOKKEEPING_FIELDS = {"updated_at", "current_stage", "completed_stages"}


class MutationEngine:
    """Stateless - all methods are classmethods operating on a Case."""

    @classmethod
    def apply(
        cls, case: Case, output: AgentOutput, contract: AgentContract
    ) -> tuple[Case, list[CaseMutation]]:
        """
        Apply `output` to `case` via its `apply()` method, and derive
        a CaseMutation for every substantive top-level field that
        changed. Also appends a warning to `output.warnings` if the
        agent wrote outside its declared contract (it does NOT block
        the write - that's a calibration signal for the team, not a
        runtime failure).
        """
        before = case.model_dump(mode="json")
        case = output.apply(case)
        after = case.model_dump(mode="json")

        violations = validate_contract_compliance(contract, before, after)
        if violations:
            output.warnings.append(
                f"{output.agent_name} wrote to undeclared field(s): {violations}"
            )

        changed = [f for f in diff_top_level_fields(before, after) if f not in _BOOKKEEPING_FIELDS]

        mutations = [
            CaseMutation(
                case_id=case.case_id,
                field=field,
                before=before.get(field),
                after=after.get(field),
                source_agent=output.agent_name,
                stage=output.stage,
                reason=f"{output.agent_name} updated '{field}'",
            )
            for field in changed
        ]

        return case, mutations

    @classmethod
    def rollback(cls, case: Case, mutation: CaseMutation) -> Case:
        """
        Restore `mutation.field` to its pre-mutation value. Pydantic's
        `validate_assignment=True` on Case re-validates/coerces the
        raw dict/list back into the proper model types.
        """
        if mutation.case_id != case.case_id:
            raise ValueError(
                f"Mutation {mutation.mutation_id} belongs to case "
                f"{mutation.case_id}, not {case.case_id}"
            )

        setattr(case, mutation.field, mutation.before)
        mutation.review_status = "rejected"
        case.touch()
        return case

    @classmethod
    def approve(cls, mutation: CaseMutation) -> CaseMutation:
        mutation.review_status = "approved"
        return mutation
