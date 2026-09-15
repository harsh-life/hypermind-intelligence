"""Policy Engine. docs/02_COMPONENT_SPECS.md §6 ("Policy Engine (OPA/Rego)"),
docs/09_SECURITY_POLICIES_README.md §1 (the Rego policy shape this
mirrors), docs/13_OPEN_DECISIONS.md OD-18.

docs/02 §6 describes a policy engine serving *both* the Scope Gate and
the Orchestrator's own policy-check step (P5) "through the same
evaluation interface — one engine, two call sites, not two engines." The
Orchestrator's other checks (registry lookups, resource accounting) are
explicitly out of scope for Context 3 ("Do not implement orchestration
engine"), so only one policy is actually registered here (the "scope"
policy, trackA.policy.scope_gate) — but the generic, dict-in/dict-out
`evaluate(policy_id, input_document)` interface is real and built exactly
as documented, so a later Orchestrator context can register additional
policies against this same engine without redesigning it.

This is a deterministic, in-process stand-in for OPA/Rego, not a real OPA
integration (no OPA binary/service is available or required for Context
3's scope; docs/09 §1 explicitly frames its Rego text as "illustrative
structure, not final code"). The three [LOCKED] properties from docs/09
§1 apply to every registered policy via this engine's own error handling,
not per-policy: fail-closed on error, and no policy contributes anything
beyond deny on a raised exception."""
from __future__ import annotations

from typing import Callable, Dict, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel

PolicyFunction = Callable[[dict], "PolicyDecision"]


class PolicyDecision(HypermindModel):
    """docs/02 §6's `PolicyDecision(allow | deny, reason)`, widened with
    an optional machine-readable `reason_code` (task requirement:
    "preserve a machine-readable denial reason" — docs/02 §6 names only a
    free-text `reason`, this is a compatible addition, not a redefinition).
    """

    policy_id: str
    decision: Literal["allow", "deny"]
    reason: str
    reason_code: Optional[str] = None

    @model_validator(mode="after")
    def _reason_code_only_on_deny(self) -> "PolicyDecision":
        if self.decision == "allow" and self.reason_code is not None:
            raise ValueError("PolicyDecision.reason_code must be unset when decision='allow'")
        if self.decision == "deny" and self.reason_code is None:
            raise ValueError("PolicyDecision.reason_code is required when decision='deny'")
        return self


class UnknownPolicyError(ValueError):
    """Raised by PolicyEngine.evaluate for an unregistered policy_id."""


class PolicyEngine:
    """docs/02 §6: `evaluate(policy_id: str, input_document: dict) -> PolicyDecision`.

    [LOCKED, docs/09 §2 Policy Engine failure handling]: "Evaluation
    error/timeout -> fail closed (deny) — never fail open." Enforced here
    unconditionally: any exception raised by a registered policy function
    is caught and converted into a `deny` PolicyDecision, never allowed to
    propagate as an unhandled exception that a caller might mistake for
    "no decision made, proceed." An unregistered `policy_id` is likewise
    fail-closed, not merely an error a caller could ignore.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, PolicyFunction] = {}

    def register_policy(self, policy_id: str, fn: PolicyFunction) -> None:
        self._policies[policy_id] = fn

    def evaluate(self, policy_id: str, input_document: dict) -> PolicyDecision:
        fn = self._policies.get(policy_id)
        if fn is None:
            return PolicyDecision(
                policy_id=policy_id,
                decision="deny",
                reason=f"no policy registered for policy_id={policy_id!r}; fail closed",
                reason_code="unknown_policy",
            )
        try:
            decision = fn(input_document)
        except Exception as exc:  # noqa: BLE001 - fail-closed is intentional and total
            return PolicyDecision(
                policy_id=policy_id,
                decision="deny",
                reason=f"policy {policy_id!r} raised during evaluation ({exc!r}); fail closed",
                reason_code="policy_evaluation_error",
            )
        if decision.policy_id != policy_id:
            return PolicyDecision(
                policy_id=policy_id,
                decision="deny",
                reason=(
                    f"policy {policy_id!r} returned a PolicyDecision for a "
                    f"different policy_id ({decision.policy_id!r}); fail closed"
                ),
                reason_code="policy_id_mismatch",
            )
        return decision
