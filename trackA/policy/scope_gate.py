"""Scope Gate. docs/02_COMPONENT_SPECS.md §7, docs/09_SECURITY_POLICIES_
README.md §1, docs/13_OPEN_DECISIONS.md OD-18 (authoritative decision)
and OD-23 (RunScope source-flexibility).

OD-18's authoritative text (docs/13): "Every network-capable tool request
initiated by a model/worker must pass through the Scope Gate before the
request is executed... A tool request is authorized only when the
requested operation/target is within the established RunScope... This
preserves the governing spine unchanged: MODEL PROPOSES -> POLICY/SCOPE
DECIDES -> TOOL EXECUTES."

`ScopeGate` implements exactly that decision boundary and nothing past
it:

    MODEL REQUESTS CAPABILITY  (OrchestratorAction, out of Context 3's
                                 authorship — already exists)
            |
            v
    SCOPE / POLICY EVALUATION  (THIS MODULE)
            |
            v
    AUTHORIZED REQUEST          (ScopeGateDecision(decision="allow"))
            |
            v
    LATER TOOL EXECUTION LAYER  (Docker Tool Execution Engine — NOT built
                                  here; docs/02 §12, explicitly out of
                                  scope for Context 3)

[REQ, per task brief §7] This is REQUEST-LEVEL authorization only. It
does not, and is explicitly not claimed to, guarantee that an already-
authorized tool's own subsequent internal network traffic stays within
scope once the tool is running — that is a network-layer enforcement
question docs/13 OD-18 explicitly declined to make an MVP requirement
("Do not claim a proxy has been adopted — none has... Do not add any
technical enforcement mechanism beyond the Scope Gate check that hasn't
been explicitly selected"). Nothing in this module builds, simulates, or
assumes a network proxy or firewall.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import model_validator

from trackA.policy.engine import PolicyDecision, PolicyEngine
from trackA.policy.requests import NetworkOperationRequest, NormalizationError, from_orchestrator_action
from trackA.schemas.base import HypermindModel
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.scope import RunScope, domain_matches, normalize_hostname

SCOPE_POLICY_ID = "scope"
POLICY_VERSION = "trackA-scope-policy-v1"


class ScopeDenialReason(str, Enum):
    """Machine-readable reason a request was denied. Every DENY carries
    exactly one of these (PolicyDecision.reason_code); ALLOW carries
    none. Distinguishing these (rather than a single generic "denied")
    is what the task brief's "machine-readable denial reason" and
    "at minimum distinguish allowed / denied / ambiguous-insufficient"
    requirements resolve to concretely: `NO_TARGET_SPECIFIED` and
    `MALFORMED_REQUEST` are this module's two "ambiguous / insufficiently
    specified" cases (see module-level design note below); every other
    value is an unambiguous, specific denial.
    """

    MISSING_RUN_SCOPE = "missing_run_scope"
    RUN_SCOPE_NOT_ESTABLISHED = "run_scope_not_established"
    MISSING_AUTHORIZATION_CONTEXT = "missing_authorization_context"
    MALFORMED_REQUEST = "malformed_request"
    NO_TARGET_SPECIFIED = "no_target_specified"
    PROHIBITED_OPERATION = "prohibited_operation"
    DOMAIN_EXCLUDED = "domain_excluded"
    IP_EXCLUDED = "ip_excluded"
    DOMAIN_NOT_ALLOWED = "domain_not_allowed"
    IP_NOT_ALLOWED = "ip_not_allowed"
    PORT_NOT_ALLOWED = "port_not_allowed"
    PROTOCOL_NOT_ALLOWED = "protocol_not_allowed"


class ScopeGateDecision(HypermindModel):
    """The Scope Gate's own typed decision, carrying the run/request
    context a bare `PolicyDecision` does not (PolicyEngine.evaluate's
    dict-in/dict-out interface is deliberately generic — see
    trackA/policy/engine.py's module docstring — this is the ergonomic,
    audit-friendly wrapper `ScopeGate` actually returns to callers).
    """

    run_id: str
    decision: Literal["allow", "deny"]
    reason: str
    reason_code: Optional[ScopeDenialReason] = None
    policy_version: str = POLICY_VERSION
    evaluated_request: Optional[NetworkOperationRequest] = None

    @model_validator(mode="after")
    def _reason_code_only_on_deny(self) -> "ScopeGateDecision":
        if self.decision == "allow" and self.reason_code is not None:
            raise ValueError("ScopeGateDecision.reason_code must be unset when decision='allow'")
        if self.decision == "deny" and self.reason_code is None:
            raise ValueError("ScopeGateDecision.reason_code is required when decision='deny'")
        return self

    @property
    def is_allowed(self) -> bool:
        return self.decision == "allow"


def _deny(
    run_id: str,
    reason: str,
    reason_code: ScopeDenialReason,
    *,
    request: Optional[NetworkOperationRequest] = None,
) -> ScopeGateDecision:
    return ScopeGateDecision(
        run_id=run_id,
        decision="deny",
        reason=reason,
        reason_code=reason_code,
        evaluated_request=request,
    )


def _allow(run_id: str, reason: str, *, request: NetworkOperationRequest) -> ScopeGateDecision:
    return ScopeGateDecision(
        run_id=run_id,
        decision="allow",
        reason=reason,
        reason_code=None,
        evaluated_request=request,
    )


def decide_scope(
    request: NetworkOperationRequest, run_scope: Optional[RunScope]
) -> ScopeGateDecision:
    """The core, deterministic decision chain. Pure function of
    (request, run_scope) — same inputs always produce the same decision
    (task brief §6: "deterministic for the same normalized request +
    RunScope + policy inputs"), and every branch is fail-closed: nothing
    below reaches ALLOW except the final line, and every early return is
    a DENY.

    Design notes on the "narrowest safe behavior" choices this chain
    encodes (task brief §9, where the canonical docs are silent on the
    exact edge-case rule):

    1. `run_scope is None` or not `run_scope.is_established` denies
       before anything else is inspected — an unestablished/candidate
       RunScope (docs/13 OD-23: "A parser/model may extract and normalize
       scope information into a structured candidate RunScope, but it
       does not itself grant authorization") must never be able to
       authorize any request, full stop.

    2. Prohibited-operation-class is checked before target matching, and
       independently of it: "an explicitly prohibited operation must
       remain prohibited even if the target itself is in scope" (task
       brief §9) — this is an absolute veto, not one factor among others.

    3. Exclusions are checked before inclusions for both domain and IP
       (docs/09 §1 [LOCKED]: "explicit exclusions win over inclusions").

    4. If a request supplies BOTH a hostname and an IP, EACH is
       independently required to pass its own inclusion/exclusion check
       (logical AND, not OR). This is the conservative reading: allowing
       either alone to suffice would let a request smuggle an
       out-of-scope hostname riding alongside an in-scope IP (or vice
       versa) — exactly the "target mutation between proposed request
       and authorization representation" class of attack the task brief
       names explicitly.

    5. `allowed_ports`/`allowed_protocols` being empty is treated as "not
       restricted" (see `RunScope`'s own docstring for the full
       rationale) — this is the one place this chain is permissive by
       default, and it is scoped narrowly to two refinement dimensions,
       never to target identity (domain/IP), which always requires a
       positive match.
    """

    run_id = request.run_id

    if run_scope is None:
        return _deny(
            run_id,
            "no RunScope has been established for this run; nothing is authorized "
            "(fail closed per docs/09 SS1)",
            ScopeDenialReason.MISSING_RUN_SCOPE,
            request=request,
        )

    if not run_scope.is_established:
        return _deny(
            run_id,
            "RunScope exists only as an unconfirmed candidate (established_by is "
            "unset) — a human/authorized process must establish it before any "
            "request may be authorized (docs/13 OD-23)",
            ScopeDenialReason.RUN_SCOPE_NOT_ESTABLISHED,
            request=request,
        )

    if not run_scope.authorization_reference:
        # Unreachable via RunScope's own validator (authorization_reference
        # is a required, non-empty field) — kept as an explicit, fail-closed
        # belt-and-suspenders check rather than assuming the schema layer
        # can never be bypassed by a future caller.
        return _deny(
            run_id,
            "RunScope.authorization_reference is missing",
            ScopeDenialReason.MISSING_AUTHORIZATION_CONTEXT,
            request=request,
        )

    if request.hostname is None and request.ip is None:
        return _deny(
            run_id,
            "request names neither a hostname nor an IP address — insufficient "
            "information to evaluate; ambiguity/absence is treated as denial, "
            "never as an implicit allow",
            ScopeDenialReason.NO_TARGET_SPECIFIED,
            request=request,
        )

    if run_scope.is_operation_prohibited(request.operation_class):
        return _deny(
            run_id,
            f"operation_class {request.operation_class!r} is explicitly prohibited "
            f"for this RunScope, regardless of target scope",
            ScopeDenialReason.PROHIBITED_OPERATION,
            request=request,
        )

    if request.hostname is not None:
        if run_scope.is_domain_excluded(request.hostname):
            return _deny(
                run_id,
                f"hostname {request.hostname!r} matches an explicit exclusion "
                f"(exclusions override inclusions)",
                ScopeDenialReason.DOMAIN_EXCLUDED,
                request=request,
            )
        if not run_scope.matches_domain(request.hostname):
            return _deny(
                run_id,
                f"hostname {request.hostname!r} does not match any allowed "
                f"domain/subdomain pattern in this RunScope",
                ScopeDenialReason.DOMAIN_NOT_ALLOWED,
                request=request,
            )

    if request.ip is not None:
        if run_scope.is_ip_excluded(request.ip):
            return _deny(
                run_id,
                f"IP {request.ip!r} matches an explicit exclusion "
                f"(exclusions override inclusions)",
                ScopeDenialReason.IP_EXCLUDED,
                request=request,
            )
        if not run_scope.matches_ip(request.ip):
            return _deny(
                run_id,
                f"IP {request.ip!r} does not match any allowed IP/CIDR entry "
                f"in this RunScope",
                ScopeDenialReason.IP_NOT_ALLOWED,
                request=request,
            )

    if not run_scope.permits_port(request.port):
        return _deny(
            run_id,
            f"port {request.port!r} is not among this RunScope's allowed_ports",
            ScopeDenialReason.PORT_NOT_ALLOWED,
            request=request,
        )

    if not run_scope.permits_protocol(request.protocol):
        return _deny(
            run_id,
            f"protocol {request.protocol!r} is not among this RunScope's allowed_protocols",
            ScopeDenialReason.PROTOCOL_NOT_ALLOWED,
            request=request,
        )

    return _allow(
        run_id,
        "request target(s), port, and protocol are within the established "
        "RunScope; no exclusion or prohibited-operation match",
        request=request,
    )


def _scope_policy_fn(input_document: dict) -> PolicyDecision:
    """Adapts `decide_scope` to `trackA.policy.engine.PolicyEngine`'s
    generic dict-in/dict-out `evaluate(policy_id, input_document)`
    contract (docs/02 §6). Registered under SCOPE_POLICY_ID."""

    request = NetworkOperationRequest.model_validate(input_document["request"])
    run_scope_data = input_document.get("run_scope")
    run_scope = RunScope.model_validate(run_scope_data) if run_scope_data is not None else None
    gate_decision = decide_scope(request, run_scope)
    return PolicyDecision(
        policy_id=SCOPE_POLICY_ID,
        decision=gate_decision.decision,
        reason=gate_decision.reason,
        reason_code=(gate_decision.reason_code.value if gate_decision.reason_code else None),
    )


def build_policy_engine() -> PolicyEngine:
    """A PolicyEngine with the scope policy pre-registered — the one
    concrete policy Context 3 builds (see trackA/policy/engine.py's
    module docstring for why the engine itself stays generic)."""

    engine = PolicyEngine()
    engine.register_policy(SCOPE_POLICY_ID, _scope_policy_fn)
    return engine


class ScopeGate:
    """docs/02 §7 + docs/13 OD-18's extended, request-level role.

    Two responsibilities, matching the two distinct scope questions this
    package's docs/03 §4.4 / OD-23 explicitly kept separate (see
    trackA/schemas/scope.py's module docstring):

    - `authorize_request` / `authorize_action`: the OD-18 request-level
      gate — "is this specific proposed network-capable operation within
      the current run's established RunScope?" THIS is the gate every
      network-capable request must pass through, and is the primary
      deliverable of Context 3.

    - `check_scope`: the docs/02 §7 Stage-0 interface
      (`check_scope(ScopeRequest) -> ScopeDecision`) — "is this target
      part of a programme we're authorized to test at all?", evaluated
      against an explicit list of authorized/excluded patterns (mirroring
      docs/09 §1's `data.authorized_scope_patterns` / `data.
      explicitly_excluded` Rego inputs) rather than against a RunScope
      object, since at Stage 0 a confirmed RunScope may not exist yet.
      Reuses the same `domain_matches` primitive as RunScope itself so
      there is exactly one domain-pattern-matching implementation in the
      codebase.
    """

    def __init__(self, *, policy_engine: Optional[PolicyEngine] = None) -> None:
        self._policy_engine = policy_engine or build_policy_engine()

    # -- OD-18: request-level authorization --------------------------------

    def authorize_request(
        self, request: NetworkOperationRequest, run_scope: Optional[RunScope]
    ) -> ScopeGateDecision:
        """Evaluate one already-normalized NetworkOperationRequest. Routes
        through the registered PolicyEngine (rather than calling
        `decide_scope` directly) so the fail-closed-on-exception guarantee
        in `PolicyEngine.evaluate` also covers this path, and so a future
        context that swaps in a real OPA-backed PolicyEngine changes
        nothing here."""

        input_document = {
            "request": request.model_dump(mode="json"),
            "run_scope": run_scope.model_dump(mode="json") if run_scope is not None else None,
        }
        policy_decision = self._policy_engine.evaluate(SCOPE_POLICY_ID, input_document)
        reason_code = (
            ScopeDenialReason(policy_decision.reason_code)
            if policy_decision.reason_code is not None
            else None
        )
        return ScopeGateDecision(
            run_id=request.run_id,
            decision=policy_decision.decision,
            reason=policy_decision.reason,
            reason_code=reason_code,
            evaluated_request=request,
        )

    def authorize_action(
        self, action: OrchestratorAction, run_scope: Optional[RunScope]
    ) -> ScopeGateDecision:
        """Normalize `action` (a model-proposed, therefore untrusted,
        OrchestratorAction — see trackA/schemas/orchestrator.py) and
        evaluate it. Normalization failures (an unrecognized parameter
        shape, a multi-host action, a malformed target string) are caught
        here and converted into a MALFORMED_REQUEST deny — they never
        propagate as an unhandled exception, which would leave a caller
        with no decision at all rather than a safe one (task brief §4:
        "malformed target/address representations must fail safely")."""

        run_id = action.provenance.run_id
        try:
            request = from_orchestrator_action(action)
        except NormalizationError as exc:
            return _deny(
                run_id,
                f"could not normalize OrchestratorAction into a "
                f"NetworkOperationRequest: {exc}",
                ScopeDenialReason.MALFORMED_REQUEST,
            )
        return self.authorize_request(request, run_scope)

    # -- docs/02 SS7 Stage-0 interface --------------------------------------

    def check_scope(
        self,
        target_identifier: str,
        *,
        authorized_scope_patterns: List[str],
        explicitly_excluded: Optional[List[str]] = None,
    ) -> bool:
        """docs/02 §7 / docs/09 §1's Stage-0 check, in its own right (does
        not require a RunScope to already exist — a RunScope is typically
        established as an outcome of, or alongside, this confirmation,
        not a precondition for it).

        Returns True only for an unambiguous match against
        `authorized_scope_patterns` with no matching exclusion; every
        other case (no match, malformed target, excluded) returns False.
        Building the corresponding `ScopeDecision` record (which also
        needs a `ScopeRequest` to correlate against, per docs/03 §2.1-2.2)
        is left to the caller — this method is the pure policy predicate
        docs/09 §1's Rego `allow` rule describes; the caller supplies the
        rest of the record-keeping that isn't a policy decision."""

        target = normalize_hostname(target_identifier)
        if not target:
            return False
        for excluded in explicitly_excluded or []:
            if domain_matches(target, excluded):
                return False
        return any(domain_matches(target, pattern) for pattern in authorized_scope_patterns)
