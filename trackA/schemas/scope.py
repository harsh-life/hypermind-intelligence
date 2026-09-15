"""Scope schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.1-2.2, §4.4;
docs/13_OPEN_DECISIONS.md OD-18/OD-23 (authoritative decisions); docs/
09_SECURITY_POLICIES_README.md §1 (scope-policy semantics: default-deny,
exclusions override inclusions, ambiguity resolves to deny).

Two distinct concepts live in this module — do not conflate them:

    ScopeAuthorization
        The Stage-0, once-per-run pairing of a ScopeRequest and its
        (possibly not-yet-made) ScopeDecision (docs/03 §2.1-2.2,
        literally-named schemas). Answers "is this target part of a
        programme we are authorized to test at all?"

    RunScope
        [Context 3] The structured, engagement-specific authorization
        object described in docs/03 §4.4 ("RunScope — shape note") and
        authoritatively decided in docs/13_OPEN_DECISIONS.md OD-23: the
        confirmed set of domains/subdomains/IPs/ports/protocols/
        exclusions/prohibited-operation-classes a run is actually allowed
        to touch, established/confirmed by a human before execution and
        evaluated by the Scope Gate (trackA.policy.scope_gate) against
        *every* proposed network-capable request for the run's duration
        (OD-18). NOT the same question as ScopeAuthorization above — a
        program-level "yes, test this domain" (ScopeAuthorization) and
        the fine-grained "which hosts/ports/protocols within that domain,
        right now" (RunScope) are different, if related, decisions; OD-23
        explicitly left §2.1/§2.2's literal schemas un-restructured and
        recorded RunScope's shape separately for exactly this reason.

Naming note: an earlier context used the name `RunScope` for what is
`ScopeAuthorization` here (see that class's docstring). That name is
reclaimed here for the actual OD-23/docs-03-§4.4 concept, since nothing
in docs/03 or docs/13 ever named the request/decision pairing "RunScope"
— it was an unlabelled convenience type from the start. The rename's
blast radius (trackA/schemas/__init__.py, tests/schemas/test_scope.py)
is updated in the same commit; nothing outside the schema layer consumed
the old name (registries/models/tests were checked).
"""
from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import Provenance, _new_uuid, _utc_now_iso  # noqa: F401


# --------------------------------------------------------------------------
# Stage-0: ScopeRequest / ScopeDecision / ScopeAuthorization
# --------------------------------------------------------------------------


class ScopeRequest(HypermindModel):
    """docs/03 §2.1. Produced by: Human / Scope Gate caller."""

    provenance: Provenance
    target_identifier: str
    authorization_reference: str
    requested_by: str
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _stage_is_scope_gate(self) -> "ScopeRequest":
        from trackA.schemas.common import PipelineStage

        if self.provenance.stage != PipelineStage.SCOPE_GATE:
            raise ValueError("ScopeRequest.provenance.stage must be 'scope_gate'")
        return self


class ScopeDecision(HypermindModel):
    """docs/03 §2.2. Produced by: Scope Gate."""

    provenance: Provenance
    request_record_id: str
    decision: Literal["allow", "deny"]
    reason: str
    policy_version: str

    @model_validator(mode="after")
    def _stage_is_scope_gate(self) -> "ScopeDecision":
        from trackA.schemas.common import PipelineStage

        if self.provenance.stage != PipelineStage.SCOPE_GATE:
            raise ValueError("ScopeDecision.provenance.stage must be 'scope_gate'")
        return self


class ScopeAuthorization(HypermindModel):
    """Composition of a ScopeRequest and its (possibly not-yet-made)
    ScopeDecision for one run's Stage-0 programme-level authorization.

    NOT a literally-named schema in docs/03 — docs/03 §2.1/§2.2 define
    ScopeRequest and ScopeDecision as two separate records correlated only
    via ScopeDecision.request_record_id. ScopeAuthorization pairs them
    because a run cannot proceed past Stage 0 (docs/01_ARCHITECTURE.md §5)
    without both existing, and downstream code needs one thing to hold.
    Built only from the two documented schemas; no new fields invented.

    (Renamed from `RunScope` in Context 3 — see this module's docstring.)
    """

    request: ScopeRequest
    decision: Optional[ScopeDecision] = None

    @model_validator(mode="after")
    def _decision_correlates_to_request(self) -> "ScopeAuthorization":
        if self.decision is not None:
            if self.decision.request_record_id != self.request.provenance.record_id:
                raise ValueError(
                    "ScopeAuthorization.decision.request_record_id must reference "
                    "ScopeAuthorization.request.provenance.record_id"
                )
        return self

    @property
    def is_authorized(self) -> bool:
        """True only once an explicit 'allow' ScopeDecision exists.

        Ambiguity/absence must never resolve to authorized — mirrors the
        default-deny principle stated repeatedly across docs/01 §4 and
        docs/09_SECURITY_POLICIES §1 (enforcing that principle at runtime
        is Scope Gate logic and out of scope here; this property only
        reflects the state already present on the object).
        """

        return self.decision is not None and self.decision.decision == "allow"


# --------------------------------------------------------------------------
# Domain/IP matching primitives — shared by RunScope's own predicate
# methods and by trackA.policy's Stage-0 checker, so there is exactly one
# implementation of "does this hostname match this pattern" in the codebase.
# --------------------------------------------------------------------------


def normalize_hostname(value: str) -> str:
    """Lowercase, strip surrounding whitespace and a single trailing dot
    (the DNS root label). Does not validate character content — callers
    that need to reject malformed hostnames do so separately (see
    `RunScope`'s and `trackA.policy.requests.NetworkOperationRequest`'s
    own validators), because a *pattern* (which may legitimately start
    with a bare `*.`) and a *concrete request target* (which must not)
    have different validity rules over the same normalized string.
    """

    v = value.strip().lower()
    if v.endswith(".") and v != ".":
        v = v[:-1]
    return v


def domain_matches(hostname: str, pattern: str) -> bool:
    """True if `hostname` (a concrete, already-normalized host) is
    covered by `pattern` (an allow/exclude-list entry, possibly
    wildcarded).

    Semantics [documented judgment call — docs/03 §4.4 and docs/13 OD-23
    name "allowed domains"/"allowed subdomains" as fields but do not
    specify wildcard matching rules]:

    - `pattern` with no leading `*.` — exact match only. "example.com"
      matches "example.com" and nothing else; it does NOT match
      "api.example.com". This is the narrowest safe reading of a bare
      domain entry.
    - `pattern` starting with `*.` — matches any hostname that has one or
      more additional labels prepended to the pattern's suffix (i.e.
      *.example.com matches api.example.com and a.b.example.com) but
      does NOT match the bare apex "example.com" itself — matching
      convention is one entry per level to include (list both
      "example.com" and "*.example.com" to cover the whole domain plus
      every subdomain, mirroring how real bug-bounty scope documents are
      written, e.g. docs/09 §1's own `*.example.com` example).
    """

    h = normalize_hostname(hostname)
    p = normalize_hostname(pattern)
    if not h or not p:
        return False
    if p.startswith("*."):
        suffix = p[1:]  # ".example.com"
        return h.endswith(suffix) and len(h) > len(suffix)
    return h == p


def _parse_ip_network(value: str) -> "ipaddress.IPv4Network | ipaddress.IPv6Network":
    # strict=False: a host bit set on a /24-style entry ("10.0.0.5/24")
    # is accepted as identifying that host's network, matching how real
    # scope documents list ranges — never silently widened beyond what
    # the CIDR prefix itself specifies.
    return ipaddress.ip_network(value.strip(), strict=False)


# --------------------------------------------------------------------------
# RunScope — the canonical, engagement-specific authorization object
# (docs/03 §4.4, docs/13 OD-23).
# --------------------------------------------------------------------------


class RunScope(HypermindModel):
    """The confirmed, structured authorization for one run.

    Field set matches docs/03 §4.4's recorded RunScope shape exactly:
    authorization_reference, allowed domains, allowed subdomains, allowed
    IPs/CIDRs, allowed ports/protocols, exclusions, prohibited operation
    classes, relevant run metadata — "none of these are hardcoded values,
    they are the shape a real RunScope instance populates" (docs/03 §4.4).

    Source flexibility (docs/13 OD-23): a RunScope's initial content may
    originate from human-provided scope, an uploaded structured scope
    file, or (later) normalized extraction from an authorized bug-bounty/
    client scope source. Regardless of source, constructing a `RunScope`
    object alone NEVER grants authorization — see `established_by` below.
    A parser/model may build a `RunScope` as a *candidate*; only a human/
    authorized process setting `established_by` makes it usable by the
    Scope Gate (trackA.policy.scope_gate.ScopeGate refuses to authorize
    anything against an unestablished RunScope — see that module).

    This is a process invariant the schema layer cannot cryptographically
    enforce (i.e. nothing here stops code from passing
    `established_by="not actually a human"`) — the same documented
    boundary already accepted elsewhere in this package for
    `TrustClassification.VALIDATED_FINDING` (trackA/schemas/common.py):
    only trusted, human-authorized call sites may ever populate this
    field. `trackA.policy.scope_gate.ScopeGate` never sets it itself.

    Port/protocol semantics [documented judgment call]: `allowed_ports`
    and `allowed_protocols` are treated as *optional refinements*, not
    required target-identity fields like domains/IPs. An empty list means
    "this RunScope does not restrict along this dimension" (a request is
    not denied merely for specifying an unlisted port when no port
    restriction was ever declared) — mirroring how real scope documents
    name domains but rarely enumerate every port a recon tool might
    touch. A non-empty list, by contrast, is a real restriction: only the
    listed values are permitted. Domains/subdomains/IPs do not get this
    permissive-when-empty treatment because they are the run's target
    *identity* — an empty allow-list there means literally nothing has
    been authorized, which is the correct fail-closed default (no special
    case needed: no domain/IP pattern for a request to match against
    means the request is denied through the ordinary matching path).
    """

    run_id: str
    authorization_reference: str = Field(min_length=1)

    allowed_domains: List[str] = Field(default_factory=list)
    allowed_subdomains: List[str] = Field(default_factory=list)
    allowed_ips: List[str] = Field(default_factory=list)
    allowed_ports: List[int] = Field(default_factory=list)
    allowed_protocols: List[str] = Field(default_factory=list)

    excluded_domains: List[str] = Field(default_factory=list)
    excluded_ips: List[str] = Field(default_factory=list)

    prohibited_operation_classes: List[str] = Field(default_factory=list)

    run_metadata: Dict[str, Any] = Field(default_factory=dict)

    source_scope_request_id: Optional[str] = None

    established_by: Optional[str] = None
    established_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults_and_normalize(cls, data):
        # Normalization happens here (before construction), not in an
        # `after` validator: HypermindModel sets `validate_assignment=True`
        # so `self.field = ...` inside an `after` validator would trigger
        # a fresh validation pass on that assignment and recurse into this
        # same validator again (RecursionError) — assigning normalized
        # values back onto `self` during `after` is a genuine trap the
        # validate_assignment config sets, not just verbose.
        if isinstance(data, dict):
            data = dict(data)
            if data.get("established_by") and not data.get("established_at"):
                data["established_at"] = _utc_now_iso()
            for key in ("allowed_domains", "allowed_subdomains", "excluded_domains"):
                if key in data and data[key] is not None:
                    data[key] = [normalize_hostname(d) for d in data[key]]
            if "allowed_protocols" in data and data["allowed_protocols"] is not None:
                data["allowed_protocols"] = [p.strip().lower() for p in data["allowed_protocols"]]
            if (
                "prohibited_operation_classes" in data
                and data["prohibited_operation_classes"] is not None
            ):
                data["prohibited_operation_classes"] = [
                    c.strip().lower() for c in data["prohibited_operation_classes"]
                ]
        return data

    @model_validator(mode="after")
    def _validate(self) -> "RunScope":
        for label, values in (
            ("allowed_ips", self.allowed_ips),
            ("excluded_ips", self.excluded_ips),
        ):
            for entry in values:
                try:
                    _parse_ip_network(entry)
                except ValueError as exc:
                    raise ValueError(
                        f"RunScope.{label} contains an unparseable IP/CIDR entry "
                        f"{entry!r}: {exc}"
                    ) from exc

        for port in self.allowed_ports:
            if not (1 <= port <= 65535):
                raise ValueError(
                    f"RunScope.allowed_ports entries must be in 1-65535, got {port}"
                )

        if (self.established_by is None) != (self.established_at is None):
            raise ValueError(
                "RunScope.established_by and established_at must be set together "
                "(both present, once a human/authorized process establishes the "
                "scope, or both absent for a not-yet-established candidate)"
            )

        return self

    # -- Predicate methods: pure queries over this object's own data. --
    # Combining these into an allow/deny *decision* (including the
    # default-deny / exclusions-override-inclusions / ambiguity-denies
    # policy) is deliberately NOT done here — that is Scope Gate/Policy
    # Engine logic (trackA.policy.scope_gate), not schema logic.

    @property
    def is_established(self) -> bool:
        return self.established_by is not None

    def matches_domain(self, hostname: str) -> bool:
        return any(
            domain_matches(hostname, p)
            for p in (*self.allowed_domains, *self.allowed_subdomains)
        )

    def is_domain_excluded(self, hostname: str) -> bool:
        return any(domain_matches(hostname, p) for p in self.excluded_domains)

    def matches_ip(self, ip_str: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip_str.strip())
        except ValueError:
            return False
        for entry in self.allowed_ips:
            if addr in _parse_ip_network(entry):
                return True
        return False

    def is_ip_excluded(self, ip_str: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip_str.strip())
        except ValueError:
            return False
        for entry in self.excluded_ips:
            if addr in _parse_ip_network(entry):
                return True
        return False

    def permits_port(self, port: Optional[int]) -> bool:
        if not self.allowed_ports:
            return True
        return port is not None and port in self.allowed_ports

    def permits_protocol(self, protocol: Optional[str]) -> bool:
        if not self.allowed_protocols:
            return True
        return protocol is not None and protocol.strip().lower() in self.allowed_protocols

    def is_operation_prohibited(self, operation_class: Optional[str]) -> bool:
        if operation_class is None:
            return False
        return operation_class.strip().lower() in self.prohibited_operation_classes


# --------------------------------------------------------------------------
# Run — thin run-correlation convenience (unchanged concept from Context 1;
# extended here to also carry the confirmed RunScope, since that is new
# content Context 3 owns and a run legitimately needs both the Stage-0
# ScopeAuthorization and its confirmed RunScope to proceed).
# --------------------------------------------------------------------------


class Run(HypermindModel):
    """Minimal run-correlation record.

    UNRESOLVED AMBIGUITY: no document defines a standalone "Run" schema.
    docs/03_DATA_SCHEMAS_README.md §1.1 only establishes
    `Provenance.run_id` as the join key correlating every record produced
    during one target's run — there is no dedicated record type for the
    run itself. This type is a thin, explicitly-flagged convenience built
    only from already-documented, already-required fields (a run_id, the
    ScopeAuthorization that authorizes it, the confirmed RunScope used for
    ongoing request-level checks, and a start timestamp) so downstream
    code has something to construct before individual pipeline records
    exist. If a literal Run schema is later specified in the docs,
    replace this type rather than silently extend it.
    """

    run_id: str
    scope: ScopeAuthorization
    run_scope: Optional[RunScope] = None
    started_at: str = ""

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            data.setdefault("started_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return data

    @model_validator(mode="after")
    def _scope_run_id_matches(self) -> "Run":
        if self.scope.request.provenance.run_id != self.run_id:
            raise ValueError("Run.scope.request.provenance.run_id must equal Run.run_id")
        if self.scope.decision is not None and self.scope.decision.provenance.run_id != self.run_id:
            raise ValueError("Run.scope.decision.provenance.run_id must equal Run.run_id")
        if self.run_scope is not None and self.run_scope.run_id != self.run_id:
            raise ValueError("Run.run_scope.run_id must equal Run.run_id")
        return self
