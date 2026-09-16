"""Outcome types the Orchestrator returns from one run's actions.

None of these correspond to a docs/03 schema by name — they are explicit,
inspectable compositions of already-documented pipeline records (task
brief §4: "a tool invocation should be represented explicitly and should
preserve..."), built the same way `trackA.schemas.scope.ScopeAuthorization`
and `trackA.models.runtime.ModelBinding` already compose existing types
into a convenience object rather than inventing new pipeline schemas for
what is really just "here are the several already-schema'd records one
action produced, held together." Kept out of `trackA.schemas` for the same
reason those two are: they are execution/orchestration-layer bookkeeping,
not something any other pipeline stage consumes by contract.

Every `*ActionOutcome` follows the same exactly-one-of shape as
`trackA.schemas.common.Provenance`'s model_id/tool_id rule: exactly one of
`authorized`/`rejected` is set, mirroring the Orchestrator's own
`AuthorizedAction | OrchestratorRejection` return type
(trackA.schemas.execution) at the composition layer.
"""
from __future__ import annotations

from typing import Optional

from pydantic import model_validator

from trackA.policy.scope_gate import ScopeGateDecision
from trackA.execution.tools import ToolInvocationRecord
from trackA.schemas.audit import FailureEvent
from trackA.schemas.base import HypermindModel
from trackA.schemas.execution import AuthorizedAction, OrchestratorRejection
from trackA.schemas.judge import JudgeInput, JudgeRoutingDecision
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.skills import SpecialistPoCOutput
from trackA.schemas.workers import WorkerOutput


class _AuthorizationOutcomeMixin(HypermindModel):
    authorized: Optional[AuthorizedAction] = None
    rejected: Optional[OrchestratorRejection] = None

    @model_validator(mode="after")
    def _exactly_one_authorization(self):
        if bool(self.authorized) == bool(self.rejected):
            raise ValueError(
                f"{type(self).__name__}: exactly one of authorized/rejected must be set"
            )
        return self

    @property
    def was_authorized(self) -> bool:
        return self.authorized is not None


class ToolActionOutcome(_AuthorizationOutcomeMixin):
    """One `tool_execution`-type `OrchestratorAction`'s full, explicit
    record (task brief §4): the proposal, the authorization decision, the
    Scope Gate decision that fed it (present whenever scope evaluation
    ran — i.e. whenever authorization was attempted at all, allow or
    deny), and — only when authorized *and* the Tool Registry itself
    didn't reject it — the resulting invocation.
    """

    action: OrchestratorAction
    scope_decision: Optional[ScopeGateDecision] = None
    invocation: Optional[ToolInvocationRecord] = None
    failure: Optional[FailureEvent] = None


class WorkerActionOutcome(_AuthorizationOutcomeMixin):
    """One `worker_invocation`-type `OrchestratorAction`'s full record."""

    action: OrchestratorAction
    output: Optional[WorkerOutput] = None
    failure: Optional[FailureEvent] = None
    retries_used: int = 0


class SpecialistActionOutcome(_AuthorizationOutcomeMixin):
    """One `specialist_investigation`-type `OrchestratorAction`'s full
    record. `output`, when present, is a `SpecialistPoCOutput` —
    `trust_classification` is structurally pinned to `CANDIDATE_FINDING`
    by that schema itself (trackA/schemas/skills.py); nothing in this
    module, or anywhere else in Context 5, ever promotes it further (task
    brief §19 [LOCKED]: "Context 5 must NOT automatically promote
    evidence to VALIDATED_FINDING").
    """

    action: OrchestratorAction
    output: Optional[SpecialistPoCOutput] = None
    failure: Optional[FailureEvent] = None
    retries_used: int = 0


class JudgeActionOutcome(HypermindModel):
    """The Judge is never something a model *proposes* — no
    `OrchestratorAction.proposed_action_type` value exists for it
    (trackA/schemas/orchestrator.py's closed
    `tool_execution | worker_invocation | specialist_investigation`
    literal has no fourth option), matching docs/02_COMPONENT_SPECS.md
    §15: the Judge is invoked once "whatever assembles Worker outputs"
    (here, `trackA.orchestrator.run.RunContext.run_judge`) decides enough
    evidence exists — a deterministic Orchestrator decision, not a
    model-proposed, Scope-Gate-or-registry-checked action. Consequently
    this outcome carries no `action`/`authorized`/`rejected` fields at
    all: there is nothing to authorize a request *against* (no tool, no
    target, no registry lookup), which is itself part of how this module
    keeps the Judge path structurally distinct from — and never routed
    through — the Skill-Registry-reaching Specialist path.
    """

    judge_input: JudgeInput
    decision: Optional[JudgeRoutingDecision] = None
    failure: Optional[FailureEvent] = None
    retries_used: int = 0
