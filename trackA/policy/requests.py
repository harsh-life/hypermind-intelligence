"""The normalized request shape the Scope Gate reasons about, plus a
best-effort normalizer from an `OrchestratorAction`.

Source: docs/01_ARCHITECTURE.md §5/§9 (MODEL PROPOSES -> POLICY/SCOPE
DECIDES -> TOOL EXECUTES; Orchestrator's scope-validation check),
docs/13_OPEN_DECISIONS.md OD-18 ("every network-capable tool request
initiated by a model/worker must pass through the Scope Gate").

Scope boundary: this module defines the CONTRACT the Scope Gate
evaluates (a single, concrete, already-normalized target) and a
convenience normalizer for the common case. It does not attempt a
complete, tool-manifest-driven extraction for all eight docs/06 tools —
that full mapping (ToolManifest.input_schema-aware parameter extraction)
belongs to the future Orchestrator/Docker-execution-layer integration
(docs/02 §11-12), explicitly out of scope for Context 3 ("Do not
implement actual tool execution here"). What is built here is real and
useful today: a fixed, documented, best-effort extraction over the
parameter-key conventions already visible in docs/06_TOOL_REGISTRY_README.md
(subfinder's `domain`, katana's `start_url`, nuclei's `target_url`, ...),
raising rather than guessing whenever the shape is unrecognized or
ambiguous (multiple hosts in one action, no recognizable target field).
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.orchestrator import OrchestratorAction

# Fixed, documented parameter-key preference order for extracting a single
# target string out of `OrchestratorAction.proposed_parameters`, matching
# docs/06's actual per-tool `input_schema` field names for the tools named
# in docs/01_ARCHITECTURE.md §11. Order matters only in that the first key
# present wins; a request naming more than one is unusual and not treated
# specially (whichever recognized key appears first in this tuple is used).
_TARGET_PARAM_KEYS = (
    "target_url",  # katana.start_url is handled separately below; nuclei/ffuf use target_url*
    "target_url_pattern",  # ffuf (may contain a FUZZ placeholder — rejected as malformed, see below)
    "start_url",  # katana
    "target_endpoint",  # garak / pyrit
    "target_domain",
    "domain",  # subfinder
    "target",
)


class NormalizationError(ValueError):
    """Raised when an OrchestratorAction cannot be safely normalized into
    a single NetworkOperationRequest. Callers (trackA.policy.scope_gate)
    must treat this the same as any other malformed-request case: DENY,
    never "no decision" / implicit proceed."""


class NetworkOperationRequest(HypermindModel):
    """One concrete, already-normalized network-capable operation a tool
    proposes to perform. This is what the Scope Gate actually evaluates —
    never raw, tool-specific parameters, and never free text.

    Deliberately narrow: exactly one target identity per request. An
    OrchestratorAction that would touch multiple hosts (e.g. httpx given
    several `hosts`) must be expanded into one NetworkOperationRequest per
    host by the caller — `from_orchestrator_action` below refuses to
    collapse a multi-host action into one request rather than silently
    picking one (see its docstring).
    """

    run_id: str
    hostname: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    protocol: Optional[str] = None
    operation_class: Optional[str] = None
    source_action_id: Optional[str] = None
    raw_target: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        from trackA.schemas.scope import normalize_hostname

        if data.get("hostname") is not None:
            h = normalize_hostname(str(data["hostname"]))
            if not h or h == "." or "*" in h or any(c.isspace() for c in h):
                raise ValueError(
                    f"NetworkOperationRequest.hostname is not a valid concrete "
                    f"hostname: {data['hostname']!r} (wildcards and blank/"
                    f"whitespace hostnames are never valid for a single "
                    f"request — a wildcard belongs only in a RunScope "
                    f"allow-list pattern, never in a proposed request)"
                )
            data["hostname"] = h

        if data.get("ip") is not None:
            import ipaddress

            try:
                ipaddress.ip_address(str(data["ip"]).strip())
            except ValueError as exc:
                raise ValueError(
                    f"NetworkOperationRequest.ip is not a single valid IP "
                    f"address: {data['ip']!r} ({exc}); a request names one "
                    f"concrete address, never a CIDR range"
                ) from exc
            data["ip"] = str(data["ip"]).strip()

        if data.get("protocol") is not None:
            data["protocol"] = str(data["protocol"]).strip().lower()
        if data.get("operation_class") is not None:
            data["operation_class"] = str(data["operation_class"]).strip().lower()

        return data

    @model_validator(mode="after")
    def _has_some_target(self) -> "NetworkOperationRequest":
        # No hard requirement here that hostname/ip be present: an absent
        # target is a legitimate, well-defined state (the request is
        # "insufficiently specified") that the Scope Gate denies with a
        # specific, machine-readable reason (ScopeDenialReason.NO_TARGET_
        # SPECIFIED) rather than one this schema silently forbids at
        # construction time. Rejecting it here would collapse that
        # distinguishable deny-reason into a generic ValidationError.
        return self


def from_orchestrator_action(action: OrchestratorAction) -> NetworkOperationRequest:
    """Best-effort extraction of a single NetworkOperationRequest from an
    OrchestratorAction's `proposed_parameters`.

    Raises `NormalizationError` (never returns a guessed/partial result)
    when:
      - no recognized target parameter key is present, or
      - the recognized value is a list with other than exactly one entry
        (a multi-host action must be expanded by the caller into one
        NetworkOperationRequest per host — silently checking only the
        first would authorize the rest by omission), or
      - the recognized value contains a FUZZ-style placeholder (ffuf's
        `target_url_pattern`) that is not a concrete target, or
      - the value cannot be parsed into a hostname/IP at all.

    `operation_class` is populated only from an explicit
    `proposed_parameters["operation_class"]` override if the caller
    supplied one; mapping each tool's docs/06 `category`/`risk_classification`
    into an operation_class automatically is Tool-Registry-integration
    work left for the Orchestrator context that actually wires the Tool
    Registry to this normalizer — omitting it here can only ever cause a
    missed PROHIBITED_OPERATION veto (fail-safe direction), never a false
    ALLOW, so it is a documented limitation, not a security gap.
    """

    params: Dict[str, Any] = action.proposed_parameters

    raw_value = None
    used_key = None
    for key in _TARGET_PARAM_KEYS:
        if key in params:
            raw_value = params[key]
            used_key = key
            break
    if used_key is None and "hosts" in params:
        raw_value = params["hosts"]
        used_key = "hosts"

    if used_key is None:
        raise NormalizationError(
            f"OrchestratorAction (target_registry_id={action.target_registry_id!r}) "
            f"proposed_parameters contain no recognized target field "
            f"(checked {_TARGET_PARAM_KEYS + ('hosts',)}); refusing to guess"
        )

    if isinstance(raw_value, list):
        if len(raw_value) != 1:
            raise NormalizationError(
                f"proposed_parameters[{used_key!r}] names {len(raw_value)} "
                f"targets; a single NetworkOperationRequest can authorize "
                f"only one target at a time — expand into one request per "
                f"host rather than checking (and thereby silently "
                f"authorizing) only the first"
            )
        raw_value = raw_value[0]

    if not isinstance(raw_value, str) or not raw_value.strip():
        raise NormalizationError(
            f"proposed_parameters[{used_key!r}] is not a non-empty string: {raw_value!r}"
        )
    raw_value = raw_value.strip()

    if "FUZZ" in raw_value:
        raise NormalizationError(
            f"proposed_parameters[{used_key!r}]={raw_value!r} contains an "
            f"unresolved FUZZ placeholder — not a concrete target"
        )

    hostname: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None

    parsed = urlsplit(raw_value if "://" in raw_value else f"//{raw_value}")
    host_part = parsed.hostname
    if "://" in raw_value:
        protocol = parsed.scheme or None
        port = parsed.port
    else:
        # No scheme: support a bare "host" or "host:port" form directly
        # (e.g. subfinder's `domain`, or an ip:port SSRF-style target).
        if parsed.hostname is None and ":" in raw_value and raw_value.count(":") == 1:
            candidate_host, _, candidate_port = raw_value.partition(":")
            host_part = candidate_host or None
            if candidate_port.isdigit():
                port = int(candidate_port)
        else:
            port = parsed.port

    if not host_part:
        raise NormalizationError(
            f"could not extract a hostname/IP from proposed_parameters"
            f"[{used_key!r}]={raw_value!r}"
        )

    import ipaddress

    try:
        ipaddress.ip_address(host_part)
        ip = host_part
    except ValueError:
        hostname = host_part

    operation_class = params.get("operation_class")
    if operation_class is not None:
        operation_class = str(operation_class)

    return NetworkOperationRequest(
        run_id=action.provenance.run_id,
        hostname=hostname,
        ip=ip,
        port=port,
        protocol=protocol,
        operation_class=operation_class,
        source_action_id=action.provenance.record_id,
        raw_target=raw_value,
    )
