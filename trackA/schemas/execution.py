"""Orchestrator authorization-outcome schemas. Context 5 (runtime/tools/
orchestration) addition.

Genuine schema gap, reported per the Context-5 task brief §28's escalation
path: docs/02_COMPONENT_SPECS.md §11 (Orchestrator/Planner) documents the
Orchestrator's own interface as

    propose_and_authorize(context: dict) -> AuthorizedAction | OrchestratorRejection

and its Observability row requires "every proposal logged with full
check-by-check outcome (which of the five checks passed/failed)" — but
neither `AuthorizedAction` nor `OrchestratorRejection` is ever defined as a
schema anywhere in docs/03_DATA_SCHEMAS_README.md (its Schema Index lists
`OrchestratorAction`, the model-*proposed* record, and stops there; the
Orchestrator's own deterministic authorize/reject outcome has no
documented shape). docs/13_OPEN_DECISIONS.md does not carry an open
decision for this gap either. This is exactly the same class of gap
already resolved twice in this codebase's history for other manifest/
schema fields (OD-19's `ToolManifest.expected_output`, OD-09's
`ScreenResult`): an interface docs/02 names explicitly but docs/03 never
formalised. Context 5 owns it, because Context 5 is what builds the
Orchestrator these two types belong to. Smallest compatible addition:
two new, purely additive schemas, reusing existing common types
(`Provenance`, `CheckResult`) rather than inventing new ones.

Design choices:

    Both types embed `Provenance` with neither `model_id` nor `tool_id`
    set. The Orchestrator's authorize/reject decision is itself
    deterministic (docs/02 §11: "The Orchestrator is primarily
    deterministic. An LLM may propose the next action. The Orchestrator
    validates ... before executing it.") — the same convention already
    used for `EvidenceGateResult` (trackA/schemas/gates.py): a
    deterministic gate's own provenance names neither a model nor a tool.

    `checks_performed: List[CheckResult]` reuses the existing
    `CheckResult` shape from trackA/schemas/gates.py (`{check_name,
    passed}`) rather than inventing a parallel structure — docs/02 §11's
    "full check-by-check outcome" requirement is structurally identical
    to what `EvidenceGateResult.checks_performed` already models for a
    different gate, and reusing it keeps exactly one "named check result"
    shape in the schema layer.

    `OrchestratorRejection.reason_code` is a free `str`, not a shared enum
    with `trackA.policy.scope_gate.ScopeDenialReason`: a rejection can
    originate from several distinct check failures (schema, scope,
    registry, resource), only one of which is scope-specific. Forcing a
    single enum across all of them would either import a policy-layer
    type into the schema layer (a layering violation — trackA.policy
    already imports trackA.schemas, never the reverse) or require
    duplicating ScopeDenialReason's values here for no benefit. Reason
    codes such as scope denials still flow through unmodified as their
    own string value (e.g. "domain_not_allowed") for machine-readability;
    this field just does not force a closed type.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.gates import CheckResult

ActionType = Literal["tool_execution", "worker_invocation", "specialist_investigation"]


class AuthorizedAction(HypermindModel):
    """docs/02_COMPONENT_SPECS.md §11's `AuthorizedAction` — the
    Orchestrator's own record that a proposed `OrchestratorAction` cleared
    every check in the authorization chain. Handed to the relevant
    executor (Docker Tool Execution Engine / Worker Execution Framework /
    Specialist Executor); never executed by the Orchestrator itself
    (docs/02 §11: "Never execute a proposal itself — authorization is
    handed to the relevant execution component" [LOCKED]).
    """

    provenance: Provenance
    source_action_id: str
    action_type: ActionType
    target_registry_id: str
    authorized_parameters: Dict[str, Any]
    checks_performed: List[CheckResult]

    @model_validator(mode="after")
    def _validate(self) -> "AuthorizedAction":
        if self.provenance.stage != PipelineStage.ORCHESTRATOR:
            raise ValueError("AuthorizedAction.provenance.stage must be 'orchestrator'")
        if self.provenance.model_id or self.provenance.tool_id:
            raise ValueError(
                "AuthorizedAction.provenance must set neither model_id nor "
                "tool_id — the Orchestrator's authorization decision is "
                "deterministic (docs/02 §11)"
            )
        if not self.source_action_id:
            raise ValueError("AuthorizedAction.source_action_id must be non-empty")
        if any(not c.passed for c in self.checks_performed):
            raise ValueError(
                "AuthorizedAction.checks_performed must all be passed=True — "
                "any failing check belongs on an OrchestratorRejection instead"
            )
        return self


class OrchestratorRejection(HypermindModel):
    """docs/02_COMPONENT_SPECS.md §11's `OrchestratorRejection` — emitted
    for any failing check, "no execution" (docs/02 §11 [LOCKED]: "Any
    check fails -> reject + audit event, no execution").
    """

    provenance: Provenance
    source_action_id: str
    checks_performed: List[CheckResult]
    reason: str
    reason_code: str

    @model_validator(mode="after")
    def _validate(self) -> "OrchestratorRejection":
        if self.provenance.stage != PipelineStage.ORCHESTRATOR:
            raise ValueError("OrchestratorRejection.provenance.stage must be 'orchestrator'")
        if self.provenance.model_id or self.provenance.tool_id:
            raise ValueError(
                "OrchestratorRejection.provenance must set neither model_id "
                "nor tool_id (docs/02 §11 — deterministic decision)"
            )
        if not self.source_action_id:
            raise ValueError("OrchestratorRejection.source_action_id must be non-empty")
        if not self.reason or not self.reason_code:
            raise ValueError(
                "OrchestratorRejection.reason and reason_code are both required"
            )
        if not any(not c.passed for c in self.checks_performed):
            raise ValueError(
                "OrchestratorRejection.checks_performed must contain at least "
                "one failing check — a rejection with no failing check is not "
                "a rejection"
            )
        return self
