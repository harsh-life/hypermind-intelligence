"""Track A policy layer: Policy Engine + Scope Gate + authorization.

Context 3 scope (see the Context-3 task brief and
docs/02_COMPONENT_SPECS.md §6-7, docs/13_OPEN_DECISIONS.md OD-18/OD-23):
the deterministic "POLICY / SCOPE DECIDES" layer of

    MODEL PROPOSES -> POLICY / SCOPE DECIDES -> TOOL EXECUTES -> EVIDENCE -> HUMAN VALIDATES

Two components, matching docs/02's own separation:

    PolicyEngine (trackA.policy.engine)
        Generic, deterministic `evaluate(policy_id, input_document) ->
        PolicyDecision`, fail-closed on any error or unregistered policy.

    ScopeGate (trackA.policy.scope_gate)
        The request-level authorization gate every network-capable
        request must pass through (OD-18), plus the docs/02 §7 Stage-0
        `check_scope` interface. Built on top of PolicyEngine with one
        concrete registered policy ("scope").

Out of scope for this context (see the Context-3 task brief §11): actual
network/Docker/tool execution, the Orchestrator's other checks (registry
lookups, resource accounting), the Human Verification workflow, the
Judge, model evaluation, Track B, Darwin, any network-layer proxy or
firewall. `RunScope` (the object this layer authorizes requests against)
lives in `trackA.schemas.scope`, not here — this package only decides,
it does not define the scope data model.
"""
from __future__ import annotations

from trackA.policy.engine import PolicyDecision, PolicyEngine, UnknownPolicyError
from trackA.policy.requests import NetworkOperationRequest, NormalizationError, from_orchestrator_action
from trackA.policy.scope_gate import (
    POLICY_VERSION,
    SCOPE_POLICY_ID,
    ScopeDenialReason,
    ScopeGate,
    ScopeGateDecision,
    build_policy_engine,
    decide_scope,
)

__all__ = [
    "PolicyDecision",
    "PolicyEngine",
    "UnknownPolicyError",
    "NetworkOperationRequest",
    "NormalizationError",
    "from_orchestrator_action",
    "ScopeGate",
    "ScopeGateDecision",
    "ScopeDenialReason",
    "decide_scope",
    "build_policy_engine",
    "SCOPE_POLICY_ID",
    "POLICY_VERSION",
]
